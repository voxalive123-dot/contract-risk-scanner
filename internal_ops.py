from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import AccountContext
from account_provisioning import ProvisionedAccount, provision_customer_account, request_password_reset
from crud import month_start_utc
from entitlement_diagnostics import build_entitlement_diagnostics
from entitlement_spine import resolve_entitlement_for_org
from models import (
    AIUsageMeter,
    AccountPasswordToken,
    AccountProfile,
    BillingCustomerReference,
    BillingInvoice,
    InternalOperatorAction,
    Membership,
    MonitoringSignal,
    Organization,
    OrganizationInvite,
    OwnerEntitlementGrant,
    Scan,
    StripeWebhookEvent,
    Subscription,
    UsageLog,
    User,
)
from platform_owner import (
    choose_canonical_platform_org,
    is_platform_like_org_name,
    is_platform_owner_email,
    owner_email,
    platform_owner_emails,
    platform_owner_membership_statuses,
)
from account_dashboard import set_user_account_state
from owner_entitlement_grants import (
    OwnerGrantError,
    create_owner_entitlement_grant,
    list_owner_entitlement_grants,
    revoke_owner_entitlement_grant,
)


class InternalOpsError(Exception):
    pass


class InternalOpsConfigError(InternalOpsError):
    pass


class InternalOpsForbiddenError(InternalOpsError):
    pass


