from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import InternalOperatorAction, Membership, Organization, OwnerEntitlementGrant, User
from platform_owner import choose_canonical_platform_org, owner_email


OWNER_GRANT_PLANS = {"executive", "enterprise"}
OWNER_GRANT_TYPES = {"trial", "complimentary", "internal"}
OWNER_GRANT_ACTIVE_STATUSES = {"active"}
INDEFINITE_GRANT_TYPES = {"complimentary", "internal"}
DEFAULT_GRANT_DAYS = {
    "executive": 14,
    "enterprise": 30,
}
PLAN_RANK = {
    "starter": 0,
    "business": 1,
    "executive": 2,
    "enterprise": 3,
}


class OwnerGrantError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize(value: str | None, *, lower: bool = True) -> str:
    raw = (value or "").strip()
    return raw.lower() if lower else raw


def _coerce_uuid(value: str | uuid.UUID | None, *, field_name: str) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise OwnerGrantError(f"Invalid {field_name}") from exc


def _positive_limit(value: int | None) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def _owner_actor(db: Session) -> User:
    canonical_org, _reason = choose_canonical_platform_org(db)
    if canonical_org is None:
        raise OwnerGrantError("Canonical platform owner organization is not available")

    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.org_id == canonical_org.id,
            Membership.role == "owner",
            Membership.status == "active",
            func.lower(User.email) == owner_email(),
        )
        .limit(1)
    )
    actor = db.execute(stmt).scalars().first()
    if actor is None:
        raise OwnerGrantError("Platform owner account is not configured")
    return actor


def _grant_actor(db: Session, actor_user_id: str | uuid.UUID | None = None) -> User:
    normalized_actor_user_id = _coerce_uuid(actor_user_id, field_name="actor_user_id")
    if normalized_actor_user_id is None:
        return _owner_actor(db)

    actor = db.get(User, normalized_actor_user_id)
    if actor is None or not actor.is_active:
        raise OwnerGrantError("Grant actor is not valid")
    return actor


def _grant_snapshot(grant: OwnerEntitlementGrant) -> dict[str, str | int | None]:
    return {
        "id": str(grant.id),
        "org_id": str(grant.org_id),
        "user_id": str(grant.user_id) if grant.user_id else None,
        "granted_plan": grant.granted_plan,
        "grant_type": grant.grant_type,
        "scan_quota_override": grant.scan_quota_override,
        "reason": grant.reason,
        "starts_at": _as_utc(grant.starts_at).isoformat() if grant.starts_at else None,
        "expires_at": _as_utc(grant.expires_at).isoformat() if grant.expires_at else None,
        "status": grant.status,
        "created_by_user_id": str(grant.created_by_user_id),
        "created_at": _as_utc(grant.created_at).isoformat() if grant.created_at else None,
        "revoked_by_user_id": str(grant.revoked_by_user_id) if grant.revoked_by_user_id else None,
        "revoked_at": _as_utc(grant.revoked_at).isoformat() if grant.revoked_at else None,
        "revocation_reason": grant.revocation_reason,
    }


def _record_operator_action(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    org_id: uuid.UUID,
    target_id: str,
    action_type: str,
    reason: str,
    before: dict | None,
    after: dict | None,
) -> None:
    db.add(
        InternalOperatorAction(
            actor_user_id=actor_user_id,
            org_id=org_id,
            target_type="owner_entitlement_grant",
            target_id=target_id,
            action_type=action_type,
            reason=reason,
            before_json=json.dumps(before, sort_keys=True) if before is not None else None,
            after_json=json.dumps(after, sort_keys=True) if after is not None else None,
        )
    )


