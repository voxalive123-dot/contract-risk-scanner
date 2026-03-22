from __future__ import annotations

import os
import time
import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Header, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from crud import create_scan, create_usage_log, get_api_key_by_hash, touch_api_key_last_used
from analyzer.scorer import score_contract
from auth_keys import hash_api_key
from db import get_db


# ==========================================================
# TEST / CONTRACT CONSTANTS
# ==========================================================
MAX_TEXT_CHARS = 60_000
REQUEST_ID_HEADER = "X-Request-ID"
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "1") == "1"

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "0") == "1"
RATE_LIMIT_CAPACITY = int(os.getenv("RATE_LIMIT_CAPACITY", "60"))
RATE_LIMIT_REFILL_PER_SEC = float(os.getenv("RATE_LIMIT_REFILL_PER_SEC", "1.0"))

_BUCKETS: dict[str, dict[str, float]] = {}


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
# APP
# ==========================================================
app = FastAPI(
    title="VoxaRisk_INTELLIGENCE",
    version="1.0.0",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
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
    api_key_ctx = Depends(get_api_key_ctx),
):
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
        ip=http_request.client.host if http_request.client else "unknown",
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
    api_key_ctx = Depends(get_api_key_ctx),
):
    enforce_rate_limit(http_request)

    result = score_contract(
        request.text,
        include_findings=True,
        include_meta=True,
    )

    raw_meta = result.get("meta", {}) or {}
    word_count = len(request.text.split())

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
    }

    return {
        "risk_score": int(result.get("risk_score", 0)),
        "severity": str(result.get("severity", "LOW")),
        "flags": list(result.get("flags", [])),
        "findings": findings,
        "meta": meta,
    }
