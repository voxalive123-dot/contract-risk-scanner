import hashlib
import hmac
from typing import Optional, Tuple


API_KEY_HEADER = "X-API-Key"


def hash_api_key(raw_key: str) -> str:
    """
    Hash the *full* raw API key with SHA-256.
    Store/compare only the hex digest.
    """
    raw_key = raw_key.strip()
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def parse_api_key_header(value: Optional[str]) -> Optional[str]:
    """
    Extract raw key from header value.
    """
    if not value:
        return None
    v = value.strip()
    return v if v else None


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
