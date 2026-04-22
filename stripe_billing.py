from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Organization, Plan


DEFAULT_PLAN_NAME = "starter"
DEFAULT_PLAN_LIMIT = 5
PLAN_QUOTAS: dict[str, int] = {
    "starter": 5,
    "business": 100,
    "executive": 500,
    "enterprise": 2000,
}

PRICE_LOOKUP_KEY_TO_PLAN: dict[str, str] = {
    "business_monthly_gbp": "business",
    "business_yearly_gbp": "business",
    "executive_monthly_gbp": "executive",
    "executive_yearly_gbp": "executive",
    "enterprise_monthly_gbp": "enterprise",
    "enterprise_yearly_gbp": "enterprise",
}

PAID_ACTIVE_STATUSES = {"active", "trialing"}
RESTRICTED_STATUSES = {
    "past_due",
    "unpaid",
    "canceled",
    "incomplete",
    "incomplete_expired",
}


def map_lookup_key_to_plan(lookup_key: str | None) -> str | None:
    if not lookup_key:
        return None
    return PRICE_LOOKUP_KEY_TO_PLAN.get(lookup_key)


def get_effective_plan_name(org: Organization | None) -> str:
    if org is None:
        return DEFAULT_PLAN_NAME

    plan_type = (org.plan_type or DEFAULT_PLAN_NAME).strip().lower()
    plan_status = (org.plan_status or "").strip().lower()

    if plan_type in {"business", "executive", "enterprise"} and plan_status in PAID_ACTIVE_STATUSES:
        return plan_type

    if plan_type == DEFAULT_PLAN_NAME:
        return DEFAULT_PLAN_NAME

    return DEFAULT_PLAN_NAME


def get_effective_plan_limit(org: Organization | None) -> int:
    effective_plan = get_effective_plan_name(org)
    return PLAN_QUOTAS.get(effective_plan, DEFAULT_PLAN_LIMIT)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _parse_period_end(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _extract_subscription_price(price_holder: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not isinstance(price_holder, dict):
        return None, None

    price = price_holder.get("price")
    if not isinstance(price, dict):
        return None, None

    return _string_or_none(price.get("id")), _string_or_none(price.get("lookup_key"))


def _first_subscription_item_price(items: Any) -> tuple[str | None, str | None]:
    if not isinstance(items, dict):
        return None, None

    data = items.get("data")
    if not isinstance(data, list) or not data:
        return None, None

    first_item = data[0]
    if not isinstance(first_item, dict):
        return None, None

    return _extract_subscription_price(first_item)


def _first_invoice_line_price(lines: Any) -> tuple[str | None, str | None]:
    if not isinstance(lines, dict):
        return None, None

    data = lines.get("data")
    if not isinstance(data, list) or not data:
        return None, None

    first_line = data[0]
    if not isinstance(first_line, dict):
        return None, None

    return _extract_subscription_price(first_line)


def extract_event_context(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    customer_id = _string_or_none(payload.get("customer"))
    subscription_id = _string_or_none(payload.get("subscription"))
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata_org_id = _string_or_none(metadata.get("org_id"))

    billing_email = None
    customer_details = payload.get("customer_details")
    if isinstance(customer_details, dict):
        billing_email = _string_or_none(customer_details.get("email"))
    if billing_email is None:
        billing_email = _string_or_none(payload.get("customer_email"))
    if billing_email is None:
        billing_email = _string_or_none(payload.get("email"))

    price_id: str | None = None
    price_lookup_key: str | None = None
    subscription_status = _string_or_none(payload.get("status"))
    current_period_end = _parse_period_end(payload.get("current_period_end"))

    if event_type.startswith("customer.subscription."):
        subscription_id = subscription_id or _string_or_none(payload.get("id"))
        price_id, price_lookup_key = _first_subscription_item_price(payload.get("items"))
    elif event_type == "invoice.payment_failed":
        price_id, price_lookup_key = _first_invoice_line_price(payload.get("lines"))
        subscription_status = subscription_status or "past_due"
    elif event_type == "checkout.session.completed":
        price_id = _string_or_none(metadata.get("price_id"))
        price_lookup_key = _string_or_none(metadata.get("price_lookup_key"))

    if event_type == "customer.subscription.deleted":
        subscription_status = "canceled"

    return {
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "price_id": price_id,
        "price_lookup_key": price_lookup_key,
        "billing_email": billing_email,
        "metadata_org_id": metadata_org_id,
        "subscription_status": subscription_status,
        "current_period_end": current_period_end,
    }


def get_plan_record(db: Session, plan_name: str) -> Plan | None:
    stmt = select(Plan).where(Plan.name == plan_name).limit(1)
    return db.execute(stmt).scalars().first()


def resolve_org_match(
    db: Session,
    *,
    metadata_org_id: str | None,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
) -> Organization | None:
    if metadata_org_id:
        try:
            parsed = uuid.UUID(metadata_org_id)
        except ValueError:
            parsed = None

        if parsed:
            stmt = select(Organization).where(Organization.id == parsed).limit(1)
            org = db.execute(stmt).scalars().first()
            if org:
                return org

    if stripe_customer_id:
        stmt = (
            select(Organization)
            .where(Organization.stripe_customer_id == stripe_customer_id)
            .limit(1)
        )
        org = db.execute(stmt).scalars().first()
        if org:
            return org

    if stripe_subscription_id:
        stmt = (
            select(Organization)
            .where(Organization.stripe_subscription_id == stripe_subscription_id)
            .limit(1)
        )
        return db.execute(stmt).scalars().first()

    return None


def bind_billing_identity(org: Organization, context: dict[str, Any]) -> None:
    if context.get("customer_id"):
        org.stripe_customer_id = context["customer_id"]
    if context.get("subscription_id"):
        org.stripe_subscription_id = context["subscription_id"]
    if context.get("price_id"):
        org.stripe_price_id = context["price_id"]
    if context.get("price_lookup_key"):
        org.stripe_price_lookup_key = context["price_lookup_key"]
    if context.get("billing_email"):
        org.billing_email = context["billing_email"]
    if context.get("current_period_end") is not None:
        org.current_period_end = context["current_period_end"]


def apply_paid_entitlement(
    db: Session,
    org: Organization,
    *,
    plan_name: str,
    subscription_status: str,
    context: dict[str, Any],
) -> None:
    bind_billing_identity(org, context)
    org.plan_type = plan_name
    org.plan_status = subscription_status

    plan_record = get_plan_record(db, plan_name)
    if plan_record:
        org.plan_id = plan_record.id
        org.plan_limit = PLAN_QUOTAS.get(plan_name, plan_record.monthly_scan_quota)
    else:
        org.plan_id = None
        org.plan_limit = PLAN_QUOTAS.get(plan_name, DEFAULT_PLAN_LIMIT)


def apply_default_entitlement(
    db: Session,
    org: Organization,
    *,
    subscription_status: str,
    context: dict[str, Any],
) -> None:
    bind_billing_identity(org, context)
    org.plan_type = DEFAULT_PLAN_NAME
    org.plan_status = subscription_status

    starter_plan = get_plan_record(db, DEFAULT_PLAN_NAME)
    if starter_plan:
        org.plan_id = starter_plan.id
        org.plan_limit = PLAN_QUOTAS.get(DEFAULT_PLAN_NAME, starter_plan.monthly_scan_quota)
    else:
        org.plan_id = None
        org.plan_limit = DEFAULT_PLAN_LIMIT
