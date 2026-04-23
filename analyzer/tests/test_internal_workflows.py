from __future__ import annotations

from datetime import datetime, timezone

from models import InternalOperatorAction, OrganizationInvite
from analyzer.tests.test_internal_ops import add_activity, create_user_org, internal_ops_client


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_internal_workflow_view_is_internal_only(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    customer = create_user_org(session_factory, email="customer@example.test", role="owner")
    add_activity(session_factory, org_id=admin["org_id"], user_id=admin["user_id"])
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    allowed = client.get(
        f"/internal/ops/organizations/{admin['org_id']}/workflow",
        headers=_auth(admin["token"]),
    )
    denied = client.get(
        f"/internal/ops/organizations/{admin['org_id']}/workflow",
        headers=_auth(customer["token"]),
    )

    assert allowed.status_code == 200
    assert allowed.json()["read_only_truth"]["found"] is True
    assert allowed.json()["manual_controls"] == ["operator_note", "cancel_pending_invite"]
    assert "do not override resolver-backed entitlement truth" in allowed.json()["authority_notice"]
    assert denied.status_code == 403


def test_operator_note_writes_audit_record_and_preserves_entitlement(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    before = client.get("/account/me", headers=_auth(admin["token"])).json()["entitlement"]
    response = client.post(
        f"/internal/ops/organizations/{admin['org_id']}/workflow/notes",
        headers=_auth(admin["token"]),
        json={"reason": "Customer paid access investigation note"},
    )
    after = client.get("/account/me", headers=_auth(admin["token"])).json()["entitlement"]

    assert response.status_code == 200
    assert response.json()["status"] == "operator_note_recorded"
    assert response.json()["action"]["action_type"] == "operator_note"
    assert response.json()["action"]["org_id"] == str(admin["org_id"])
    assert response.json()["action"]["reason"] == "Customer paid access investigation note"
    assert before == after

    with session_factory() as db:
        actions = db.query(InternalOperatorAction).all()
        assert len(actions) == 1
        assert actions[0].actor_user_id == admin["user_id"]
        assert actions[0].org_id == admin["org_id"]
        assert actions[0].target_type == "organization"
        assert actions[0].action_type == "operator_note"
        assert actions[0].before_json is not None
        assert actions[0].after_json is not None


def test_customer_user_cannot_write_workflow_actions(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    customer = create_user_org(session_factory, email="customer@example.test", role="owner")
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    response = client.post(
        f"/internal/ops/organizations/{admin['org_id']}/workflow/notes",
        headers=_auth(customer["token"]),
        json={"reason": "Trying to write customer note"},
    )

    assert response.status_code == 403
    with session_factory() as db:
        assert db.query(InternalOperatorAction).count() == 0


def test_cancel_pending_invite_is_bounded_and_audited(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    add_activity(session_factory, org_id=admin["org_id"], user_id=admin["user_id"])
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    with session_factory() as db:
        invite = db.query(OrganizationInvite).filter_by(org_id=admin["org_id"], status="pending").one()
        invite_id = invite.id

    response = client.post(
        f"/internal/ops/invites/{invite_id}/cancel",
        headers=_auth(admin["token"]),
        json={"reason": "Duplicate invite created during support review"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "invite_cancelled"
    assert response.json()["action"]["action_type"] == "invite_cancelled"
    assert response.json()["action"]["before"]["status"] == "pending"
    assert response.json()["action"]["after"]["status"] == "cancelled"

    with session_factory() as db:
        invite = db.get(OrganizationInvite, invite_id)
        assert invite.status == "cancelled"
        actions = db.query(InternalOperatorAction).all()
        assert len(actions) == 1
        assert actions[0].target_type == "organization_invite"
        assert actions[0].target_id == str(invite_id)
        assert actions[0].org_id == admin["org_id"]


def test_cancel_non_pending_invite_fails_without_audit_or_state_change(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    add_activity(session_factory, org_id=admin["org_id"], user_id=admin["user_id"])
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    with session_factory() as db:
        invite = db.query(OrganizationInvite).filter_by(org_id=admin["org_id"], status="pending").one()
        invite.status = "accepted"
        invite.accepted_at = datetime.now(timezone.utc)
        db.commit()
        invite_id = invite.id

    response = client.post(
        f"/internal/ops/invites/{invite_id}/cancel",
        headers=_auth(admin["token"]),
        json={"reason": "Attempting to cancel accepted invite"},
    )

    assert response.status_code == 400
    with session_factory() as db:
        invite = db.get(OrganizationInvite, invite_id)
        assert invite.status == "accepted"
        assert db.query(InternalOperatorAction).count() == 0


def test_workflow_action_history_visible_after_note(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    client.post(
        f"/internal/ops/organizations/{admin['org_id']}/workflow/notes",
        headers=_auth(admin["token"]),
        json={"reason": "Reviewing webhook mismatch with customer"},
    )
    response = client.get(
        f"/internal/ops/organizations/{admin['org_id']}/workflow",
        headers=_auth(admin["token"]),
    )

    assert response.status_code == 200
    actions = response.json()["operator_actions"]
    assert len(actions) == 1
    assert actions[0]["action_type"] == "operator_note"
    assert actions[0]["reason"] == "Reviewing webhook mismatch with customer"