from __future__ import annotations

import os
import logging
import time
import uuid
from pathlib import Path
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
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from account_auth import (
    AccountConfigError,
    InvalidCredentialsError,
    InvalidMembershipError,
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
    create_usage_log,
    get_api_key_by_hash,
    get_organization_by_id,
    month_start_utc,
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
    get_internal_organization_detail,
    list_internal_organizations,
    require_internal_admin,
)
from internal_workflows import (
    InternalWorkflowInvalidActionError,
    InternalWorkflowNotFoundError,
    cancel_pending_invite,
    create_operator_note,
    workflow_view,
)
from models import StripeWebhookEvent
from pdf_utils import PdfExtractionError, extract_text_from_pdf
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

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
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


class AnalyzeResponse(BaseModel):
    risk_score: int
    severity: str
    flags: list[str]

    model_config = ConfigDict(extra="forbid")


class AccountPasswordActionRequest(BaseModel):
    token: str = Field(...)
    password: str = Field(...)

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


class InternalWorkflowReasonRequest(BaseModel):
    reason: str = Field(...)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not isinstance(value, str) or len(value.strip()) < 8:
            raise ValueError("a clear operator reason is required")
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account session configuration missing",
        ) from exc
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
    entitlement = resolve_entitlement_for_org(db, org)
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
    entitlement = resolve_entitlement_for_org(db, org)
    effective_plan = entitlement.effective_plan
    monthly_limit = entitlement.monthly_scan_limit
    scans_used = count_scans_for_org_since(
        db=db,
        org_id=org_id,
        since_dt=month_start_utc(),
    )

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


def _build_detailed_payload(text: str) -> dict[str, Any]:
    result = score_contract(
        text,
        include_findings=True,
        include_meta=True,
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
                "rationale": f.get("rationale"),
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
app = FastAPI(
    title="VoxaRisk_INTELLIGENCE",
    version="1.0.0",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
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
    if request.url.path == "/account/password/reset/complete":
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
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Password reset token is invalid or expired"},
        )
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account session configuration missing",
        ) from exc
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account session configuration missing",
        ) from exc
    except AccountTokenError as exc:
        logger.info(
            "password_reset_consume_failed",
            extra={
                "event": "password_reset_consume_failed",
                "reason": getattr(exc, "reason", "invalid_token"),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or expired",
        ) from exc

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


@app.post("/account/logout")
def account_logout():
    return {"status": "signed_out"}


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

    result = score_contract(request.text)
    risk_score = int(result.get("risk_score", 0))
    req_id = getattr(http_request.state, "request_id", "unknown")

    create_scan(
        db=db,
        org_id=api_key_ctx.org_id if api_key_ctx else None,
        user_id=api_key_ctx.user_id,
        request_id=req_id,
        risk_score=risk_score,
        risk_density=float(result.get("risk_density", 0.0)),
        confidence=float(result.get("confidence", 0.0)),
        ruleset_version=result.get("ruleset_version", "unknown"),
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

    payload = _build_detailed_payload(request.text)
    _persist_analysis(
        db=db,
        api_key_ctx=api_key_ctx,
        http_request=http_request,
        endpoint="/analyze_detailed",
        payload=payload,
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
