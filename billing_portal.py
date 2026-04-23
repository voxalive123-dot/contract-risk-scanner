from __future__ import annotations

import os
from dataclasses import dataclass

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from account_auth import AccountContext
from models import BillingCustomerReference


DEFAULT_BILLING_PORTAL_RETURN_URL = "http://localhost:3000/account"


class BillingPortalError(Exception):
    pass


class BillingPortalConfigError(BillingPortalError):
    pass


class BillingPortalMissingCustomerError(BillingPortalError):
    pass


class BillingPortalProviderError(BillingPortalError):
    pass


@dataclass(frozen=True)
class BillingPortalSession:
    url: str
    customer_id: str
    organization_id: str


def _configured_return_url(return_url: str | None) -> str:
    candidate = (return_url or os.getenv("BILLING_PORTAL_RETURN_URL") or DEFAULT_BILLING_PORTAL_RETURN_URL).strip()
    if not candidate.startswith(("https://", "http://")):
        raise BillingPortalConfigError("Billing portal return URL must be absolute HTTP(S)")
    return candidate


def _stripe_secret_key() -> str:
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        raise BillingPortalConfigError("STRIPE_SECRET_KEY is not configured")
    return secret


def _billing_customer_reference(db: Session, context: AccountContext) -> BillingCustomerReference:
    stmt = (
        select(BillingCustomerReference)
        .where(
            BillingCustomerReference.org_id == context.organization.id,
            BillingCustomerReference.provider == "stripe",
        )
        .limit(2)
    )
    references = list(db.execute(stmt).scalars().all())
    if len(references) != 1 or not references[0].external_customer_id:
        raise BillingPortalMissingCustomerError("No deterministic billing customer reference found")
    return references[0]


def create_billing_portal_session(
    db: Session,
    *,
    context: AccountContext,
    return_url: str | None = None,
) -> BillingPortalSession:
    reference = _billing_customer_reference(db, context)
    stripe.api_key = _stripe_secret_key()

    try:
        session = stripe.billing_portal.Session.create(
            customer=reference.external_customer_id,
            return_url=_configured_return_url(return_url),
        )
    except Exception as exc:  # Stripe SDK raises provider-specific subclasses.
        raise BillingPortalProviderError("Billing portal session could not be created") from exc

    url = None
    if isinstance(session, dict):
        url = session.get("url")
    else:
        url = getattr(session, "url", None)

    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise BillingPortalProviderError("Billing portal provider did not return a valid URL")

    return BillingPortalSession(
        url=url,
        customer_id=reference.external_customer_id,
        organization_id=str(context.organization.id),
    )