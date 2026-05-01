from __future__ import annotations

from contextlib import asynccontextmanager
import os
import logging
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from tempfile import NamedTemporaryFile
from typing import Any

import pytesseract
import stripe
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from account_auth import (
    AccountConfigError,
    InvalidCredentialsError,
    InvalidMembershipError,
    account_session_config_missing_keys,
    account_context_for_user,
    account_context_from_token,
    authenticate_user,
    create_session_token,
    serialize_account_context,
)
from account_provisioning import (
    AccountTokenError,
    complete_password_token,
    request_password_reset,
    validate_password_token,
)
from ai_explain import AIExplainRequest, AIProviderError, generate_ai_explanation, openai_api_configured
from billing_portal import (
    BillingPortalConfigError,
    BillingPortalMissingCustomerError,
    BillingPortalProviderError,
    create_billing_portal_session,
)
from analyzer.scorer import score_contract
from auth_keys import hash_api_key
from crud import (
    count_scans_for_org_since,
    create_scan,
    create_scan_note,
    create_usage_log,
    get_api_key_by_hash,
    get_organization_by_id,
    get_scan_for_org,
    list_scans_for_org,
    month_start_utc,
    serialize_scan_detail,
    serialize_scan_summary,
    touch_api_key_last_used,
)
from db import get_db
from email_delivery import (
    EmailDeliveryConfigError,
    EmailDeliveryError,
    password_reset_url,
    send_password_reset_email,
)
from entitlement_spine import resolve_entitlement_for_org
from internal_ops import (
    InternalOpsConfigError,
    InternalOpsForbiddenError,
    create_internal_access_grant,
    get_internal_organization_detail,
    list_internal_access_grants,
    list_internal_organizations,
    revoke_internal_access_grant,
    require_internal_admin,
)
from internal_workflows import (
    InternalWorkflowInvalidActionError,
    InternalWorkflowNotFoundError,
    cancel_pending_invite,
    create_operator_note,
    downgrade_organization_to_starter,
    manual_override_organization,
    reactivate_organization,
    restrict_organization,
    workflow_view,
)
from models import StripeWebhookEvent
from owner_entitlement_grants import OwnerGrantError
from pdf_utils import PdfExtractionError, extract_text_from_pdf
from platform_owner import is_platform_owner_account
from stripe_reconciliation import reconcile_stripe_event
from stripe_billing import DEFAULT_PLAN_LIMIT, DEFAULT_PLAN_NAME
from team_invites import (
    TeamInviteError,
    TeamInvitePermissionError,
    TeamInviteTokenError,
    accept_team_invite,
    create_team_invite,
    team_snapshot,
)


# ==========================================================
# TEST / CONTRACT CONSTANTS
# ==========================================================
MAX_TEXT_CHARS = 60_000
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
REQUEST_ID_HEADER = "X-Request-ID"
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "1") == "1"

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "0") == "1"
RATE_LIMIT_CAPACITY = int(os.getenv("RATE_LIMIT_CAPACITY", "60"))
RATE_LIMIT_REFILL_PER_SEC = float(os.getenv("RATE_LIMIT_REFILL_PER_SEC", "1.0"))

_BUCKETS: dict[str, dict[str, float]] = {}
logger = logging.getLogger("voxarisk.api")

RESET_ERROR_STATUSES = {
    "missing_token": status.HTTP_400_BAD_REQUEST,
    "missing_token_or_password": status.HTTP_400_BAD_REQUEST,
    "token_not_found": status.HTTP_404_NOT_FOUND,
    "token_expired": status.HTTP_410_GONE,
    "token_already_used": status.HTTP_410_GONE,
    "password_validation_failed": status.HTTP_400_BAD_REQUEST,
    "payload_invalid": status.HTTP_400_BAD_REQUEST,
    "token_user_invalid": status.HTTP_403_FORBIDDEN,
}


def _normalize_choice(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _validate_optional_choice(value: str | None, allowed: set[str], message: str) -> str | None:
    if value is None:
        return None
    normalized = _normalize_choice(value)
    if normalized not in allowed:
        raise ValueError(message)
    return normalized


def reset_error_response(code: str) -> JSONResponse:
    return JSONResponse(
        status_code=RESET_ERROR_STATUSES.get(code, status.HTTP_400_BAD_REQUEST),
        content={
            "status": "failed",
            "code": code,
            "detail": "Password reset could not be completed.",
        },
    )


def session_config_error_response() -> JSONResponse:
    missing = account_session_config_missing_keys()
    logger.error(
        "account_session_config_missing",
        extra={
            "event": "account_session_config_missing",
            "reason": "session_config_missing",
            "missing_keys": ",".join(missing),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "failed",
            "code": "session_config_missing",
            "detail": "Account session configuration missing",
        },
    )

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

ALLOWED_SOURCE_TYPES = {"text", "pdf", "image", "unknown"}
ALLOWED_USER_ROLES = {
    "buyer",
    "supplier",
    "saas_provider",
    "agency",
    "consultant",
    "employer",
    "contractor",
    "reseller",
    "processor",
    "controller",
    "unknown",
}
ALLOWED_CONTRACT_TYPES = {
    "saas",
    "services",
    "consultancy",
    "procurement",
    "employment",
    "lease",
    "data_processing",
    "franchise",
    "logistics",
    "security_services",
    "healthcare",
    "unknown",
}
ALLOWED_COUNTERPARTY_PROFILES = {
    "larger_counterparty",
    "smaller_counterparty",
    "strategic_customer",
    "key_supplier",
    "public_sector",
    "regulated_party",
    "unknown",
}
ALLOWED_VALUE_CRITICALITY = {
    "low_value",
    "high_value",
    "business_critical",
    "recurring",
    "one_off",
    "pilot",
    "strategic_partnership",
    "unknown",
}
ALLOWED_DOCUMENT_POSITIONS = {
    "vendor_paper",
    "negotiated_draft",
    "renewal",
    "amendment",
    "supplier_terms",
    "customer_terms",
    "unknown",
}


def enforce_rate_limit(request: Request) -> None:
    if not RATE_LIMIT_ENABLED:
        return

    key = "global"
    now = time.time()

    bucket = _BUCKETS.get(key)
    if bucket is None:
        bucket = {
            "tokens": float(RATE_LIMIT_CAPACITY),
            "last_refill": now,
        }
        _BUCKETS[key] = bucket

    if RATE_LIMIT_REFILL_PER_SEC > 0:
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            float(RATE_LIMIT_CAPACITY),
            bucket["tokens"] + elapsed * RATE_LIMIT_REFILL_PER_SEC,
        )
        bucket["last_refill"] = now

    if bucket["tokens"] <= 0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    bucket["tokens"] -= 1
    _BUCKETS[key] = bucket


