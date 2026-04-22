from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytesseract
import stripe
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from models import StripeWebhookEvent
from pdf_utils import PdfExtractionError, extract_text_from_pdf
from stripe_billing import (
    PAID_ACTIVE_STATUSES,
    RESTRICTED_STATUSES,
    apply_default_entitlement,
    apply_paid_entitlement,
    bind_billing_identity,
    extract_event_context,
    get_effective_plan_limit,
    get_effective_plan_name,
    map_lookup_key_to_plan,
    resolve_org_match,
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


# ==========================================================
# HELPERS
# ==========================================================
def _client_ip(http_request: Request) -> str:
    return http_request.client.host if http_request.client else "unknown"


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
                "current_plan": "starter",
                "monthly_limit": get_effective_plan_limit(None),
                "scans_used": 0,
            },
        )

    org = get_organization_by_id(db, org_id)
    effective_plan = get_effective_plan_name(org)
    monthly_limit = get_effective_plan_limit(org)
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
    context = extract_event_context(event_type, payload_object)
    plan_name = map_lookup_key_to_plan(context.get("price_lookup_key"))
    org = resolve_org_match(
        db,
        metadata_org_id=context.get("metadata_org_id"),
        stripe_customer_id=context.get("customer_id"),
        stripe_subscription_id=context.get("subscription_id"),
    )

    processing_status = "processed"
    error: str | None = None

    if org is None:
        processing_status = "unmatched"
    elif event_type == "checkout.session.completed":
        bind_billing_identity(org, context)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_failed",
    }:
        subscription_status = context.get("subscription_status")
        if subscription_status in PAID_ACTIVE_STATUSES:
            if plan_name is None:
                processing_status = "unmatched"
                error = "Unable to determine VoxaRisk plan from Stripe price lookup key."
            else:
                apply_paid_entitlement(
                    db,
                    org,
                    plan_name=plan_name,
                    subscription_status=subscription_status,
                    context=context,
                )
        elif subscription_status in RESTRICTED_STATUSES:
            apply_default_entitlement(
                db,
                org,
                subscription_status=subscription_status,
                context=context,
            )
        else:
            processing_status = "ignored"
    else:
        processing_status = "ignored"

    event_row = StripeWebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        processing_status=processing_status,
        org_id=org.id if org else None,
        stripe_customer_id=context.get("customer_id"),
        stripe_subscription_id=context.get("subscription_id"),
        stripe_price_id=context.get("price_id"),
        stripe_price_lookup_key=context.get("price_lookup_key"),
        billing_email=context.get("billing_email"),
        error=error,
    )
    db.add(event_row)
    db.commit()

    return {
        "status": processing_status,
        "event_id": event_id,
        "matched_org_id": str(org.id) if org else None,
    }