def _resolve_target(
    db: Session,
    *,
    org_id: str | uuid.UUID | None,
    email: str | None,
) -> tuple[Organization, User | None]:
    normalized_org_id = _coerce_uuid(org_id, field_name="org_id")
    normalized_email = _normalize(email)

    user: User | None = None
    if normalized_email:
        stmt = select(User).where(func.lower(User.email) == normalized_email).limit(1)
        user = db.execute(stmt).scalars().first()
        if user is None:
            raise OwnerGrantError("User email not found")

    if normalized_org_id is not None:
        org = db.get(Organization, normalized_org_id)
        if org is None:
            raise OwnerGrantError("Organization not found")
    elif user is not None:
        membership_stmt = select(Membership).where(
            Membership.user_id == user.id,
            Membership.status == "active",
        )
        memberships = list(db.execute(membership_stmt).scalars().all())
        if len(memberships) != 1:
            raise OwnerGrantError("User must have exactly one active membership for email-based grants")
        org = db.get(Organization, memberships[0].org_id)
        if org is None:
            raise OwnerGrantError("Membership organization not found")
    else:
        raise OwnerGrantError("Either org_id or email is required")

    if user is not None:
        membership_stmt = select(Membership).where(
            Membership.user_id == user.id,
            Membership.org_id == org.id,
        )
        membership = db.execute(membership_stmt).scalars().first()
        if membership is None:
            raise OwnerGrantError("User does not belong to the selected organization")

    return org, user


def create_owner_entitlement_grant(
    db: Session,
    *,
    org_id: str | uuid.UUID | None = None,
    email: str | None = None,
    granted_plan: str,
    reason: str,
    grant_type: str = "trial",
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    scan_quota_override: int | None = None,
    allow_indefinite: bool = False,
    actor_user_id: str | uuid.UUID | None = None,
) -> OwnerEntitlementGrant:
    org, user = _resolve_target(db, org_id=org_id, email=email)
    actor = _grant_actor(db, actor_user_id)

    normalized_plan = _normalize(granted_plan)
    if normalized_plan not in OWNER_GRANT_PLANS:
        raise OwnerGrantError("Granted plan must be executive or enterprise")

    normalized_type = _normalize(grant_type)
    if normalized_type not in OWNER_GRANT_TYPES:
        raise OwnerGrantError("Grant type must be trial, complimentary, or internal")

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise OwnerGrantError("Grant reason is required")

    starts_at_utc = _as_utc(starts_at) or _utc_now()
    expires_at_utc = _as_utc(expires_at)

    if expires_at_utc is None:
        if allow_indefinite:
            if normalized_type not in INDEFINITE_GRANT_TYPES:
                raise OwnerGrantError("Indefinite grants require grant type complimentary or internal")
        else:
            expires_at_utc = starts_at_utc + timedelta(days=DEFAULT_GRANT_DAYS[normalized_plan])

    if expires_at_utc is not None and expires_at_utc <= starts_at_utc:
        raise OwnerGrantError("Grant expiry must be after the start time")

    if scan_quota_override is not None and scan_quota_override <= 0:
        raise OwnerGrantError("Scan quota override must be positive")

    grant = OwnerEntitlementGrant(
        org_id=org.id,
        user_id=user.id if user else None,
        granted_plan=normalized_plan,
        grant_type=normalized_type,
        scan_quota_override=scan_quota_override,
        reason=normalized_reason,
        starts_at=starts_at_utc,
        expires_at=expires_at_utc,
        status="active",
        created_by_user_id=actor.id,
    )
    db.add(grant)
    db.flush()
    db.refresh(grant)
    _record_operator_action(
        db,
        actor_user_id=actor.id,
        org_id=grant.org_id,
        target_id=str(grant.id),
        action_type="create_owner_entitlement_grant",
        reason=normalized_reason,
        before=None,
        after=_grant_snapshot(grant),
    )
    db.commit()
    db.refresh(grant)
    return grant


def revoke_owner_entitlement_grant(
    db: Session,
    *,
    grant_id: str | uuid.UUID,
    reason: str,
    actor_user_id: str | uuid.UUID | None = None,
) -> OwnerEntitlementGrant:
    actor = _grant_actor(db, actor_user_id)
    normalized_grant_id = _coerce_uuid(grant_id, field_name="grant_id")
    if normalized_grant_id is None:
        raise OwnerGrantError("Grant id is required")

    grant = db.get(OwnerEntitlementGrant, normalized_grant_id)
    if grant is None:
        raise OwnerGrantError("Grant not found")

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise OwnerGrantError("Revocation reason is required")

    before = _grant_snapshot(grant)
    grant.status = "revoked"
    grant.revoked_at = _utc_now()
    grant.revoked_by_user_id = actor.id
    grant.revocation_reason = normalized_reason
    db.flush()
    _record_operator_action(
        db,
        actor_user_id=actor.id,
        org_id=grant.org_id,
        target_id=str(grant.id),
        action_type="revoke_owner_entitlement_grant",
        reason=normalized_reason,
        before=before,
        after=_grant_snapshot(grant),
    )
    db.commit()
    db.refresh(grant)
    return grant


