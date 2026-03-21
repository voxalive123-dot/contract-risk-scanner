from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import ApiKey, Organization, Scan, UsageLog


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# -------------------------
# API KEY LOOKUP / TOUCH
# -------------------------
def get_api_key_by_hash(db: Session, key_hash: str) -> Optional[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.key_hash == key_hash).limit(1)
    return db.execute(stmt).scalars().first()


def touch_api_key_last_used(db: Session, api_key: ApiKey) -> None:
    api_key.last_used_at = utcnow()
    db.add(api_key)
    db.commit()


# -------------------------
# ORGANIZATION / QUOTA HELPERS
# -------------------------
def get_organization_by_id(db: Session, org_id: uuid.UUID) -> Optional[Organization]:
    stmt = select(Organization).where(Organization.id == org_id).limit(1)
    return db.execute(stmt).scalars().first()


def count_scans_for_org_since(
    db: Session,
    org_id: uuid.UUID,
    since_dt: datetime,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Scan)
        .where(
            Scan.org_id == org_id,
            Scan.created_at >= since_dt,
        )
    )
    return int(db.execute(stmt).scalar_one())


# -------------------------
# PERSISTENCE WRITES
# -------------------------
def create_scan(
    db: Session,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    request_id: str,
    risk_score: int,
    risk_density: float,
    confidence: float,
    ruleset_version: str,
) -> Scan:
    scan = Scan(
        org_id=org_id,
        user_id=user_id,
        request_id=request_id,
        risk_score=int(risk_score),
        risk_density=float(risk_density),
        confidence=float(confidence),
        ruleset_version=ruleset_version,
        created_at=utcnow(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def create_usage_log(
    db: Session,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    api_key_id: Optional[uuid.UUID],
    endpoint: str,
    request_id: str,
    method: str,
    ip: str,
    duration_ms: int,
    status_code: int,
) -> UsageLog:
    log = UsageLog(
        org_id=org_id,
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        request_id=request_id,
        method=method,
        ip=ip,
        duration_ms=int(duration_ms),
        status_code=int(status_code),
        created_at=utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# -------------------------
# OPTIONAL: READ HELPERS
# -------------------------
def count_scans_for_org(db: Session, org_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Scan).where(Scan.org_id == org_id)
    return int(db.execute(stmt).scalar_one())


def list_scans_for_org(
    db: Session,
    org_id: uuid.UUID,
    offset: int,
    limit: int,
) -> List[Scan]:
    stmt = (
        select(Scan)
        .where(Scan.org_id == org_id)
        .order_by(Scan.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
