from sqlalchemy.orm import Session
from models import Scan, UsageLog


def create_scan(
    db: Session,
    *,
    org_id,
    user_id,
    request_id,
    risk_score: int,
    risk_density: float,
    confidence: float,
    ruleset_version: str,
):
    scan = Scan(
        org_id=org_id,
        user_id=user_id,
        request_id=request_id,
        risk_score=risk_score,
        risk_density=risk_density,
        confidence=confidence,
        ruleset_version=ruleset_version,
    )
    db.add(scan)
    db.flush()  # assigns scan.id
    return scan


def create_usage_log(
    db: Session,
    *,
    org_id,
    user_id,
    api_key_id,
    endpoint: str,
    method: str,
    request_id,
    ip,
    duration_ms,
    status_code,
):
    row = UsageLog(
        org_id=org_id,
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        request_id=request_id,
        ip=ip,
        duration_ms=duration_ms,
        status_code=status_code,
    )
    db.add(row)
    return row