# ==========================================================
# REQUEST / RESPONSE MODELS
# ==========================================================
class AnalyzeRequest(BaseModel):
    text: str = Field(...)
    source_title: str | None = None
    source_type: str | None = None
    user_role: str | None = None
    contract_type: str | None = None
    counterparty_profile: str | None = None
    value_criticality: str | None = None
    document_position: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("text must be a string")
        if not value.strip():
            raise ValueError("text must not be empty")
        if len(value) > MAX_TEXT_CHARS:
            raise ValueError(f"maximum length is {MAX_TEXT_CHARS} characters")
        return value

    @field_validator("source_title")
    @classmethod
    def validate_source_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped[:255] if stripped else None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().replace("-", "_")
        if normalized not in ALLOWED_SOURCE_TYPES:
            raise ValueError("unsupported source_type")
        return normalized

    @field_validator("user_role")
    @classmethod
    def validate_user_role(cls, value: str | None) -> str | None:
        return _validate_optional_choice(value, ALLOWED_USER_ROLES, "unsupported user_role")

    @field_validator("contract_type")
    @classmethod
    def validate_contract_type(cls, value: str | None) -> str | None:
        return _validate_optional_choice(value, ALLOWED_CONTRACT_TYPES, "unsupported contract_type")

    @field_validator("counterparty_profile")
    @classmethod
    def validate_counterparty_profile(cls, value: str | None) -> str | None:
        return _validate_optional_choice(value, ALLOWED_COUNTERPARTY_PROFILES, "unsupported counterparty_profile")

    @field_validator("value_criticality")
    @classmethod
    def validate_value_criticality(cls, value: str | None) -> str | None:
        return _validate_optional_choice(value, ALLOWED_VALUE_CRITICALITY, "unsupported value_criticality")

    @field_validator("document_position")
    @classmethod
    def validate_document_position(cls, value: str | None) -> str | None:
        return _validate_optional_choice(value, ALLOWED_DOCUMENT_POSITIONS, "unsupported document_position")


class AnalyzeResponse(BaseModel):
    risk_score: int
    severity: str
    flags: list[str]

    model_config = ConfigDict(extra="forbid")


class AccountPasswordActionRequest(BaseModel):
    token: str = Field(...)
    password: str = Field(...)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_password_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and "password" not in data and "new_password" in data:
            normalized = dict(data)
            normalized["password"] = normalized.get("new_password")
            return normalized
        return data

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("token is required")
        return value.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or len(value) < 12:
            raise ValueError("password must be at least 12 characters")
        return value


class AccountPasswordTokenValidateRequest(BaseModel):
    token: str = Field(...)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("token is required")
        return value.strip()


class AccountPasswordResetRequest(BaseModel):
    email: str = Field(...)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("email is required")
        return value.strip().lower()


class AccountBillingPortalRequest(BaseModel):
    return_url: str | None = None

    @field_validator("return_url")
    @classmethod
    def validate_return_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        stripped = value.strip()
        if not stripped.startswith(("https://", "http://")):
            raise ValueError("return_url must be absolute HTTP(S)")
        return stripped


class ScanNoteRequest(BaseModel):
    note: str = Field(...)
    finding_rule_id: str | None = None

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        if not isinstance(value, str) or len(value.strip()) < 1:
            raise ValueError("note is required")
        return value.strip()[:4000]

    @field_validator("finding_rule_id")
    @classmethod
    def validate_finding_rule_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped[:120] if stripped else None


class InternalWorkflowReasonRequest(BaseModel):
    reason: str = Field(...)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not isinstance(value, str) or len(value.strip()) < 8:
            raise ValueError("a clear operator reason is required")
        return value.strip()


class InternalOrganizationOverrideRequest(InternalWorkflowReasonRequest):
    plan_type: str = Field(...)
    plan_status: str = Field(...)
    plan_limit: int = Field(...)

    @field_validator("plan_type")
    @classmethod
    def validate_plan_type(cls, value: str) -> str:
        if value.strip().lower() not in {"starter", "business", "executive", "enterprise"}:
            raise ValueError("unsupported override plan_type")
        return value.strip().lower()

    @field_validator("plan_status")
    @classmethod
    def validate_plan_status(cls, value: str) -> str:
        if value.strip().lower() not in {"active", "trialing", "manual_override", "restricted"}:
            raise ValueError("unsupported override plan_status")
        return value.strip().lower()

    @field_validator("plan_limit")
    @classmethod
    def validate_plan_limit(cls, value: int) -> int:
        if not isinstance(value, int) or value <= 0:
            raise ValueError("plan_limit must be positive")
        return value