def list_owner_entitlement_grants(
    db: Session,
    *,
    active_only: bool = False,
    org_id: str | uuid.UUID | None = None,
    email: str | None = None,
) -> list[dict[str, str | int | bool | None]]:
    normalized_org_id = _coerce_uuid(org_id, field_name="org_id")
    normalized_email = _normalize(email)
    stmt = select(OwnerEntitlementGrant).order_by(OwnerEntitlementGrant.created_at.desc())
    if normalized_org_id is not None:
        stmt = stmt.where(OwnerEntitlementGrant.org_id == normalized_org_id)

    grants = list(db.execute(stmt).scalars().all())
    if normalized_email:
        email_user_stmt = select(User).where(func.lower(User.email) == normalized_email).limit(1)
        user = db.execute(email_user_stmt).scalars().first()
        grants = [grant for grant in grants if user is not None and grant.user_id == user.id]

    now = _utc_now()
    rows: list[dict[str, str | int | bool | None]] = []
    for grant in grants:
        effective_active = is_owner_grant_effective(grant, now=now)
        if active_only and not effective_active:
            continue
        rows.append(
            {
                **_grant_snapshot(grant),
                "effective_active": effective_active,
            }
        )
    return rows


def is_owner_grant_effective(grant: OwnerEntitlementGrant, *, now: datetime | None = None) -> bool:
    current_time = _as_utc(now) or _utc_now()
    if _normalize(grant.status) not in OWNER_GRANT_ACTIVE_STATUSES:
        return False
    if grant.revoked_at is not None:
        return False
    if _normalize(grant.granted_plan) not in OWNER_GRANT_PLANS:
        return False
    if _normalize(grant.grant_type) not in OWNER_GRANT_TYPES:
        return False
    starts_at = _as_utc(grant.starts_at)
    expires_at = _as_utc(grant.expires_at)
    if starts_at is None or starts_at > current_time:
        return False
    if expires_at is None and _normalize(grant.grant_type) not in INDEFINITE_GRANT_TYPES:
        return False
    if expires_at is not None and expires_at <= current_time:
        return False
    return True


def select_active_owner_grant(
    db: Session,
    *,
    org: Organization,
    user_id: str | uuid.UUID | None = None,
    now: datetime | None = None,
) -> OwnerEntitlementGrant | None:
    current_time = _as_utc(now) or _utc_now()
    normalized_user_id = _coerce_uuid(user_id, field_name="user_id")

    stmt = select(OwnerEntitlementGrant).where(OwnerEntitlementGrant.org_id == org.id)
    if normalized_user_id is not None:
        stmt = stmt.where(
            (OwnerEntitlementGrant.user_id == None) | (OwnerEntitlementGrant.user_id == normalized_user_id)  # noqa: E711
        )
    else:
        stmt = stmt.where(OwnerEntitlementGrant.user_id == None)  # noqa: E711

    grants = [grant for grant in db.execute(stmt).scalars().all() if is_owner_grant_effective(grant, now=current_time)]
    if not grants:
        return None

    def sort_key(grant: OwnerEntitlementGrant) -> tuple[int, int, int, float]:
        expires_at = _as_utc(grant.expires_at)
        created_at = _as_utc(grant.created_at) or current_time
        return (
            PLAN_RANK.get(_normalize(grant.granted_plan), 0),
            1 if grant.user_id is not None else 0,
            _positive_limit(grant.scan_quota_override) or 0,
            (expires_at or datetime.max.replace(tzinfo=timezone.utc)).timestamp() + created_at.timestamp() / 1_000_000,
        )

    return max(grants, key=sort_key)
