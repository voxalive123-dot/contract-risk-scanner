from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional, List
import json
import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from decision_intelligence import (
    AGGREGATE_INSIGHTS_GOVERNANCE,
    DEFAULT_ORG_POLICY,
    DECISION_REASON_CODES,
    FINDING_DECISION_STATUSES,
    SCAN_DECISION_STATES,
    SECTOR_INTELLIGENCE_PACKS,
    context_bucket_from_scan,
    validate_policy_values,
)
from models import (
    ApiKey,
    DecisionAuditLog,
    DecisionNote,
    FindingDecisionStatus,
    Organization,
    OrganizationRiskPolicy,
    OrganizationRiskPolicyAudit,
    Scan,
    ScanDecisionState,
    ScanNote,
    UsageLog,
)



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


def _scan_decision_payload(decision: ScanDecisionState | None) -> dict[str, Any]:
    return {
        "state": decision.state if decision else "pending",
        "reason_code": decision.reason_code if decision else None,
        "note": decision.note if decision else None,
        "updated_by": str(decision.updated_by_user_id) if decision and decision.updated_by_user_id else None,
        "updated_at": decision.updated_at.isoformat() if decision and decision.updated_at else None,
    }


def _finding_decision_payload(decision: FindingDecisionStatus) -> dict[str, Any]:
    return {
        "finding_id": decision.finding_id,
        "status": decision.status,
        "reason_code": decision.reason_code,
        "note": decision.note,
        "updated_by": str(decision.updated_by_user_id) if decision.updated_by_user_id else None,
        "updated_at": decision.updated_at.isoformat() if decision.updated_at else None,
    }