class InternalAccessGrantCreateRequest(BaseModel):
    email: str = Field(...)
    granted_plan: str = Field(...)
    duration_days: int | None = Field(default=None)
    scan_quota_override: int | None = Field(default=None)
    reason: str = Field(default="family_beta_testing")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("email is required")
        return value.strip().lower()

    @field_validator("granted_plan")
    @classmethod
    def validate_granted_plan(cls, value: str) -> str:
        plan = value.strip().lower()
        if plan not in {"executive", "enterprise"}:
            raise ValueError("granted_plan must be executive or enterprise")
        return plan

    @field_validator("duration_days")
    @classmethod
    def validate_duration_days(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value <= 0 or value > 365:
            raise ValueError("duration_days must be between 1 and 365")
        return value

    @field_validator("scan_quota_override")
    @classmethod
    def validate_scan_quota_override(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value <= 0:
            raise ValueError("scan_quota_override must be positive")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("a clear grant reason is required")
        return value.strip()


class TeamInviteCreateRequest(BaseModel):
    email: str = Field(...)
    role: str = Field(default="member")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("email is required")
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("role is required")
        return value.strip().lower()


class TeamInviteAcceptRequest(BaseModel):
    token: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("token is required")
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("email is required")
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or len(value) < 12:
            raise ValueError("password must be at least 12 characters")
        return value


class AccountLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(...)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("email is required")
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("password is required")
        return value


# ==========================================================
# REAL API KEY DEPENDENCY
# ==========================================================
def get_api_key_ctx(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    raw_key = (x_api_key or "").strip()
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_key = get_api_key_by_hash(db, hash_api_key(raw_key))
    if not api_key or not api_key.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    touch_api_key_last_used(db, api_key)
    return api_key


def get_account_ctx(
    authorization: str = Header("", alias="Authorization"),
    db: Session = Depends(get_db),
):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing account session",
        )

    try:
        return account_context_from_token(db, token.strip())
    except AccountConfigError as exc:
        return session_config_error_response()
    except InvalidMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account membership is not valid",
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account session",
        ) from exc


def account_ctx_as_runtime_subject(account_ctx) -> SimpleNamespace:
    return SimpleNamespace(
        org_id=account_ctx.organization.id,
        user_id=account_ctx.user.id,
        id=None,
    )


def get_internal_admin_ctx(account_ctx=Depends(get_account_ctx)):
    try:
        require_internal_admin(account_ctx)
    except InternalOpsConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal operations access is not configured",
        ) from exc
    except InternalOpsForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal operations access denied: signed-in email is not configured as platform owner or internal admin",
        ) from exc
    return account_ctx

# ==========================================================
# HELPERS
# ==========================================================
def _client_ip(http_request: Request) -> str:
    return http_request.client.host if http_request.client else "unknown"


def enforce_ai_plan_access(
    *,
    db: Session,
    api_key_ctx: Any,
) -> str:
    org_id = getattr(api_key_ctx, "org_id", None)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "organization_context_missing",
                "current_plan": "starter",
                "feature": "ai_explain",
            },
        )

    org = get_organization_by_id(db, org_id)
    entitlement = resolve_entitlement_for_org(
        db,
        org,
        user_id=str(getattr(api_key_ctx, "user_id", "") or ""),
    )
    if not entitlement.ai_review_notes_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ai_explain_not_available_for_plan",
                "current_plan": entitlement.effective_plan,
                "feature": "ai_explain",
            },
        )

    return entitlement.effective_plan


def enforce_org_plan_quota(
    *,
    db: Session,
    api_key_ctx: Any,
) -> None:
    org_id = getattr(api_key_ctx, "org_id", None)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "organization_context_missing",
                "current_plan": DEFAULT_PLAN_NAME,
                "monthly_limit": DEFAULT_PLAN_LIMIT,
                "scans_used": 0,
            },
        )

    org = get_organization_by_id(db, org_id)
    entitlement = resolve_entitlement_for_org(
        db,
        org,
        user_id=str(getattr(api_key_ctx, "user_id", "") or ""),
    )
    effective_plan = entitlement.effective_plan
    monthly_limit = entitlement.monthly_scan_limit
    scans_used = count_scans_for_org_since(
        db=db,
        org_id=org_id,
        since_dt=month_start_utc(),
    )

    if is_platform_owner_account(
        db,
        user_id=str(getattr(api_key_ctx, "user_id", "") or ""),
        org_id=str(org_id),
    ):
        return

    if scans_used >= monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "monthly_scan_quota_exceeded",
                "current_plan": effective_plan,
                "monthly_limit": monthly_limit,
                "scans_used": scans_used,
            },
        )


def _context_from_request(request: AnalyzeRequest) -> dict[str, Any]:
    return {
        "user_role": request.user_role,
        "contract_type": request.contract_type,
        "counterparty_profile": request.counterparty_profile,
        "value_criticality": request.value_criticality,
        "document_position": request.document_position,
    }


def _derive_clause_families(findings: list[dict[str, Any]]) -> list[str]:
    families: set[str] = set()
    for finding in findings:
        category = str(finding.get("category") or "").lower()
        rule_id = str(finding.get("rule_id") or "").lower()
        title = str(finding.get("title") or "").lower()
        haystack = f"{category} {rule_id} {title}"
        if "indemn" in haystack:
            families.add("indemnity")
        if "liability" in haystack:
            families.add("liability")
        if "renewal" in haystack or "auto_renew" in haystack:
            families.add("auto-renewal")
        if category == "jurisdiction" or "forum" in haystack or "dispute" in haystack:
            families.add("jurisdiction")
        if category in {"data", "licensing"} or "data" in haystack:
            families.add("data use")
        if category == "termination" or "termination" in haystack:
            families.add("termination")
        if "price" in haystack or "pricing" in haystack or "fee increase" in haystack:
            families.add("price variation")
        if "suspension" in haystack or "suspend" in haystack:
            families.add("suspension")
        if "subcontract" in haystack:
            families.add("subcontracting")
        if category == "payment" or "payment" in haystack or "fee" in haystack:
            families.add("payment")
        if "confidential" in haystack:
            families.add("confidentiality")
        if category in {"control", "amendment", "audit"} or "control" in haystack or "variation" in haystack:
            families.add("dispute/control")
    return sorted(families)


