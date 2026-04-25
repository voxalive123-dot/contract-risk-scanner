from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import ApiKey, Membership, Organization, OrganizationInvite, Scan, Subscription, UsageLog, User


DEFAULT_OWNER_EMAIL = "admin.dashboard@voxarisk.com"
DEFAULT_OWNER_ORG_NAME = "VoxaRisk Platform"
LEGACY_PLATFORM_ORG_NAMES = {"voxarisk-platform-org"}


def _normalized(value: str | None) -> str:
    return (value or "").strip().lower()


def owner_email() -> str:
    return _normalized(os.getenv("PLATFORM_OWNER_EMAIL", DEFAULT_OWNER_EMAIL)) or _normalized(DEFAULT_OWNER_EMAIL)


def owner_org_name() -> str:
    raw = os.getenv("PLATFORM_OWNER_ORG_NAME", DEFAULT_OWNER_ORG_NAME).strip()
    return raw or DEFAULT_OWNER_ORG_NAME


def canonical_platform_org_name() -> str:
    return owner_org_name()


def platform_org_name_aliases() -> set[str]:
    return {_normalized(canonical_platform_org_name()), *{_normalized(item) for item in LEGACY_PLATFORM_ORG_NAMES}}


def is_platform_owner_email(email: str | None) -> bool:
    return _normalized(email) == owner_email()


def is_platform_like_org_name(name: str | None) -> bool:
    return _normalized(name) in platform_org_name_aliases()


def _owner_membership_rows(db: Session, org: Organization) -> list[Membership]:
    stmt = (
        select(Membership)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.org_id == org.id,
            func.lower(User.email) == owner_email(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def _org_activity_vector(db: Session, org: Organization) -> tuple[int, int, int, int, int, int, float]:
    current_subscriptions = int(
        db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.org_id == org.id, Subscription.is_current.is_(True))
        ).scalar_one()
    )
    active_api_keys = int(
        db.execute(
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.org_id == org.id, ApiKey.active.is_(True))
        ).scalar_one()
    )
    usage_count = int(
        db.execute(select(func.count()).select_from(UsageLog).where(UsageLog.org_id == org.id)).scalar_one()
    )
    scan_count = int(
        db.execute(select(func.count()).select_from(Scan).where(Scan.org_id == org.id)).scalar_one()
    )
    invite_count = int(
        db.execute(
            select(func.count()).select_from(OrganizationInvite).where(OrganizationInvite.org_id == org.id)
        ).scalar_one()
    )
    owner_memberships = _owner_membership_rows(db, org)
    active_owner_memberships = sum(1 for membership in owner_memberships if membership.status == "active")
    created = org.created_at or datetime.now(timezone.utc)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    # Older orgs win ties to preserve existing production-carrying records.
    return (
        current_subscriptions,
        active_api_keys,
        usage_count,
        scan_count,
        invite_count,
        active_owner_memberships,
        -created.timestamp(),
    )


def _has_platform_authority(vector: tuple[int, int, int, int, int, int, float]) -> bool:
    return any(vector[index] > 0 for index in range(6))


def platform_org_candidates(db: Session) -> list[Organization]:
    stmt = select(Organization)
    orgs = list(db.execute(stmt).scalars().all())
    return [org for org in orgs if is_platform_like_org_name(org.name)]


def choose_canonical_platform_org(db: Session) -> tuple[Organization | None, str]:
    candidates = platform_org_candidates(db)
    if not candidates:
        return None, "no_platform_org_candidates"

    canonical_name = _normalized(canonical_platform_org_name())
    canonical_named = [org for org in candidates if _normalized(org.name) == canonical_name]
    scored = {str(org.id): _org_activity_vector(db, org) for org in candidates}
    best_any = max(candidates, key=lambda org: scored[str(org.id)])

    if canonical_named:
        best_named = max(canonical_named, key=lambda org: scored[str(org.id)])
        if (
            best_any.id != best_named.id
            and _has_platform_authority(scored[str(best_any.id)])
            and scored[str(best_any.id)] > scored[str(best_named.id)]
        ):
            return best_any, "legacy_alias_real_activity"
        return best_named, "canonical_name_preferred"

    return best_any, "activity_based_fallback"


def platform_owner_membership_statuses(db: Session, *, org: Organization) -> list[dict[str, str]]:
    rows = _owner_membership_rows(db, org)
    return [
        {
            "membership_id": str(row.id),
            "role": row.role,
            "status": row.status,
        }
        for row in rows
    ]


def is_platform_owner_account(
    db: Session,
    *,
    user_id: str | None,
    org_id: str | None,
) -> bool:
    if not user_id or not org_id:
        return False

    try:
        normalized_user_id = uuid.UUID(str(user_id))
        normalized_org_id = uuid.UUID(str(org_id))
    except (TypeError, ValueError, AttributeError):
        return False

    canonical_org, _reason = choose_canonical_platform_org(db)
    if canonical_org is None or canonical_org.id != normalized_org_id:
        return False

    stmt = (
        select(Membership)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.user_id == normalized_user_id,
            Membership.org_id == canonical_org.id,
            Membership.role == "owner",
            Membership.status == "active",
            func.lower(User.email) == owner_email(),
        )
        .limit(1)
    )
    return db.execute(stmt).scalars().first() is not None
