from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, List
import json
import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import ApiKey, Organization, Scan, ScanNote, UsageLog



def _json_dump(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, default=str)


def _json_load(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _scan_note_payload(note: ScanNote) -> dict[str, Any]:
    return {
        "id": str(note.id),
        "scan_id": str(note.scan_id),
        "finding_rule_id": note.finding_rule_id,
        "note": note.note,
        "created_by": str(note.created_by_user_id) if note.created_by_user_id else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


def serialize_scan_summary(scan: Scan) -> dict[str, Any]:
    families = _json_load(scan.clause_families_detected, [])
    top_findings = _json_load(scan.top_findings_snapshot, [])
    return {
        "id": str(scan.id),
        "organization_id": str(scan.org_id),
        "user_id": str(scan.user_id) if scan.user_id else None,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "source_title": scan.source_title,
        "source_type": scan.source_type or "unknown",
        "risk_score": scan.risk_score,
        "severity": scan.severity,
        "confidence": float(scan.confidence or 0),
        "top_findings": top_findings,
        "clause_families_detected": families,
        "synthesis_patterns_triggered": _json_load(scan.synthesis_patterns_triggered, []),
        "report_export_state": scan.report_export_state or "absent",
    }


def serialize_scan_detail(scan: Scan) -> dict[str, Any]:
    payload = serialize_scan_summary(scan)
    payload.update(
        {
            "request_id": scan.request_id,
            "ruleset_version": scan.ruleset_version,
            "risk_density": float(scan.risk_density or 0),
            "scan_input_length": scan.scan_input_length,
            "context_profile_snapshot": _json_load(scan.context_profile_snapshot, None),
            "notes": [_scan_note_payload(note) for note in sorted(scan.notes, key=lambda item: item.created_at)],
        }
    )
    return payload

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def month_start_utc(reference_dt: datetime | None = None) -> datetime:
    current = reference_dt or utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


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
    *,
    scan_input_length: int = 0,
    source_title: Optional[str] = None,
    source_type: str = "unknown",
    severity: Optional[str] = None,
    top_findings_snapshot: Optional[list[dict[str, Any]]] = None,
    clause_families_detected: Optional[list[str]] = None,
    synthesis_patterns_triggered: Optional[list[str]] = None,
    context_profile_snapshot: Optional[dict[str, Any]] = None,
    report_export_state: str = "absent",
) -> Scan:
    scan = Scan(
        org_id=org_id,
        user_id=user_id,
        request_id=request_id,
        risk_score=int(risk_score),
        risk_density=float(risk_density),
        confidence=float(confidence),
        ruleset_version=ruleset_version,
        scan_input_length=int(scan_input_length or 0),
        source_title=source_title,
        source_type=source_type or "unknown",
        severity=severity,
        top_findings_snapshot=_json_dump(top_findings_snapshot or []),
        clause_families_detected=_json_dump(clause_families_detected or []),
        synthesis_patterns_triggered=_json_dump(synthesis_patterns_triggered or []),
        context_profile_snapshot=_json_dump(context_profile_snapshot),
        report_export_state=report_export_state or "absent",
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


def get_scan_for_org(db: Session, org_id: uuid.UUID, scan_id: uuid.UUID) -> Optional[Scan]:
    stmt = select(Scan).where(Scan.org_id == org_id, Scan.id == scan_id).limit(1)
    return db.execute(stmt).scalars().first()


def create_scan_note(
    db: Session,
    *,
    org_id: uuid.UUID,
    scan_id: uuid.UUID,
    created_by_user_id: Optional[uuid.UUID],
    note: str,
    finding_rule_id: Optional[str] = None,
) -> ScanNote:
    scan = get_scan_for_org(db, org_id, scan_id)
    if scan is None:
        raise ValueError("scan_not_found")

    scan_note = ScanNote(
        org_id=org_id,
        scan_id=scan_id,
        created_by_user_id=created_by_user_id,
        finding_rule_id=finding_rule_id,
        note=note.strip(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(scan_note)
    db.commit()
    db.refresh(scan_note)
    return scan_note