def _scan_snapshot_fields(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings", []) or []
    meta = payload.get("meta", {}) or {}
    top_findings = [
        {
            "rule_id": finding.get("rule_id"),
            "title": finding.get("title"),
            "category": finding.get("category"),
            "severity": finding.get("severity"),
            "matched_text": finding.get("matched_text"),
            "contextual_emphasis": finding.get("contextual_emphasis"),
        }
        for finding in findings[:5]
    ]
    families = sorted(set(meta.get("rule_families_detected") or []) | set(_derive_clause_families(findings)))
    return {
        "severity": str(payload.get("severity", "LOW")),
        "top_findings_snapshot": top_findings,
        "clause_families_detected": families,
        "synthesis_patterns_triggered": list(meta.get("synthesis_patterns_triggered") or []),
        "context_profile_snapshot": meta.get("context_profile_used"),
    }


def _build_detailed_payload(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    result = score_contract(
        text,
        include_findings=True,
        include_meta=True,
        user_role=context.get("user_role"),
        contract_type=context.get("contract_type"),
        counterparty_profile=context.get("counterparty_profile"),
        value_criticality=context.get("value_criticality"),
        document_position=context.get("document_position"),
    )

    raw_meta = result.get("meta", {}) or {}
    word_count = len(text.split())

    raw_findings = result.get("findings", []) or []
    findings: list[dict[str, Any]] = []

    for f in raw_findings:
        if not isinstance(f, dict):
            continue

        rule_id = f.get("rule_id") or f.get("id")
        title = f.get("title") or ""

        if (
            rule_id == "termination_for_convenience_counterparty"
            and "without notice" in str(f.get("matched_text", "")).lower()
        ):
            rule_id = "termination_without_notice"
            title = "Termination without notice"

        findings.append(
            {
                "rule_id": rule_id,
                "title": title,
                "category": f.get("category"),
                "severity": f.get("severity"),
                "matched_text": f.get("matched_text"),
                "matched_location": f.get("matched_location"),
                "context_note": f.get("context_note"),
                "rationale": f.get("rationale"),
                "contextual_emphasis": f.get("contextual_emphasis"),
            }
        )

    meta = {
        "ruleset_version": raw_meta.get("ruleset_version", "unknown"),
        "max_possible_score": 100,
        "normalized_score": raw_meta.get("normalized_score", 0),
        "word_count": word_count,
        "risk_density_per_1000_words": round(
            float(raw_meta.get("risk_density", 0.0)) * 1000, 4
        )
        if word_count > 0
        else 0.0,
        "scan_char_limit": raw_meta.get("scan_char_limit"),
        "scanned_chars": raw_meta.get("scanned_chars"),
        "confidence": raw_meta.get("confidence", 0.0),
        "score_adjustments": raw_meta.get("score_adjustments", []),
        "matched_rule_count": raw_meta.get("matched_rule_count", len(findings)),
        "suppressed_rule_count": raw_meta.get("suppressed_rule_count", 0),
        "contradiction_count": raw_meta.get("contradiction_count", 0),
        "top_risks": raw_meta.get("top_risks", []),
        "rule_families_detected": raw_meta.get("rule_families_detected", []),
        "synthesis_patterns_triggered": raw_meta.get("synthesis_patterns_triggered", []),
        "context_profile_used": raw_meta.get("context_profile_used"),
        "context_confidence": raw_meta.get("context_confidence"),
        "context_limitations": raw_meta.get("context_limitations", []),
        "context_emphasis": raw_meta.get("context_emphasis", []),
    }

    return {
        "risk_score": int(result.get("risk_score", 0)),
        "severity": str(result.get("severity", "LOW")),
        "flags": list(result.get("flags", [])),
        "findings": findings,
        "meta": meta,
    }


def _persist_analysis(
    *,
    db: Session,
    api_key_ctx: Any,
    http_request: Request,
    endpoint: str,
    payload: dict[str, Any],
    source_title: str | None = None,
    source_type: str = "unknown",
    scan_input_length: int = 0,
    report_export_state: str = "absent",
) -> None:
    req_id = getattr(http_request.state, "request_id", "unknown")
    meta = payload.get("meta", {}) or {}

    create_scan(
        db=db,
        org_id=api_key_ctx.org_id if api_key_ctx else None,
        user_id=api_key_ctx.user_id,
        request_id=req_id,
        risk_score=int(payload.get("risk_score", 0)),
        risk_density=float(meta.get("risk_density_per_1000_words", 0.0)) / 1000.0,
        confidence=float(meta.get("confidence", 0.0)),
        ruleset_version=str(meta.get("ruleset_version", "unknown")),
        scan_input_length=scan_input_length,
        source_title=source_title,
        source_type=source_type,
        report_export_state=report_export_state,
        **_scan_snapshot_fields(payload),
    )

    create_usage_log(
        db=db,
        org_id=api_key_ctx.org_id if api_key_ctx else None,
        user_id=api_key_ctx.user_id,
        api_key_id=getattr(api_key_ctx, "id", None),
        endpoint=endpoint,
        request_id=req_id,
        method="POST",
        ip=_client_ip(http_request),
        duration_ms=0,
        status_code=200,
    )


def _write_temp_file(data: bytes, suffix: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return Path(tmp.name)


def _extract_text_from_image(image_path: Path) -> tuple[str, float]:
    try:
        image = Image.open(image_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Image could not be opened") from exc

    try:
        text = pytesseract.image_to_string(image).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Image OCR failed") from exc

    if not text:
        raise HTTPException(status_code=400, detail="No readable text detected in image")

    return text, 0.65


# ==========================================================
# APP
# ==========================================================
@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    missing = account_session_config_missing_keys()
    if missing:
        logger.critical(
            "account_session_config_invalid_startup",
            extra={
                "event": "account_session_config_invalid_startup",
                "reason": "session_config_missing",
                "missing_keys": ",".join(missing),
            },
        )
    else:
        logger.info(
            "account_session_config_validated",
            extra={"event": "account_session_config_validated", "reason": "configured"},
        )
    yield


app = FastAPI(
    title="VoxaRisk_INTELLIGENCE",
    version="1.0.0",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    if request.url.path in {
        "/account/password/reset/complete",
        "/account/password/reset/validate",
    }:
        reason = "payload_invalid"
        errors = exc.errors()
        if any("token" in {str(part) for part in error.get("loc", [])} for error in errors):
            reason = "missing_token"
        elif any("password" in {str(part) for part in error.get("loc", [])} for error in errors):
            reason = "password_validation_failed"
        logger.info(
            "password_reset_consume_failed",
            extra={"event": "password_reset_consume_failed", "reason": reason},
        )
        return reset_error_response(reason)
    return await request_validation_exception_handler(request, exc)


# ==========================================================
# MIDDLEWARE
# ==========================================================
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


# ==========================================================
# HEALTH
# ==========================================================
@app.get("/")
def root(request: Request):
    return {
        "status": "Contract Risk API running",
        "request_id": getattr(request.state, "request_id", None),
    }


@app.post("/account/login")
def account_login(
    request: AccountLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        context = authenticate_user(db, email=request.email, password=request.password)
        token = create_session_token(context.user)
    except AccountConfigError as exc:
        return session_config_error_response()
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except InvalidMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account membership is not valid",
        ) from exc

    return {
        "access_token": token,
        "token_type": "bearer",
        "account": serialize_account_context(context),
    }

@app.post("/account/password/setup")
def account_password_setup(
    request: AccountPasswordActionRequest,
    db: Session = Depends(get_db),
):
    try:
        context = complete_password_token(
            db,
            raw_token=request.token,
            password=request.password,
            purpose="setup",
        )
        token = create_session_token(context.user)
    except AccountConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account session configuration missing",
        ) from exc
    except AccountTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password setup token is invalid or expired",
        ) from exc

    return {
        "access_token": token,
        "token_type": "bearer",
        "account": serialize_account_context(context),
    }


@app.post("/account/password/reset/request")
def account_password_reset_request(
    request: AccountPasswordResetRequest,
    db: Session = Depends(get_db),
):
    reset_token = request_password_reset(db, email=request.email)
    if reset_token is None:
        logger.info(
            "password_reset_request_no_match",
            extra={"event": "password_reset_request_no_match", "email": request.email},
        )
        return {"status": "reset_requested"}

    logger.info(
        "password_reset_token_created",
        extra={"event": "password_reset_token_created", "email": request.email},
    )
    reset_url = password_reset_url(reset_token)
    provider = "smtp"
    logger.info(
        "password_reset_delivery_started",
        extra={
            "event": "password_reset_delivery_started",
            "email": request.email,
            "provider": provider,
        },
    )
    try:
        provider = send_password_reset_email(to_email=request.email, reset_url=reset_url)
    except EmailDeliveryConfigError as exc:
        logger.error(
            "password_reset_delivery_failed",
            extra={
                "event": "password_reset_delivery_failed",
                "email": request.email,
                "provider": provider,
                "error": str(exc),
            },
        )
        return {"status": "reset_requested"}
    except EmailDeliveryError as exc:
        logger.error(
            "password_reset_delivery_failed",
            extra={
                "event": "password_reset_delivery_failed",
                "email": request.email,
                "provider": provider,
                "error": str(exc),
            },
        )
        return {"status": "reset_requested"}

    logger.info(
        "password_reset_delivery_succeeded",
        extra={
            "event": "password_reset_delivery_succeeded",
            "email": request.email,
            "provider": provider,
        },
    )
    return {"status": "reset_requested"}


@app.post("/account/password/reset/validate")
def account_password_reset_validate(
    request: AccountPasswordTokenValidateRequest,
    db: Session = Depends(get_db),
):
    token_status = validate_password_token(db, raw_token=request.token, purpose="reset")
    if token_status == "valid":
        logger.info(
            "password_reset_token_validated",
            extra={"event": "password_reset_token_validated", "reason": "valid"},
        )
        return {"valid": True, "code": "valid"}

    logger.info(
        "password_reset_token_validation_failed",
        extra={"event": "password_reset_token_validation_failed", "reason": token_status},
    )
    return reset_error_response(token_status)


@app.post("/account/password/reset/complete")
def account_password_reset_complete(
    request: AccountPasswordActionRequest,
    db: Session = Depends(get_db),
):
    try:
        context = complete_password_token(
            db,
            raw_token=request.token,
            password=request.password,
            purpose="reset",
        )
        token = create_session_token(context.user)
    except AccountConfigError as exc:
        logger.error(
            "password_reset_consume_failed",
            extra={
                "event": "password_reset_consume_failed",
                "reason": "session_config_missing",
            },
        )
        return session_config_error_response()
    except AccountTokenError as exc:
        logger.info(
            "password_reset_consume_failed",
            extra={
                "event": "password_reset_consume_failed",
                "reason": getattr(exc, "reason", "invalid_token"),
            },
        )
        return reset_error_response(getattr(exc, "reason", "payload_invalid"))

    logger.info(
        "password_reset_consume_succeeded",
        extra={
            "event": "password_reset_consume_succeeded",
            "user_id": str(context.user.id),
            "org_id": str(context.organization.id),
        },
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "account": serialize_account_context(context),
    }
@app.get("/internal/ops/organizations")
def internal_ops_organizations(
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    return list_internal_organizations(db)


@app.get("/internal/ops/organizations/{org_id}")
def internal_ops_organization_detail(
    org_id: str,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    return get_internal_organization_detail(db, org_id=org_id)


@app.get("/internal/ops/access-grants")
def internal_ops_access_grants(
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    return list_internal_access_grants(db)


@app.post("/internal/ops/access-grants")
def internal_ops_access_grants_create(
    request: InternalAccessGrantCreateRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        return create_internal_access_grant(
            db,
            actor=_internal_ctx,
            email=request.email,
            granted_plan=request.granted_plan,
            duration_days=request.duration_days,
            reason=request.reason,
            scan_quota_override=request.scan_quota_override,
        )
    except OwnerGrantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/ops/access-grants/{grant_id}/revoke")
def internal_ops_access_grants_revoke(
    grant_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        return revoke_internal_access_grant(
            db,
            actor=_internal_ctx,
            grant_id=grant_id,
            reason=request.reason,
        )
    except OwnerGrantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/internal/ops/organizations/{org_id}/workflow")
def internal_ops_organization_workflow(
    org_id: str,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        return workflow_view(db, org_id=org_id)
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/internal/ops/organizations/{org_id}/workflow/notes")
def internal_ops_operator_note(
    org_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = create_operator_note(
            db,
            actor=_internal_ctx,
            org_id=org_id,
            reason=request.reason,
        )
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "operator_note_recorded", "action": action}


@app.post("/internal/ops/invites/{invite_id}/cancel")
def internal_ops_invite_cancel(
    invite_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = cancel_pending_invite(
            db,
            actor=_internal_ctx,
            invite_id=invite_id,
            reason=request.reason,
        )
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "invite_cancelled", "action": action}


@app.post("/internal/ops/organizations/{org_id}/restrict")
def internal_ops_org_restrict(
    org_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = restrict_organization(db, actor=_internal_ctx, org_id=org_id, reason=request.reason)
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "organization_restricted", "action": action}


@app.post("/internal/ops/organizations/{org_id}/reactivate")
def internal_ops_org_reactivate(
    org_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = reactivate_organization(db, actor=_internal_ctx, org_id=org_id, reason=request.reason)
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "organization_reactivated", "action": action}


@app.post("/internal/ops/organizations/{org_id}/manual-override")
def internal_ops_org_manual_override(
    org_id: str,
    request: InternalOrganizationOverrideRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = manual_override_organization(
            db,
            actor=_internal_ctx,
            org_id=org_id,
            reason=request.reason,
            plan_type=request.plan_type,
            plan_status=request.plan_status,
            plan_limit=request.plan_limit,
        )
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "organization_manual_override_applied", "action": action}


@app.post("/internal/ops/organizations/{org_id}/downgrade")
def internal_ops_org_downgrade(
    org_id: str,
    request: InternalWorkflowReasonRequest,
    _internal_ctx=Depends(get_internal_admin_ctx),
    db: Session = Depends(get_db),
):
    try:
        action = downgrade_organization_to_starter(db, actor=_internal_ctx, org_id=org_id, reason=request.reason)
    except InternalWorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InternalWorkflowInvalidActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "organization_downgraded_to_starter", "action": action}

@app.get("/account/team")
def account_team(
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    return team_snapshot(db, account_ctx)


@app.post("/account/team/invites")
def account_team_invite_create(
    request: TeamInviteCreateRequest,
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    try:
        result = create_team_invite(
            db,
            context=account_ctx,
            invited_email=request.email,
            role=request.role,
        )
    except TeamInvitePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account role cannot create this team invite",
        ) from exc
    except TeamInviteError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "status": "invite_created",
        "invite": {
            "id": str(result.invite.id),
            "email": result.invite.invited_email,
            "role": result.invite.role,
            "status": result.invite.status,
            "expires_at": result.invite.expires_at.isoformat(),
        },
        "invite_token": result.raw_token,
        "accept_url": result.accept_url,
        "authority_notice": "Invite acceptance creates membership only; organisation entitlement remains resolver-backed.",
    }


@app.post("/account/team/invites/accept")
def account_team_invite_accept(
    request: TeamInviteAcceptRequest,
    db: Session = Depends(get_db),
):
    try:
        accepted = accept_team_invite(
            db,
            raw_token=request.token,
            email=request.email,
            password=request.password,
        )
        context = account_context_for_user(db, accepted.user)
        token = create_session_token(context.user)
    except (InvalidMembershipError, InvalidCredentialsError, TeamInviteTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team invite is invalid, expired, or cannot be accepted",
        ) from exc

    return {
        "access_token": token,
        "token_type": "bearer",
        "account": serialize_account_context(context),
    }
@app.post("/account/billing/portal")
def account_billing_portal(
    request: AccountBillingPortalRequest,
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    try:
        portal_session = create_billing_portal_session(
            db,
            context=account_ctx,
            return_url=request.return_url,
        )
    except BillingPortalMissingCustomerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing portal is not available for this organisation",
        ) from exc
    except BillingPortalConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing portal configuration is not available",
        ) from exc
    except BillingPortalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Billing portal provider is temporarily unavailable",
        ) from exc

    return {
        "url": portal_session.url,
        "organization_id": portal_session.organization_id,
    }

@app.get("/account/me")
def account_me(account_ctx=Depends(get_account_ctx)):
    return serialize_account_context(account_ctx)


@app.post("/account/ai/explain")
def account_ai_explain(
    request: AIExplainRequest,
    db: Session = Depends(get_db),
    account_ctx=Depends(get_account_ctx),
):
    runtime_subject = account_ctx_as_runtime_subject(account_ctx)
    enforce_ai_plan_access(db=db, api_key_ctx=runtime_subject)

    if not openai_api_configured():
        return {
            "status": "disabled",
            "reason": "openai_api_key_not_configured",
        }

    try:
        response = generate_ai_explanation(request)
    except AIProviderError:
        return {
            "status": "unavailable",
            "reason": "ai_provider_error",
        }

    return response.model_dump(mode="json")


@app.get("/account/scans")
def account_scan_history(
    offset: int = 0,
    limit: int = 25,
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    bounded_offset = max(int(offset or 0), 0)
    bounded_limit = min(max(int(limit or 25), 1), 100)
    scans = list_scans_for_org(
        db,
        account_ctx.organization.id,
        offset=bounded_offset,
        limit=bounded_limit,
    )
    family_counts: dict[str, int] = {}
    serialized = [serialize_scan_summary(scan) for scan in scans]
    for scan in serialized:
        for family in scan.get("clause_families_detected", []) or []:
            family_counts[str(family)] = family_counts.get(str(family), 0) + 1
    recurring_families = [
        {"family": family, "count": count}
        for family, count in sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {"scans": serialized, "recurring_clause_families": recurring_families}


@app.get("/account/scans/{scan_id}")
def account_scan_detail(
    scan_id: uuid.UUID,
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    scan = get_scan_for_org(db, account_ctx.organization.id, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return serialize_scan_detail(scan)


@app.post("/account/scans/{scan_id}/notes")
def account_scan_note_create(
    scan_id: uuid.UUID,
    request: ScanNoteRequest,
    account_ctx=Depends(get_account_ctx),
    db: Session = Depends(get_db),
):
    try:
        note = create_scan_note(
            db,
            org_id=account_ctx.organization.id,
            scan_id=scan_id,
            created_by_user_id=account_ctx.user.id,
            note=request.note,
            finding_rule_id=request.finding_rule_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from exc
    scan = get_scan_for_org(db, account_ctx.organization.id, scan_id)
    return {"note": serialize_scan_detail(scan)["notes"][-1] if scan else {"id": str(note.id)}}


@app.post("/account/logout")
def account_logout():
    return {"status": "signed_out"}


@app.post("/account/analyze_detailed")
def account_analyze_detailed(
    request: AnalyzeRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    account_ctx=Depends(get_account_ctx),
):
    runtime_subject = account_ctx_as_runtime_subject(account_ctx)
    enforce_org_plan_quota(db=db, api_key_ctx=runtime_subject)
    enforce_rate_limit(http_request)

    payload = _build_detailed_payload(request.text, _context_from_request(request))
    _persist_analysis(
        db=db,
        api_key_ctx=runtime_subject,
        http_request=http_request,
        endpoint="/account/analyze_detailed",
        payload=payload,
        source_title=request.source_title,
        source_type=request.source_type or "text",
        scan_input_length=len(request.text),
    )
    return payload


@app.post("/account/analyze_pdf")
async def account_analyze_pdf(
    file: UploadFile = File(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    account_ctx=Depends(get_account_ctx),
):
    runtime_subject = account_ctx_as_runtime_subject(account_ctx)
    enforce_org_plan_quota(db=db, api_key_ctx=runtime_subject)
    enforce_rate_limit(http_request)

    if file.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded PDF exceeds size limit")

    temp_path: Path | None = None
    try:
        temp_path = _write_temp_file(data, ".pdf")
        extraction = extract_text_from_pdf(str(temp_path))

        if not extraction.text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in PDF")

        payload = _build_detailed_payload(extraction.text)
        payload["extraction_method"] = extraction.extraction_method
        payload["confidence_hint"] = extraction.confidence_hint
        payload["source_type"] = "pdf"
        payload["page_count"] = extraction.page_count
        payload["has_extractable_text"] = extraction.has_extractable_text

        _persist_analysis(
            db=db,
            api_key_ctx=runtime_subject,
            http_request=http_request,
            endpoint="/account/analyze_pdf",
            payload=payload,
            source_title=file.filename,
            source_type="pdf",
            scan_input_length=len(extraction.text),
        )
        return payload
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/account/analyze_image")
async def account_analyze_image(
    file: UploadFile = File(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    account_ctx=Depends(get_account_ctx),
):
    runtime_subject = account_ctx_as_runtime_subject(account_ctx)
    enforce_org_plan_quota(db=db, api_key_ctx=runtime_subject)
    enforce_rate_limit(http_request)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are supported",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded image exceeds size limit")

    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

    temp_path: Path | None = None
    try:
        temp_path = _write_temp_file(data, suffix)
        text, confidence_hint = _extract_text_from_image(temp_path)

        payload = _build_detailed_payload(text)
        payload["extraction_method"] = "ocr"
        payload["confidence_hint"] = confidence_hint
        payload["source_type"] = "image"

        _persist_analysis(
            db=db,
            api_key_ctx=runtime_subject,
            http_request=http_request,
            endpoint="/account/analyze_image",
            payload=payload,
            source_title=file.filename,
            source_type="image",
            scan_input_length=len(text),
        )
        return payload
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/ai/explain")
def ai_explain(
    request: AIExplainRequest,
    db: Session = Depends(get_db),
    api_key_ctx=Depends(get_api_key_ctx),
):
    enforce_ai_plan_access(db=db, api_key_ctx=api_key_ctx)

    if not openai_api_configured():
        return {
            "status": "disabled",
            "reason": "openai_api_key_not_configured",
        }

    try:
        response = generate_ai_explanation(request)
    except AIProviderError:
        return {
            "status": "unavailable",
            "reason": "ai_provider_error",
        }

    return response.model_dump(mode="json")


# ==========================================================
# ANALYZE
# ==========================================================
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    api_key_ctx=Depends(get_api_key_ctx),
):
    enforce_org_plan_quota(db=db, api_key_ctx=api_key_ctx)
    enforce_rate_limit(http_request)

    result = score_contract(request.text, **_context_from_request(request))
    result_meta = result.get("meta", {}) or {}
    risk_score = int(result.get("risk_score", 0))
    req_id = getattr(http_request.state, "request_id", "unknown")

    create_scan(
        db=db,
        org_id=api_key_ctx.org_id if api_key_ctx else None,
        user_id=api_key_ctx.user_id,
        request_id=req_id,
        risk_score=risk_score,
        risk_density=float(result_meta.get("risk_density", 0.0)),
        confidence=float(result_meta.get("confidence", 0.0)),
        ruleset_version=result_meta.get("ruleset_version", "unknown"),
        scan_input_length=len(request.text),
        source_title=request.source_title,
        source_type=request.source_type or "text",
        severity=str(result.get("severity", "LOW")),
        top_findings_snapshot=[],
        clause_families_detected=list(result_meta.get("rule_families_detected", [])),
        synthesis_patterns_triggered=list(result_meta.get("synthesis_patterns_triggered", [])),
        context_profile_snapshot=result_meta.get("context_profile_used"),
    )

    create_usage_log(
        db=db,
        org_id=api_key_ctx.org_id if api_key_ctx else None,
        user_id=api_key_ctx.user_id,
        api_key_id=getattr(api_key_ctx, "id", None),
        endpoint="/analyze",
        request_id=req_id,
        method="POST",
        ip=_client_ip(http_request),
        duration_ms=0,
        status_code=200,
    )

    return {
        "risk_score": risk_score,
        "severity": str(result.get("severity", "LOW")),
        "flags": list(result.get("flags", [])),
    }


# ==========================================================
# ANALYZE DETAILED
# ==========================================================
@app.post("/analyze_detailed")
def analyze_detailed(
    request: AnalyzeRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    api_key_ctx=Depends(get_api_key_ctx),
):
    enforce_org_plan_quota(db=db, api_key_ctx=api_key_ctx)
    enforce_rate_limit(http_request)

    payload = _build_detailed_payload(request.text, _context_from_request(request))
    _persist_analysis(
        db=db,
        api_key_ctx=api_key_ctx,
        http_request=http_request,
        endpoint="/analyze_detailed",
        payload=payload,
        source_title=request.source_title,
        source_type=request.source_type or "text",
        scan_input_length=len(request.text),
    )
    return payload


# ==========================================================
# ANALYZE PDF
# ==========================================================
@app.post("/analyze_pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    api_key_ctx=Depends(get_api_key_ctx),
):
    enforce_org_plan_quota(db=db, api_key_ctx=api_key_ctx)
    enforce_rate_limit(http_request)

    if file.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded PDF exceeds size limit")

    temp_path: Path | None = None
    try:
        temp_path = _write_temp_file(data, ".pdf")
        extraction = extract_text_from_pdf(str(temp_path))

        if not extraction.text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in PDF")

        payload = _build_detailed_payload(extraction.text)
        payload["extraction_method"] = extraction.extraction_method
        payload["confidence_hint"] = extraction.confidence_hint
        payload["source_type"] = "pdf"
        payload["page_count"] = extraction.page_count
        payload["has_extractable_text"] = extraction.has_extractable_text

        _persist_analysis(
            db=db,
            api_key_ctx=api_key_ctx,
            http_request=http_request,
            endpoint="/analyze_pdf",
            payload=payload,
            source_title=file.filename,
            source_type="pdf",
            scan_input_length=len(extraction.text),
        )
        return payload

    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


# ==========================================================
# ANALYZE IMAGE
# ==========================================================
@app.post("/analyze_image")
async def analyze_image(
    file: UploadFile = File(...),
    http_request: Request = None,
    db: Session = Depends(get_db),
    api_key_ctx=Depends(get_api_key_ctx),
):
    enforce_org_plan_quota(db=db, api_key_ctx=api_key_ctx)
    enforce_rate_limit(http_request)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are supported",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded image exceeds size limit")

    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

    temp_path: Path | None = None
    try:
        temp_path = _write_temp_file(data, suffix)
        text, confidence_hint = _extract_text_from_image(temp_path)

        payload = _build_detailed_payload(text)
        payload["extraction_method"] = "ocr"
        payload["confidence_hint"] = confidence_hint
        payload["source_type"] = "image"

        _persist_analysis(
            db=db,
            api_key_ctx=api_key_ctx,
            http_request=http_request,
            endpoint="/analyze_image",
            payload=payload,
            source_title=file.filename,
            source_type="image",
            scan_input_length=len(text),
        )
        return payload
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret not configured",
        )

    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    event_id = str(event.get("id"))
    event_type = str(event.get("type", "unknown"))

    existing_event = db.execute(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
    ).scalars().first()
    if existing_event:
        return {"status": "duplicate", "event_id": event_id}

    payload_object = event.get("data", {}).get("object", {}) or {}
    result = reconcile_stripe_event(
        db,
        event_id=event_id,
        event_type=event_type,
        payload_object=payload_object,
    )

    return {
        "status": result.processing_status,
        "event_id": event_id,
        "matched_org_id": str(result.org.id) if result.org else None,
    }