def _decision_note_payload(note: DecisionNote) -> dict[str, Any]:
    return {
        "id": str(note.id),
        "scan_id": str(note.scan_id),
        "finding_id": note.finding_id,
        "reason_code": note.reason_code,
        "note": note.note,
        "created_by": str(note.created_by_user_id) if note.created_by_user_id else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
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
            "decision_intelligence_snapshot": _json_load(scan.decision_intelligence_snapshot, None),
            "decision_state": _scan_decision_payload(scan.scan_decision),
            "finding_decisions": [
                _finding_decision_payload(decision)
                for decision in sorted(scan.finding_decisions, key=lambda item: item.created_at)
            ],
            "notes": [_scan_note_payload(note) for note in sorted(scan.notes, key=lambda item: item.created_at)],
        }
    )
    top_findings = payload.get("top_findings") or []
    explicit_decisions = {item["finding_id"]: item for item in payload.get("finding_decisions", [])}
    payload["finding_decisions"] = [
        explicit_decisions.get(
            str(finding.get("rule_id") or finding.get("id") or ""),
            {
                "finding_id": str(finding.get("rule_id") or finding.get("id") or ""),
                "status": "unresolved",
                "reason_code": None,
                "note": None,
                "updated_by": None,
                "updated_at": None,
            },
        )
        for finding in top_findings
    ] + [
        decision
        for decision in payload.get("finding_decisions", [])
        if decision.get("finding_id") not in {str(f.get("rule_id") or f.get("id") or "") for f in top_findings}
    ]
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
    decision_intelligence_snapshot: Optional[dict[str, Any]] = None,
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
        decision_intelligence_snapshot=_json_dump(decision_intelligence_snapshot),
        created_at=utcnow(),
    )
    db.add(scan)
    db.flush()
    db.add(
        ScanDecisionState(
            org_id=org_id,
            scan_id=scan.id,
            state="pending",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
    )
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


# -------------------------
# DECISION INTELLIGENCE HELPERS
# -------------------------
def get_org_risk_policy(db: Session, org_id: uuid.UUID, *, create_defaults: bool = True) -> dict[str, str]:
    rows = list(
        db.execute(
            select(OrganizationRiskPolicy).where(OrganizationRiskPolicy.org_id == org_id)
        ).scalars().all()
    )
    policy = {row.policy_key: row.policy_value for row in rows}
    missing = [key for key in DEFAULT_ORG_POLICY if key not in policy]
    if create_defaults and missing:
        for key in missing:
            row = OrganizationRiskPolicy(
                org_id=org_id,
                policy_key=key,
                policy_value=DEFAULT_ORG_POLICY[key],
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(row)
            policy[key] = row.policy_value
        db.commit()
    return {key: policy.get(key, DEFAULT_ORG_POLICY[key]) for key in DEFAULT_ORG_POLICY}


def update_org_risk_policy(
    db: Session,
    *,
    org_id: uuid.UUID,
    changed_by_user_id: Optional[uuid.UUID],
    updates: dict[str, Any],
    note: Optional[str] = None,
) -> dict[str, str]:
    validated = validate_policy_values(updates)
    get_org_risk_policy(db, org_id, create_defaults=True)
    for key, new_value in validated.items():
        row = db.execute(
            select(OrganizationRiskPolicy).where(
                OrganizationRiskPolicy.org_id == org_id,
                OrganizationRiskPolicy.policy_key == key,
            )
        ).scalars().one()
        old_value = row.policy_value
        if old_value == new_value:
            continue
        row.policy_value = new_value
        row.updated_by_user_id = changed_by_user_id
        row.updated_at = utcnow()
        db.add(row)
        db.add(
            OrganizationRiskPolicyAudit(
                org_id=org_id,
                changed_by_user_id=changed_by_user_id,
                changed_at=utcnow(),
                policy_key=key,
                old_value=old_value,
                new_value=new_value,
                note=note,
            )
        )
    db.commit()
    return get_org_risk_policy(db, org_id, create_defaults=False)


def list_org_policy_audits(db: Session, org_id: uuid.UUID, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = list(
        db.execute(
            select(OrganizationRiskPolicyAudit)
            .where(OrganizationRiskPolicyAudit.org_id == org_id)
            .order_by(OrganizationRiskPolicyAudit.changed_at.desc())
            .limit(limit)
        ).scalars().all()
    )
    return [
        {
            "id": str(row.id),
            "policy_key": row.policy_key,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "changed_by": str(row.changed_by_user_id) if row.changed_by_user_id else None,
            "changed_at": row.changed_at.isoformat() if row.changed_at else None,
            "note": row.note,
        }
        for row in rows
    ]


def _validate_reason_code(reason_code: Optional[str]) -> Optional[str]:
    if reason_code is None or not str(reason_code).strip():
        return None
    normalized = str(reason_code).strip().lower()
    if normalized not in DECISION_REASON_CODES:
        raise ValueError("unsupported_reason_code")
    return normalized


def update_scan_decision_state(
    db: Session,
    *,
    org_id: uuid.UUID,
    scan_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    state: str,
    reason_code: Optional[str] = None,
    note: Optional[str] = None,
) -> ScanDecisionState:
    scan = get_scan_for_org(db, org_id, scan_id)
    if scan is None:
        raise ValueError("scan_not_found")
    normalized_state = str(state or "pending").strip().lower()
    if normalized_state not in SCAN_DECISION_STATES:
        raise ValueError("unsupported_scan_decision_state")
    normalized_reason = _validate_reason_code(reason_code)
    row = db.execute(
        select(ScanDecisionState).where(ScanDecisionState.org_id == org_id, ScanDecisionState.scan_id == scan_id)
    ).scalars().first()
    previous = row.state if row else "pending"
    if row is None:
        row = ScanDecisionState(org_id=org_id, scan_id=scan_id, state="pending", created_at=utcnow())
    row.state = normalized_state
    row.reason_code = normalized_reason
    row.note = note.strip()[:4000] if isinstance(note, str) and note.strip() else None
    row.updated_by_user_id = user_id
    row.updated_at = utcnow()
    db.add(row)
    db.add(
        DecisionAuditLog(
            org_id=org_id,
            scan_id=scan_id,
            user_id=user_id,
            event_type="scan_decision",
            previous_state=previous,
            new_state=normalized_state,
            reason_code=normalized_reason,
            note=row.note,
            created_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(row)
    return row


def update_finding_decision_status(
    db: Session,
    *,
    org_id: uuid.UUID,
    scan_id: uuid.UUID,
    finding_id: str,
    user_id: Optional[uuid.UUID],
    finding_status: str,
    reason_code: Optional[str] = None,
    note: Optional[str] = None,
) -> FindingDecisionStatus:
    scan = get_scan_for_org(db, org_id, scan_id)
    if scan is None:
        raise ValueError("scan_not_found")
    normalized_status = str(finding_status or "unresolved").strip().lower()
    if normalized_status not in FINDING_DECISION_STATUSES:
        raise ValueError("unsupported_finding_decision_status")
    normalized_reason = _validate_reason_code(reason_code)
    clean_finding_id = str(finding_id or "").strip()[:120]
    if not clean_finding_id:
        raise ValueError("finding_id_required")
    row = db.execute(
        select(FindingDecisionStatus).where(
            FindingDecisionStatus.org_id == org_id,
            FindingDecisionStatus.scan_id == scan_id,
            FindingDecisionStatus.finding_id == clean_finding_id,
        )
    ).scalars().first()
    previous = row.status if row else "unresolved"
    if row is None:
        row = FindingDecisionStatus(
            org_id=org_id,
            scan_id=scan_id,
            finding_id=clean_finding_id,
            status="unresolved",
            created_at=utcnow(),
        )
    row.status = normalized_status
    row.reason_code = normalized_reason
    row.note = note.strip()[:4000] if isinstance(note, str) and note.strip() else None
    row.updated_by_user_id = user_id
    row.updated_at = utcnow()
    db.add(row)
    db.add(
        DecisionAuditLog(
            org_id=org_id,
            scan_id=scan_id,
            finding_id=clean_finding_id,
            user_id=user_id,
            event_type="finding_decision",
            previous_state=previous,
            new_state=normalized_status,
            reason_code=normalized_reason,
            note=row.note,
            created_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(row)
    return row


def create_decision_note(
    db: Session,
    *,
    org_id: uuid.UUID,
    scan_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    note: str,
    finding_id: Optional[str] = None,
    reason_code: Optional[str] = None,
) -> DecisionNote:
    scan = get_scan_for_org(db, org_id, scan_id)
    if scan is None:
        raise ValueError("scan_not_found")
    normalized_reason = _validate_reason_code(reason_code)
    decision_note = DecisionNote(
        org_id=org_id,
        scan_id=scan_id,
        finding_id=str(finding_id).strip()[:120] if finding_id else None,
        created_by_user_id=user_id,
        reason_code=normalized_reason,
        note=note.strip()[:4000],
        created_at=utcnow(),
    )
    db.add(decision_note)
    db.flush()
    db.add(
        DecisionAuditLog(
            org_id=org_id,
            scan_id=scan_id,
            finding_id=decision_note.finding_id,
            user_id=user_id,
            event_type="decision_note",
            previous_state=None,
            new_state="note_added",
            reason_code=normalized_reason,
            note=decision_note.note,
            created_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(decision_note)
    return decision_note


def list_decision_notes_for_scan(db: Session, org_id: uuid.UUID, scan_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = list(
        db.execute(
            select(DecisionNote)
            .where(DecisionNote.org_id == org_id, DecisionNote.scan_id == scan_id)
            .order_by(DecisionNote.created_at.asc())
        ).scalars().all()
    )
    return [_decision_note_payload(row) for row in rows]


def prior_outcome_hint_for_families(
    db: Session,
    *,
    org_id: uuid.UUID,
    families: list[str],
) -> dict[str, Any] | None:
    if not families:
        return None
    scans = list(
        db.execute(
            select(Scan)
            .where(Scan.org_id == org_id)
            .order_by(Scan.created_at.desc())
            .limit(50)
        ).scalars().all()
    )
    family_set = {str(family).lower() for family in families}
    state_counts: Counter[tuple[str, str]] = Counter()
    for scan in scans:
        scan_families = {str(item).lower() for item in _json_load(scan.clause_families_detected, [])}
        matching = family_set & scan_families
        if not matching or not scan.scan_decision or scan.scan_decision.state == "pending":
            continue
        for family in matching:
            state_counts[(family, scan.scan_decision.state)] += 1
    if not state_counts:
        return None
    (family, state), count = state_counts.most_common(1)[0]
    return {"family": family, "state": state, "count": count}


def build_decision_intelligence_dashboard(db: Session, org_id: uuid.UUID) -> dict[str, Any]:
    scans = list(
        db.execute(select(Scan).where(Scan.org_id == org_id).order_by(Scan.created_at.desc())).scalars().all()
    )
    family_counts: Counter[str] = Counter()
    policy_breaches: Counter[str] = Counter()
    unresolved_count = 0
    high_by_contract: Counter[str] = Counter()
    high_by_counterparty: Counter[str] = Counter()
    open_scans: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter({"accepted": 0, "escalated": 0, "rejected": 0, "pending": 0, "negotiated": 0, "sent_for_legal_review": 0})

    for scan in scans:
        families = _json_load(scan.clause_families_detected, [])
        family_counts.update(str(family) for family in families)
        decision_state = scan.scan_decision.state if scan.scan_decision else "pending"
        decision_counts[decision_state] += 1
        if decision_state == "pending":
            open_scans.append(serialize_scan_summary(scan))
        detail = _json_load(scan.decision_intelligence_snapshot, {})
        for breach in detail.get("open_issues", []) if isinstance(detail, dict) else []:
            unresolved_count += 1
        for breach in detail.get("policy_status_summary", {}) if isinstance(detail, dict) else []:
            if breach in {"exceeds_tolerance", "conflicts_with_policy"}:
                for driver in detail.get("top_drivers", []):
                    if driver.get("policy_category"):
                        policy_breaches[driver["policy_category"]] += 1
        if scan.severity == "HIGH":
            context = _json_load(scan.context_profile_snapshot, None)
            high_by_contract[context_bucket_from_scan(context, "contract_type")] += 1
            high_by_counterparty[context_bucket_from_scan(context, "counterparty_profile")] += 1

    total_decisions = max(sum(decision_counts.values()), 1)
    ratios = {key: round(value / total_decisions, 4) for key, value in decision_counts.items()}
    return {
        "exposure_trends": [
            {
                "scan_id": str(scan.id),
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "risk_score": scan.risk_score,
                "severity": scan.severity,
            }
            for scan in scans[:20]
        ],
        "repeated_risk_families": [
            {"family": family, "count": count} for family, count in family_counts.most_common(10)
        ],
        "decision_ratios": ratios,
        "unresolved_finding_count": unresolved_count,
        "high_risk_findings_by_contract_type": [
            {"contract_type": key, "count": value} for key, value in high_by_contract.most_common()
        ],
        "high_risk_findings_by_counterparty_type": [
            {"counterparty_profile": key, "count": value} for key, value in high_by_counterparty.most_common()
        ],
        "scans_with_open_decisions": open_scans[:10],
        "most_common_policy_breaches": [
            {"policy_category": key, "count": value} for key, value in policy_breaches.most_common(10)
        ],
        "sector_intelligence_packs": SECTOR_INTELLIGENCE_PACKS,
        "owner_admin_truth_ready": {
            "scan_count": len(scans),
            "policy_adoption_count": sum(1 for value in get_org_risk_policy(db, org_id).values() if value != "unknown"),
            "open_decision_count": len(open_scans),
            "high_risk_family_trends": [
                {"family": family, "count": count} for family, count in family_counts.most_common(10)
            ],
            "failed_scan_count": None,
        },
        "aggregate_insights_governance": AGGREGATE_INSIGHTS_GOVERNANCE,
    }
