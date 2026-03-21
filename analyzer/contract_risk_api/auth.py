# contract_risk_api/auth.py
import hashlib
import hmac
import os
from typing import Set

from fastapi import Header, HTTPException, status


def _load_api_key_hashes() -> Set[str]:
    """
    Reads comma-separated SHA256 hex digests from env var API_KEY_HASHES.
    Example:
      API_KEY_HASHES="a7c3...ff,9b21...10"
    """
    raw = os.getenv("API_KEY_HASHES", "").strip()
    if not raw:
        return set()
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    Enforce X-API-Key header against configured API_KEY_HASHES (sha256 hex digests).
    - If API_KEY_HASHES is empty: reject (secure by default).
    """
    allowed_hashes = _load_api_key_hashes()
    if not allowed_hashes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API keys not configured",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    candidate = _sha256_hex(x_api_key).lower()
    # constant-time compare across possible hashes
    if not any(hmac.compare_digest(candidate, h) for h in allowed_hashes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )