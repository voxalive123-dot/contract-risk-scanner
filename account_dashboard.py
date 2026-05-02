from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import AccountContext, hash_password, serialize_account_context, verify_password
from crud import month_start_utc
from models import (
    AccountProfile,
    BillingInvoice,
    InternalOperatorAction,
    Scan,
    Subscription,
    User,
)


LEGAL_FIELDS = (
    "legal_first_name",
    "legal_last_name",
    "business_company_name",
    "role_title",
    "country",
)
PROFILE_FIELDS = LEGAL_FIELDS + (
    "business_email",
    "website",
    "address",
    "business_category",
    "display_name",
    "workspace_name",
)


class AccountDashboardError(Exception):
    pass


class PasswordChangeError(AccountDashboardError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dt(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _clean(value: Any, *, max_len: int = 255) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped[:max_len] if stripped else None


def _current_subscription(db: Session, org_id) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org_id, Subscription.is_current.is_(True))
        .order_by(Subscription.updated_at.desc(), Subscription.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _profile_for_context(db: Session, context: AccountContext, *, create: bool = False) -> AccountProfile | None:
    stmt = select(AccountProfile).where(AccountProfile.user_id == context.user.id).limit(1)
    profile = db.execute(stmt).scalars().first()
    if profile is None and create:
        profile = AccountProfile(user_id=context.user.id, org_id=context.organization.id)
        db.add(profile)
        db.flush()
    return profile


def serialize_profile(profile: AccountProfile | None) -> dict[str, Any]:
    if profile is None:
        payload = {field: None for field in PROFILE_FIELDS}
    else:
        payload = {field: getattr(profile, field) for field in PROFILE_FIELDS}
    payload["legal_identity_complete"] = all(payload.get(field) for field in LEGAL_FIELDS)
    payload["identity_notice"] = "Legal identity is the internal billing and compliance truth. Display profile is workspace-facing only."
    return payload


def _invoice_payload(invoice: BillingInvoice) -> dict[str, Any]:
    return {
        "id": str(invoice.id),
        "provider": invoice.provider,
        "external_invoice_id": invoice.external_invoice_id,
        "date": _dt(invoice.invoice_date or invoice.created_at),
        "amount_due": invoice.amount_due,
        "amount_paid": invoice.amount_paid,
        "currency": invoice.currency,
        "status": invoice.status,
        "hosted_invoice_url": invoice.hosted_invoice_url,
        "invoice_pdf": invoice.invoice_pdf,
    }


def list_account_invoices(db: Session, context: AccountContext, *, limit: int = 24) -> list[dict[str, Any]]:
    stmt = (
        select(BillingInvoice)
        .where(BillingInvoice.org_id == context.organization.id)
        .order_by(BillingInvoice.invoice_date.desc().nullslast(), BillingInvoice.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    return [_invoice_payload(invoice) for invoice in db.execute(stmt).scalars().all()]


def account_summary(db: Session, context: AccountContext) -> dict[str, Any]:
    month_start = month_start_utc()
    monthly_usage = int(
        db.execute(
            select(func.count())
            .select_from(Scan)
            .where(Scan.org_id == context.organization.id, Scan.created_at >= month_start)
        ).scalar_one()
    )
    total_scans = int(db.execute(select(func.count()).select_from(Scan).where(Scan.org_id == context.organization.id)).scalar_one())
    latest_scan = db.execute(
        select(Scan).where(Scan.org_id == context.organization.id).order_by(Scan.created_at.desc()).limit(1)
    ).scalars().first()
    subscription = _current_subscription(db, context.organization.id)
    profile = _profile_for_context(db, context)
    invoices = list_account_invoices(db, context)
    serialized = serialize_account_context(context)
    serialized["user"]["account_status"] = getattr(context.user, "account_status", "active")
    serialized["usage"] = {
        "month_start": _dt(month_start),
        "monthly_scans_used": monthly_usage,
        "monthly_scan_limit": context.entitlement.monthly_scan_limit,
        "scan_limit_remaining": max(context.entitlement.monthly_scan_limit - monthly_usage, 0),
        "total_scans": total_scans,
        "latest_scan_at": _dt(latest_scan.created_at) if latest_scan else None,
    }
    serialized["subscription"] = {
        "plan_name": subscription.plan_name if subscription else context.entitlement.effective_plan,
        "status": subscription.status if subscription else context.entitlement.subscription_state,
        "provider": subscription.provider if subscription else None,
        "current_period_end": _dt(subscription.current_period_end) if subscription else None,
        "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
        "source": subscription.source if subscription else context.entitlement.source,
    }
    serialized["billing"] = {
        "billing_email": context.organization.billing_email,
        "stripe_customer_id_present": bool(context.organization.stripe_customer_id),
        "invoices": invoices,
        "invoice_storage_status": "stored" if invoices else "no_stored_invoices",
        "payment_history": invoices,
    }
    serialized["profile"] = serialize_profile(profile)
    return serialized


def update_account_profile(db: Session, context: AccountContext, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _profile_for_context(db, context, create=True)
    assert profile is not None
    before = serialize_profile(profile)
    values: dict[str, str | None] = {}
    for field in PROFILE_FIELDS:
        max_len = 4000 if field == "address" else 320 if field == "business_email" else 255
        values[field] = _clean(payload.get(field), max_len=max_len)
    missing = [field for field in LEGAL_FIELDS if not values.get(field)]
    if missing:
        raise AccountDashboardError(f"Legal identity fields required: {', '.join(missing)}")
    for field, value in values.items():
        setattr(profile, field, value)
    profile.org_id = context.organization.id
    profile.updated_at = _now()
    db.add(profile)
    db.add(
        InternalOperatorAction(
            actor_user_id=context.user.id,
            org_id=context.organization.id,
            target_type="account_profile",
            target_id=str(context.user.id),
            action_type="account_profile_updated",
            reason="User updated own account profile",
            before_json=json.dumps(before, sort_keys=True, default=str),
            after_json=json.dumps(serialize_profile(profile), sort_keys=True, default=str),
        )
    )
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)


def change_account_password(db: Session, context: AccountContext, *, current_password: str, new_password: str, confirm_password: str) -> dict[str, Any]:
    if not verify_password(current_password or "", context.user.password_hash):
        raise PasswordChangeError("Current password is not valid")
    if new_password != confirm_password:
        raise PasswordChangeError("New password confirmation does not match")
    if len(new_password or "") < 12:
        raise PasswordChangeError("New password must be at least 12 characters")
    context.user.password_hash = hash_password(new_password)
    db.add(context.user)
    db.add(
        InternalOperatorAction(
            actor_user_id=context.user.id,
            org_id=context.organization.id,
            target_type="user",
            target_id=str(context.user.id),
            action_type="account_password_changed",
            reason="User changed own password",
            before_json=None,
            after_json='{"password_hash":"updated"}',
        )
    )
    db.commit()
    return {"status": "password_changed"}


def request_account_closure(db: Session, context: AccountContext, *, reason: str | None = None) -> dict[str, Any]:
    before = {
        "is_active": context.user.is_active,
        "account_status": getattr(context.user, "account_status", "active"),
    }
    context.user.account_status = "closure_requested"
    context.user.closure_requested_at = _now()
    context.user.is_active = False
    db.add(context.user)
    db.add(
        InternalOperatorAction(
            actor_user_id=context.user.id,
            org_id=context.organization.id,
            target_type="user",
            target_id=str(context.user.id),
            action_type="account_closure_requested",
            reason=(reason or "User requested account closure").strip()[:4000],
            before_json=json.dumps(before, sort_keys=True),
            after_json=json.dumps({"is_active": False, "account_status": "closure_requested"}, sort_keys=True),
        )
    )
    db.commit()
    return {
        "status": "closure_requested",
        "retention_notice": "Critical billing, scan, and audit records are retained. The account is disabled rather than hard deleted.",
    }


def set_user_account_state(
    db: Session,
    *,
    actor: AccountContext,
    user: User,
    action: str,
    reason: str,
) -> dict[str, Any]:
    before = {
        "is_active": user.is_active,
        "account_status": getattr(user, "account_status", "active"),
        "disabled_at": _dt(getattr(user, "disabled_at", None)),
        "soft_deleted_at": _dt(getattr(user, "soft_deleted_at", None)),
    }
    now = _now()
    if action == "suspend":
        user.account_status = "suspended"
        user.is_active = False
    elif action == "reactivate":
        user.account_status = "active"
        user.is_active = True
        user.disabled_at = None
        user.soft_deleted_at = None
    elif action == "disable":
        user.account_status = "disabled"
        user.is_active = False
        user.disabled_at = now
    elif action == "soft_delete":
        user.account_status = "soft_deleted"
        user.is_active = False
        user.soft_deleted_at = now
    else:
        raise AccountDashboardError("Unsupported user account action")
    after = {
        "is_active": user.is_active,
        "account_status": user.account_status,
        "disabled_at": _dt(user.disabled_at),
        "soft_deleted_at": _dt(user.soft_deleted_at),
    }
    db.add(user)
    db.add(
        InternalOperatorAction(
            actor_user_id=actor.user.id,
            org_id=user.org_id,
            target_type="user",
            target_id=str(user.id),
            action_type=f"user_{action}",
            reason=reason.strip(),
            before_json=json.dumps(before, sort_keys=True),
            after_json=json.dumps(after, sort_keys=True),
        )
    )
    db.commit()
    return {"status": f"user_{action}", "user_id": str(user.id), "account_status": user.account_status}
