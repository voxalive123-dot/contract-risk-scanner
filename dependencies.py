from __future__ import annotations

import uuid
import logging
from typing import Tuple

from fastapi import HTTPException, status, Header
from sqlalchemy.orm import Session

# ==========================================================
# LOGGER
# ==========================================================

logger = logging.getLogger("voxa.dependencies")

# ==========================================================
# API KEY (STRUCTURED MOCK — REQUIRED)
# ==========================================================

class MockAPIKey:
    def __init__(self, key: str):
        self.key = key
        self.org_id = uuid.uuid4()
        self.user_id = uuid.uuid4()   # <-- ADD THIS LINE ONLY

def get_api_key(x_api_key: str = Header(...)) -> MockAPIKey:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    return MockAPIKey(x_api_key)

# ==========================================================
# SCAN QUOTA (TEMP BYPASS)
# ==========================================================


def check_scan_quota(db: Session, org_id: uuid.UUID) -> None:
    # TEMP: bypass quota checks during backend hardening
    return


# ==========================================================
# RATE LIMIT SETTINGS (STUB)
# ==========================================================


def get_rate_limit_settings(
    db: Session, org_id: uuid.UUID
) -> Tuple[int, int, int, int, str]:
    return (10, 60, 100, 3600, "open")


# ==========================================================
# RATE LIMIT CHECK (DISABLED)
# ==========================================================


def check_rate_limit(db: Session, org_id: uuid.UUID) -> None:
    # TEMP: fully disabled for stability
    return