def _serialize_dt(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def platform_owner_email() -> str:
    return owner_email()


def _env_emails(name: str) -> set[str]:
    raw = os.getenv(name, "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def internal_staff_roles() -> dict[str, set[str]]:
    owners = _env_emails("INTERNAL_OWNER_EMAILS") | platform_owner_emails()
    managers = _env_emails("INTERNAL_MANAGER_EMAILS") | _env_emails("INTERNAL_ADMIN_EMAILS")
    assistants = _env_emails("INTERNAL_ASSISTANT_EMAILS")
    return {"owner": owners, "manager": managers, "assistant": assistants}


def internal_admin_emails() -> set[str]:
    roles = internal_staff_roles()
    return set().union(*roles.values())


def internal_staff_role_for_context(context: AccountContext) -> str | None:
    email = context.user.email.strip().lower()
    roles = internal_staff_roles()
    if is_platform_owner_email(email) or email in roles["owner"]:
        return "owner"
    if email in roles["manager"]:
        return "manager"
    if email in roles["assistant"]:
        return "assistant"
    return None


def require_internal_admin(context: AccountContext) -> None:
    if not internal_admin_emails():
        raise InternalOpsConfigError("Internal operations access is not configured")
    if internal_staff_role_for_context(context) is None:
        raise InternalOpsForbiddenError("Account is not an internal platform admin")


def require_internal_permission(context: AccountContext, allowed_roles: set[str]) -> str:
    role = internal_staff_role_for_context(context)
    if role is None:
        raise InternalOpsForbiddenError("Account is not an internal platform admin")
    if role not in allowed_roles:
        raise InternalOpsForbiddenError("Internal staff role is not permitted for this action")
    return role


def require_platform_owner_or_internal_admin(context: AccountContext) -> None:
    require_internal_admin(context)


def _current_subscription(db: Session, org_id: uuid.UUID) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org_id, Subscription.is_current.is_(True))
        .order_by(Subscription.updated_at.desc(), Subscription.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _billing_reference(db: Session, org_id: uuid.UUID) -> BillingCustomerReference | None:
    stmt = select(BillingCustomerReference).where(BillingCustomerReference.org_id == org_id).limit(1)
    return db.execute(stmt).scalars().first()


def _count(db: Session, model, *criteria) -> int:
    stmt = select(func.count()).select_from(model)
    for item in criteria:
        stmt = stmt.where(item)
    return int(db.execute(stmt).scalar_one())


def _sum(db: Session, selectable) -> int:
    value = db.execute(selectable).scalar_one()
    return int(value or 0)


def _recent_scan_snapshot(scan: Scan) -> dict[str, Any]:
    return {
        "id": str(scan.id),
        "request_id": scan.request_id,
        "risk_score": scan.risk_score,
        "risk_density": scan.risk_density,
        "confidence": scan.confidence,
        "ruleset_version": scan.ruleset_version,
        "created_at": _serialize_dt(scan.created_at),
    }


def _usage_log_snapshot(log: UsageLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "endpoint": log.endpoint,
        "method": log.method,
        "status_code": log.status_code,
        "request_id": log.request_id,
        "created_at": _serialize_dt(log.created_at),
    }


def _signal_snapshot(signal: MonitoringSignal) -> dict[str, Any]:
    return {
        "id": str(signal.id),
        "category": signal.category,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "message": signal.message,
        "created_at": _serialize_dt(signal.created_at),
    }


def _invite_snapshot(invite: OrganizationInvite) -> dict[str, Any]:
    return {
        "id": str(invite.id),
        "email": invite.invited_email,
        "role": invite.role,
        "status": invite.status,
        "expires_at": _serialize_dt(invite.expires_at),
        "accepted_at": _serialize_dt(invite.accepted_at),
        "created_at": _serialize_dt(invite.created_at),
    }


def _membership_snapshot(db: Session, membership: Membership) -> dict[str, Any]:
    user = db.get(User, membership.user_id)
    return {
        "id": str(membership.id),
        "user_id": str(membership.user_id),
        "email": user.email if user else None,
        "role": membership.role,
        "status": membership.status,
        "created_at": _serialize_dt(membership.created_at),
    }


def _account_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "org_id": str(user.org_id),
        "created_at": _serialize_dt(user.created_at),
    }


def _operator_action_snapshot(action: InternalOperatorAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "actor_user_id": str(action.actor_user_id),
        "org_id": str(action.org_id) if action.org_id else None,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "action_type": action.action_type,
        "reason": action.reason,
        "before": action.before_json,
        "after": action.after_json,
        "created_at": _serialize_dt(action.created_at),
    }


def _owner_grant_snapshot(db: Session, grant_row: dict[str, Any]) -> dict[str, Any]:
    user = db.get(User, uuid.UUID(grant_row["user_id"])) if grant_row.get("user_id") else None
    org = db.get(Organization, uuid.UUID(grant_row["org_id"])) if grant_row.get("org_id") else None
    created_by = db.get(User, uuid.UUID(grant_row["created_by_user_id"])) if grant_row.get("created_by_user_id") else None
    return {
        "id": grant_row["id"],
        "email": user.email if user else None,
        "user_id": grant_row.get("user_id"),
        "organization_id": grant_row["org_id"],
        "organization_name": org.name if org else None,
        "granted_plan": grant_row["granted_plan"],
        "grant_type": grant_row["grant_type"],
        "scan_quota_override": grant_row["scan_quota_override"],
        "reason": grant_row["reason"],
        "starts_at": grant_row["starts_at"],
        "expires_at": grant_row["expires_at"],
        "status": grant_row["status"],
        "effective_active": grant_row["effective_active"],
        "created_by_user_id": grant_row["created_by_user_id"],
        "created_by_email": created_by.email if created_by else None,
        "created_at": grant_row["created_at"],
        "revoked_at": grant_row["revoked_at"],
        "revocation_reason": grant_row["revocation_reason"],
    }


def _single_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    users = list(db.execute(stmt).scalars().all())
    if len(users) > 1:
        raise OwnerGrantError("Multiple users exist for this email")
    return users[0] if users else None


def _active_memberships_for_user(db: Session, user: User) -> list[Membership]:
    stmt = select(Membership).where(
        Membership.user_id == user.id,
        Membership.status == "active",
    )
    return list(db.execute(stmt).scalars().all())


def list_internal_access_grants(db: Session) -> dict[str, Any]:
    grants = [
        _owner_grant_snapshot(db, row)
        for row in list_owner_entitlement_grants(db, active_only=True)
    ]
    return {
        "read_only": True,
        "grants": grants,
    }


def _provision_setup_for_new_tester(
    db: Session,
    *,
    email: str,
) -> ProvisionedAccount:
    canonical_org, _reason = choose_canonical_platform_org(db)
    if canonical_org is None:
        raise OwnerGrantError("Canonical platform organization is not available")
    return provision_customer_account(
        db,
        org_id=canonical_org.id,
        email=email,
        role="member",
    )


def create_internal_access_grant(
    db: Session,
    *,
    actor: AccountContext,
    email: str,
    granted_plan: str,
    duration_days: int | None,
    reason: str,
    scan_quota_override: int | None = None,
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise OwnerGrantError("Email is required")

    user = _single_user_by_email(db, normalized_email)
    setup_token: str | None = None
    target_org_id: str | None = None

    if user is None:
        provisioned = _provision_setup_for_new_tester(db, email=normalized_email)
        user = provisioned.user
        setup_token = provisioned.setup_token
        target_org_id = str(provisioned.organization.id)
    else:
        memberships = _active_memberships_for_user(db, user)
        if len(memberships) != 1:
            raise OwnerGrantError("Existing user must have exactly one active membership")
        target_org_id = str(memberships[0].org_id)

    expires_at = None
    if duration_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

    grant = create_owner_entitlement_grant(
        db,
        org_id=target_org_id,
        email=normalized_email,
        granted_plan=granted_plan,
        reason=reason,
        scan_quota_override=scan_quota_override,
        expires_at=expires_at,
        actor_user_id=actor.user.id,
    )
    row = next(
        (
            _owner_grant_snapshot(db, item)
            for item in list_owner_entitlement_grants(db, active_only=False, email=normalized_email)
            if item["id"] == str(grant.id)
        ),
        None,
    )
    if row is None:
        raise OwnerGrantError("Created grant could not be reloaded")
    return {
        "status": "needs_account_setup" if setup_token else "granted_existing_account",
        "grant": row,
        "setup_token": setup_token,
    }


def revoke_internal_access_grant(
    db: Session,
    *,
    actor: AccountContext,
    grant_id: str,
    reason: str,
) -> dict[str, Any]:
    grant = revoke_owner_entitlement_grant(
        db,
        grant_id=grant_id,
        reason=reason,
        actor_user_id=actor.user.id,
    )
    rows = list_owner_entitlement_grants(db, active_only=False, org_id=str(grant.org_id))
    row = next((item for item in rows if item["id"] == str(grant.id)), None)
    if row is None:
        row = {
            **{
                "id": str(grant.id),
                "org_id": str(grant.org_id),
                "user_id": str(grant.user_id) if grant.user_id else None,
                "granted_plan": grant.granted_plan,
                "grant_type": grant.grant_type,
                "scan_quota_override": grant.scan_quota_override,
                "reason": grant.reason,
                "starts_at": _serialize_dt(grant.starts_at),
                "expires_at": _serialize_dt(grant.expires_at),
                "status": grant.status,
                "effective_active": False,
                "created_by_user_id": str(grant.created_by_user_id),
                "created_at": _serialize_dt(grant.created_at),
                "revoked_at": _serialize_dt(grant.revoked_at),
                "revocation_reason": grant.revocation_reason,
            }
        }
    return {
        "status": "grant_revoked",
        "grant": _owner_grant_snapshot(db, row),
    }



def _password_token_snapshot(token: AccountPasswordToken) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if token.used_at is not None:
        token_status = "used"
    elif expires_at < now:
        token_status = "expired"
    else:
        token_status = "active"

    return {
        "id": str(token.id),
        "purpose": token.purpose,
        "status": token_status,
        "expires_at": _serialize_dt(token.expires_at),
        "used_at": _serialize_dt(token.used_at),
        "created_at": _serialize_dt(token.created_at),
    }


def _user_membership_detail(db: Session, membership: Membership) -> dict[str, Any]:
    org = db.get(Organization, membership.org_id)
    return {
        "id": str(membership.id),
        "user_id": str(membership.user_id),
        "org_id": str(membership.org_id),
        "organization_name": org.name if org else None,
        "role": membership.role,
        "status": membership.status,
        "created_at": _serialize_dt(membership.created_at),
    }


def lookup_internal_user_control(db: Session, *, email: str) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise OwnerGrantError("Email is required")

    user = _single_user_by_email(db, normalized_email)

    invites = list(
        db.execute(
            select(OrganizationInvite)
            .where(func.lower(OrganizationInvite.invited_email) == normalized_email)
            .order_by(OrganizationInvite.created_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )

    if user is None:
        available_actions: list[str] = []
        if any(invite.status == "pending" for invite in invites):
            available_actions.append("revoke_pending_invites")
        return {
            "found": False,
            "email": normalized_email,
            "user": None,
            "memberships": [],
            "invites": [_invite_snapshot(invite) for invite in invites],
            "password_tokens": [],
            "available_actions": available_actions,
        }

    memberships = list(
        db.execute(
            select(Membership)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at.desc())
        )
        .scalars()
        .all()
    )
    tokens = list(
        db.execute(
            select(AccountPasswordToken)
            .where(AccountPasswordToken.user_id == user.id)
            .order_by(AccountPasswordToken.created_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )

    available_actions: list[str] = []
    if any(membership.status == "active" for membership in memberships):
        available_actions.append("generate_reset_link")
    if any(invite.status == "pending" for invite in invites):
        available_actions.append("revoke_pending_invites")

    return {
        "found": True,
        "email": normalized_email,
        "user": _account_snapshot(user),
        "memberships": [_user_membership_detail(db, membership) for membership in memberships],
        "invites": [_invite_snapshot(invite) for invite in invites],
        "password_tokens": [_password_token_snapshot(token) for token in tokens],
        "available_actions": available_actions,
    }


def generate_internal_user_reset_link(
    db: Session,
    *,
    actor: AccountContext,
    email: str,
    reason: str,
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise OwnerGrantError("Email is required")
    if not reason or len(reason.strip()) < 8:
        raise OwnerGrantError("A clear operator reason is required")

    token = request_password_reset(db, email=normalized_email)
    if not token:
        raise OwnerGrantError("No active member account found for this email")

    user = _single_user_by_email(db, normalized_email)
    org_id = user.org_id if user else None
    action = InternalOperatorAction(
        actor_user_id=actor.user.id,
        org_id=org_id,
        target_type="user",
        target_id=str(user.id) if user else normalized_email,
        action_type="user_password_reset_link_generated",
        reason=reason.strip(),
        before_json=None,
        after_json='{"reset_path":"/reset-password?token=<redacted>"}',
    )
    db.add(action)
    db.flush()

    return {
        "status": "reset_link_generated",
        "email": normalized_email,
        "reset_path": f"/reset-password?token={token}",
        "token_ttl_hours": 2,
        "action": _operator_action_snapshot(action),
    }


def revoke_internal_user_pending_invites(
    db: Session,
    *,
    actor: AccountContext,
    email: str,
    reason: str,
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise OwnerGrantError("Email is required")
    if not reason or len(reason.strip()) < 8:
        raise OwnerGrantError("A clear operator reason is required")

    invites = list(
        db.execute(
            select(OrganizationInvite)
            .where(
                func.lower(OrganizationInvite.invited_email) == normalized_email,
                OrganizationInvite.status == "pending",
            )
            .order_by(OrganizationInvite.created_at.desc())
        )
        .scalars()
        .all()
    )

    actions: list[dict[str, Any]] = []
    for invite in invites:
        before = _invite_snapshot(invite)
        invite.status = "cancelled"
        action = InternalOperatorAction(
            actor_user_id=actor.user.id,
            org_id=invite.org_id,
            target_type="organization_invite",
            target_id=str(invite.id),
            action_type="user_pending_invite_cancelled",
            reason=reason.strip(),
            before_json=str(before),
            after_json='{"status":"cancelled"}',
        )
        db.add(action)
        db.flush()
        actions.append(_operator_action_snapshot(action))

    return {
        "status": "pending_invites_revoked",
        "email": normalized_email,
        "revoked_count": len(invites),
        "actions": actions,
    }

def _current_month_scan_count(db: Session, *, org_id: uuid.UUID | None = None) -> int:
    month_start = month_start_utc()
    stmt = select(func.count()).select_from(Scan).where(Scan.created_at >= month_start)
    if org_id is not None:
        stmt = stmt.where(Scan.org_id == org_id)
    return int(db.execute(stmt).scalar_one())


def _recent_usage_logs(
    db: Session,
    *,
    status_code: int | None = None,
    status_code_min: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(UsageLog).order_by(UsageLog.created_at.desc()).limit(limit)
    if status_code is not None:
        stmt = (
            select(UsageLog)
            .where(UsageLog.status_code == status_code)
            .order_by(UsageLog.created_at.desc())
            .limit(limit)
        )
    elif status_code_min is not None:
        stmt = (
            select(UsageLog)
            .where(UsageLog.status_code >= status_code_min)
            .order_by(UsageLog.created_at.desc())
            .limit(limit)
        )
    return [_usage_log_snapshot(log) for log in db.execute(stmt).scalars().all()]


def _recent_operator_actions(db: Session, *, org_id: uuid.UUID | None = None, limit: int = 10) -> list[dict[str, Any]]:
    stmt = select(InternalOperatorAction).order_by(InternalOperatorAction.created_at.desc()).limit(limit)
    if org_id is not None:
        stmt = (
            select(InternalOperatorAction)
            .where(InternalOperatorAction.org_id == org_id)
            .order_by(InternalOperatorAction.created_at.desc())
            .limit(limit)
        )
    return [_operator_action_snapshot(action) for action in db.execute(stmt).scalars().all()]


def _status_badge(entitlement: dict[str, Any]) -> dict[str, str]:
    if entitlement["subscription_state"] == "restricted" or entitlement["fail_closed"]:
        return {"label": "Restricted", "tone": "danger"}
    if entitlement["paid_access"]:
        return {"label": entitlement["effective_plan"].title(), "tone": "success"}
    return {"label": "Starter", "tone": "neutral"}


def _platform_context(db: Session, org: Organization) -> dict[str, Any] | None:
    canonical_org, reason = choose_canonical_platform_org(db)
    if canonical_org is None:
        return None

    owner_statuses = platform_owner_membership_statuses(db, org=org)
    is_platform_org = is_platform_like_org_name(org.name) or bool(owner_statuses) or org.id == canonical_org.id
    if not is_platform_org:
        return None

    status = "canonical_platform_org" if org.id == canonical_org.id else "legacy_platform_org"
    return {
        "status": status,
        "reason": reason,
        "canonical_org_id": str(canonical_org.id),
        "canonical_org_name": canonical_org.name,
        "owner_memberships": owner_statuses,
    }


def list_internal_organizations(db: Session, *, limit: int = 100) -> dict[str, Any]:
    month_start = month_start_utc()
    orgs = list(
        db.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(limit)
        ).scalars().all()
    )
    overview = {
        "total_organizations": len(orgs),
        "total_accounts": _count(db, User),
        "total_memberships": _count(db, Membership),
        "active_organizations": 0,
        "restricted_organizations": 0,
        "legacy_plan_type_counts": {},
        "effective_plan_counts": {},
        "scans_this_month": _current_month_scan_count(db),
        "quota_blocked_requests_this_month": _count(
            db,
            UsageLog,
            UsageLog.created_at >= month_start,
            UsageLog.status_code == 429,
        ),
        "recent_quota_blocked_requests": _recent_usage_logs(db, status_code=429, limit=10),
        "error_operations_this_month": _count(
            db,
            UsageLog,
            UsageLog.created_at >= month_start,
            UsageLog.status_code >= 500,
        ),
        "recent_error_operations": _recent_usage_logs(db, status_code_min=500, limit=10),
        "ai_usage_this_month": _sum(
            db,
            select(func.coalesce(func.sum(AIUsageMeter.usage_count), 0)).where(AIUsageMeter.period_start >= month_start),
        ),
    }
    summaries: list[dict[str, Any]] = []
    for org in orgs:
        entitlement = resolve_entitlement_for_org(db, org)
        entitlement_dict = asdict(entitlement)
        subscription = _current_subscription(db, org.id)
        reference = _billing_reference(db, org.id)
        platform_context = _platform_context(db, org)
        monthly_scans_used = _current_month_scan_count(db, org_id=org.id)
        account_count = _count(db, User, User.org_id == org.id)
        overview["legacy_plan_type_counts"][org.plan_type] = overview["legacy_plan_type_counts"].get(org.plan_type, 0) + 1
        overview["effective_plan_counts"][entitlement.effective_plan] = overview["effective_plan_counts"].get(entitlement.effective_plan, 0) + 1
        if entitlement.fail_closed or entitlement.subscription_state == "restricted":
            overview["restricted_organizations"] += 1
        else:
            overview["active_organizations"] += 1
        summaries.append(
            {
                "id": str(org.id),
                "name": org.name,
                "created_at": _serialize_dt(org.created_at),
                "legacy_plan_type": org.plan_type,
                "legacy_plan_status": org.plan_status,
                "plan_limit": org.plan_limit,
                "stripe_customer_id": org.stripe_customer_id,
                "stripe_subscription_id": org.stripe_subscription_id,
                "effective_entitlement": entitlement_dict,
                "subscription": {
                    "plan_name": subscription.plan_name,
                    "status": subscription.status,
                    "source": subscription.source,
                    "external_subscription_id": subscription.external_subscription_id,
                    "external_customer_id": subscription.external_customer_id,
                }
                if subscription
                else None,
                "billing_customer_reference": {
                    "provider": reference.provider,
                    "external_customer_id": reference.external_customer_id,
                    "billing_email": reference.billing_email,
                }
                if reference
                else None,
                "account_count": account_count,
                "member_count": _count(db, Membership, Membership.org_id == org.id),
                "pending_invite_count": _count(
                    db,
                    OrganizationInvite,
                    OrganizationInvite.org_id == org.id,
                    OrganizationInvite.status == "pending",
                ),
                "scan_count": _count(db, Scan, Scan.org_id == org.id),
                "monthly_scans_used": monthly_scans_used,
                "status_badge": _status_badge(entitlement_dict),
                "platform_context": platform_context,
            }
        )
    return {
        "read_only": True,
        "overview": overview,
        "recent_operator_actions": _recent_operator_actions(db, limit=20),
        "organizations": summaries,
    }


def get_internal_organization_detail(db: Session, *, org_id: uuid.UUID | str) -> dict[str, Any]:
    parsed = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
    org = db.get(Organization, parsed)
    if org is None:
        return {"found": False, "org_id": str(parsed), "read_only": True}

    memberships = list(
        db.execute(
            select(Membership).where(Membership.org_id == org.id).order_by(Membership.created_at.asc())
        ).scalars().all()
    )
    invites = list(
        db.execute(
            select(OrganizationInvite).where(OrganizationInvite.org_id == org.id).order_by(OrganizationInvite.created_at.desc()).limit(20)
        ).scalars().all()
    )
    scans = list(
        db.execute(
            select(Scan).where(Scan.org_id == org.id).order_by(Scan.created_at.desc()).limit(10)
        ).scalars().all()
    )
    usage = list(
        db.execute(
            select(UsageLog).where(UsageLog.org_id == org.id).order_by(UsageLog.created_at.desc()).limit(10)
        ).scalars().all()
    )
    signals = list(
        db.execute(
            select(MonitoringSignal).where(MonitoringSignal.org_id == org.id).order_by(MonitoringSignal.created_at.desc()).limit(10)
        ).scalars().all()
    )
    webhooks = list(
        db.execute(
            select(StripeWebhookEvent).where(StripeWebhookEvent.org_id == org.id).order_by(StripeWebhookEvent.processed_at.desc()).limit(10)
        ).scalars().all()
    )
    users = list(
        db.execute(
            select(User).where(User.org_id == org.id).order_by(User.created_at.asc())
        ).scalars().all()
    )
    subscription = _current_subscription(db, org.id)
    reference = _billing_reference(db, org.id)
    entitlement = resolve_entitlement_for_org(db, org)

    return {
        "found": True,
        "read_only": True,
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "plan_type": org.plan_type,
            "plan_status": org.plan_status,
            "plan_limit": org.plan_limit,
            "stripe_customer_id": org.stripe_customer_id,
            "stripe_subscription_id": org.stripe_subscription_id,
            "stripe_price_id": org.stripe_price_id,
            "stripe_price_lookup_key": org.stripe_price_lookup_key,
            "billing_email": org.billing_email,
            "current_period_end": _serialize_dt(org.current_period_end),
            "created_at": _serialize_dt(org.created_at),
        },
        "platform_context": _platform_context(db, org),
        "current_subscription": {
            "plan_name": subscription.plan_name,
            "status": subscription.status,
            "source": subscription.source,
            "external_subscription_id": subscription.external_subscription_id,
            "external_customer_id": subscription.external_customer_id,
            "current_period_end": _serialize_dt(subscription.current_period_end),
        }
        if subscription
        else None,
        "billing_customer_reference": {
            "provider": reference.provider,
            "external_customer_id": reference.external_customer_id,
            "billing_email": reference.billing_email,
        }
        if reference
        else None,
        "effective_entitlement": asdict(entitlement),
        "diagnostics": build_entitlement_diagnostics(db, org_id=org.id, webhook_limit=5),
        "accounts": [_account_snapshot(user) for user in users],
        "memberships": [_membership_snapshot(db, membership) for membership in memberships],
        "recent_invites": [_invite_snapshot(invite) for invite in invites],
        "recent_scans": [_recent_scan_snapshot(scan) for scan in scans],
        "recent_usage": [_usage_log_snapshot(log) for log in usage],
        "recent_operator_actions": _recent_operator_actions(db, org_id=org.id, limit=20),
        "recent_signals": [_signal_snapshot(signal) for signal in signals],
        "recent_webhooks": [
            {
                "id": str(event.id),
                "stripe_event_id": event.stripe_event_id,
                "event_type": event.event_type,
                "processing_status": event.processing_status,
                "error": event.error,
                "processed_at": _serialize_dt(event.processed_at),
            }
            for event in webhooks
        ],
        "manual_controls": [
            "operator_note",
            "cancel_pending_invite",
            "restrict_organization",
            "reactivate_organization",
            "manual_override_organization",
            "downgrade_organization_to_starter",
        ],
    }


def _profile_snapshot(profile: AccountProfile | None) -> dict[str, Any]:
    if profile is None:
        return {
            "legal_identity": {"first_name": None, "last_name": None, "business_company_name": None, "role_title": None, "country": None},
            "business_profile": {"business_email": None, "website": None, "address": None, "business_category": None},
            "display_profile": {"display_name": None, "workspace_name": None},
        }
    return {
        "legal_identity": {
            "first_name": profile.legal_first_name,
            "last_name": profile.legal_last_name,
            "business_company_name": profile.business_company_name,
            "role_title": profile.role_title,
            "country": profile.country,
        },
        "business_profile": {
            "business_email": profile.business_email,
            "website": profile.website,
            "address": profile.address,
            "business_category": profile.business_category,
        },
        "display_profile": {
            "display_name": profile.display_name,
            "workspace_name": profile.workspace_name,
        },
    }


def get_internal_ops_summary(db: Session) -> dict[str, Any]:
    org_payload = list_internal_organizations(db)
    total_users = _count(db, User)
    active_users = _count(db, User, User.is_active.is_(True), User.account_status == "active")
    suspended_users = _count(db, User, User.account_status == "suspended")
    subscription_rows = list(db.execute(select(Subscription).where(Subscription.is_current.is_(True))).scalars().all())
    subscription_breakdown: dict[str, int] = {"free": 0, "business": 0, "executive": 0, "enterprise": 0}
    subscription_states: dict[str, int] = {}
    for subscription in subscription_rows:
        plan = "free" if subscription.plan_name in {"starter", "free"} else subscription.plan_name
        subscription_breakdown[plan] = subscription_breakdown.get(plan, 0) + 1
        subscription_states[subscription.status] = subscription_states.get(subscription.status, 0) + 1

    paid_invoice_total = db.execute(select(func.coalesce(func.sum(BillingInvoice.amount_paid), 0))).scalar_one()
    return {
        "staff_roles_enabled": {key: bool(value) for key, value in internal_staff_roles().items()},
        "users": {
            "total": total_users,
            "active": active_users,
            "suspended": suspended_users,
            "disabled": _count(db, User, User.account_status == "disabled"),
            "closure_requested": _count(db, User, User.account_status == "closure_requested"),
        },
        "organizations": org_payload["overview"],
        "subscription_breakdown": subscription_breakdown,
        "subscription_states": subscription_states,
        "scan_usage": {"this_month": org_payload["overview"]["scans_this_month"]},
        "recent_users": list_internal_users(db, limit=8)["users"],
        "recent_scans": [
            _recent_scan_snapshot(scan)
            for scan in db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(8)).scalars().all()
        ],
        "recent_actions": _recent_operator_actions(db, limit=12),
        "revenue_summary": {
            "source": "stored_stripe_invoices",
            "amount_paid_minor_units": int(paid_invoice_total or 0),
            "estimated": False,
            "available": bool(paid_invoice_total),
        },
    }


def list_internal_users(db: Session, *, search: str | None = None, limit: int = 100) -> dict[str, Any]:
    stmt = select(User).order_by(User.created_at.desc()).limit(max(1, min(limit, 200)))
    if search and search.strip():
        needle = f"%{search.strip().lower()}%"
        stmt = select(User).where(func.lower(User.email).like(needle)).order_by(User.created_at.desc()).limit(max(1, min(limit, 200)))
    users = list(db.execute(stmt).scalars().all())
    rows: list[dict[str, Any]] = []
    for user in users:
        org = db.get(Organization, user.org_id)
        profile = db.execute(select(AccountProfile).where(AccountProfile.user_id == user.id).limit(1)).scalars().first()
        entitlement = resolve_entitlement_for_org(db, org, user_id=str(user.id)) if org else None
        rows.append({
            **_account_snapshot(user),
            "account_status": getattr(user, "account_status", "active"),
            "closure_requested_at": _serialize_dt(getattr(user, "closure_requested_at", None)),
            "disabled_at": _serialize_dt(getattr(user, "disabled_at", None)),
            "soft_deleted_at": _serialize_dt(getattr(user, "soft_deleted_at", None)),
            "organization_name": org.name if org else None,
            "profile": _profile_snapshot(profile),
            "subscription": {
                "effective_plan": entitlement.effective_plan if entitlement else None,
                "subscription_state": entitlement.subscription_state if entitlement else None,
                "monthly_scan_limit": entitlement.monthly_scan_limit if entitlement else None,
            },
            "usage": {
                "scan_count": _count(db, Scan, Scan.user_id == user.id),
                "monthly_scans_used": _current_month_scan_count(db, org_id=user.org_id),
            },
        })
    return {"read_only": True, "users": rows}


def get_internal_user(db: Session, *, user_id: str | uuid.UUID) -> User:
    parsed = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    user = db.get(User, parsed)
    if user is None:
        raise InternalOpsError("User not found")
    return user


def run_internal_user_state_action(db: Session, *, actor: AccountContext, user_id: str, action: str, reason: str) -> dict[str, Any]:
    user = get_internal_user(db, user_id=user_id)
    return set_user_account_state(db, actor=actor, user=user, action=action, reason=reason)


def list_internal_audit(db: Session, *, limit: int = 100) -> dict[str, Any]:
    return {"read_only": True, "actions": _recent_operator_actions(db, limit=max(1, min(limit, 200)))}


def internal_staff_snapshot(context: AccountContext) -> dict[str, Any]:
    role = internal_staff_role_for_context(context)
    return {
        "user_id": str(context.user.id),
        "email": context.user.email,
        "role": role,
        "permissions": {
            "read": role in {"owner", "manager", "assistant"},
            "manage_users": role in {"owner", "manager"},
            "manage_testers": role == "owner",
            "manage_staff": role == "owner",
        },
    }
