from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from account_auth import AccountContext
from entitlement_diagnostics import build_entitlement_diagnostics
from internal_ops import get_internal_organization_detail
from models import InternalOperatorAction, Organization, OrganizationInvite


class InternalWorkflowError(Exception):
    pass


class InternalWorkflowNotFoundError(InternalWorkflowError):
    pass


class InternalWorkflowInvalidActionError(InternalWorkflowError):
    pass


def _serialize(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _action_snapshot(action: InternalOperatorAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "actor_user_id": str(action.actor_user_id),
        "org_id": str(action.org_id) if action.org_id else None,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "action_type": action.action_type,
        "reason": action.reason,
        "before": json.loads(action.before_json) if action.before_json else None,
        "after": json.loads(action.after_json) if action.after_json else None,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


def _normalize_reason(reason: str) -> str:
    normalized_reason = reason.strip()
    if len(normalized_reason) < 8:
        raise InternalWorkflowInvalidActionError("A clear operator reason is required")
    return normalized_reason


def log_operator_action(
    db: Session,
    *,
    actor: AccountContext,
    action_type: str,
    reason: str,
    target_type: str,
    target_id: str | None = None,
    org_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> InternalOperatorAction:
    normalized_reason = _normalize_reason(reason)

    row = InternalOperatorAction(
        actor_user_id=actor.user.id,
        org_id=org_id,
        target_type=target_type,
        target_id=target_id,
        action_type=action_type,
        reason=normalized_reason,
        before_json=_serialize(before),
        after_json=_serialize(after),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def recent_operator_actions(
    db: Session,
    *,
    org_id: uuid.UUID | str | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    stmt = select(InternalOperatorAction).order_by(InternalOperatorAction.created_at.desc()).limit(limit)
    if org_id is not None:
        parsed = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
        stmt = (
            select(InternalOperatorAction)
            .where(InternalOperatorAction.org_id == parsed)
            .order_by(InternalOperatorAction.created_at.desc())
            .limit(limit)
        )
    return [_action_snapshot(row) for row in db.execute(stmt).scalars().all()]


def create_operator_note(
    db: Session,
    *,
    actor: AccountContext,
    org_id: uuid.UUID | str,
    reason: str,
) -> dict[str, Any]:
    parsed_org_id = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
    org = db.get(Organization, parsed_org_id)
    if org is None:
        raise InternalWorkflowNotFoundError("Organisation not found")

    diagnostics = build_entitlement_diagnostics(db, org_id=parsed_org_id, webhook_limit=5)
    action = log_operator_action(
        db,
        actor=actor,
        action_type="operator_note",
        reason=reason,
        target_type="organization",
        target_id=str(parsed_org_id),
        org_id=parsed_org_id,
        before={"diagnostics": diagnostics},
        after={"note_recorded": True},
    )
    return _action_snapshot(action)


def _invite_snapshot(invite: OrganizationInvite) -> dict[str, Any]:
    return {
        "id": str(invite.id),
        "org_id": str(invite.org_id),
        "email": invite.invited_email,
        "role": invite.role,
        "status": invite.status,
        "accepted_at": invite.accepted_at.isoformat() if invite.accepted_at else None,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
    }


def cancel_pending_invite(
    db: Session,
    *,
    actor: AccountContext,
    invite_id: uuid.UUID | str,
    reason: str,
) -> dict[str, Any]:
    normalized_reason = _normalize_reason(reason)
    parsed_invite_id = invite_id if isinstance(invite_id, uuid.UUID) else uuid.UUID(str(invite_id))
    invite = db.get(OrganizationInvite, parsed_invite_id)
    if invite is None:
        raise InternalWorkflowNotFoundError("Invite not found")
    if invite.status != "pending" or invite.accepted_at is not None:
        raise InternalWorkflowInvalidActionError("Only pending, unused invites can be cancelled")

    before = _invite_snapshot(invite)
    invite.status = "cancelled"
    after = _invite_snapshot(invite)
    action = InternalOperatorAction(
        actor_user_id=actor.user.id,
        org_id=invite.org_id,
        target_type="organization_invite",
        target_id=str(invite.id),
        action_type="invite_cancelled",
        reason=normalized_reason,
        before_json=_serialize(before),
        after_json=_serialize(after),
    )
    db.add(invite)
    db.add(action)
    db.commit()
    db.refresh(action)
    return _action_snapshot(action)


def workflow_view(db: Session, *, org_id: uuid.UUID | str) -> dict[str, Any]:
    detail = get_internal_organization_detail(db, org_id=org_id)
    return {
        "read_only_truth": detail,
        "operator_actions": recent_operator_actions(db, org_id=org_id, limit=25),
        "manual_controls": ["operator_note", "cancel_pending_invite"],
        "authority_notice": "Workflow actions are audited and do not override resolver-backed entitlement truth.",
    }