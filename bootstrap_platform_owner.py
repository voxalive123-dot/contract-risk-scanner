from __future__ import annotations

import argparse
import getpass
import json
import os
import uuid
from urllib.parse import urlencode

from sqlalchemy import func, select

from account_auth import hash_password
from account_provisioning import (
    AccountProvisioningError,
    SETUP_TTL_HOURS,
    create_password_token,
    utcnow,
)
from db import SessionLocal
from models import AccountPasswordToken, Membership, Organization, User
from platform_owner import (
    DEFAULT_OWNER_EMAIL,
    DEFAULT_OWNER_ORG_NAME,
    canonical_platform_org_name,
    choose_canonical_platform_org,
    owner_email,
)

DEFAULT_PLAN_LIMIT = 5


def build_setup_url(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def _single_org_by_name(db, name: str) -> Organization | None:
    stmt = select(Organization).where(func.lower(Organization.name) == name.strip().lower())
    orgs = list(db.execute(stmt).scalars().all())
    if len(orgs) > 1:
        raise AccountProvisioningError("Multiple platform owner organisations match this name")
    return orgs[0] if orgs else None


def resolve_owner_org(db, *, org_id: str | None = None, org_name: str | None = None) -> Organization:
    configured_org_id = (org_id or os.getenv("PLATFORM_OWNER_ORG_ID", "")).strip()
    if configured_org_id:
        try:
            parsed = uuid.UUID(configured_org_id)
        except ValueError as exc:
            raise AccountProvisioningError("PLATFORM_OWNER_ORG_ID is not a valid UUID") from exc
        org = db.get(Organization, parsed)
        if org is None:
            raise AccountProvisioningError("Configured platform owner organisation was not found")
        return org

    resolved_name = (org_name or canonical_platform_org_name()).strip()
    canonical_org, _reason = choose_canonical_platform_org(db)
    if canonical_org is not None:
        if canonical_org.name != resolved_name:
            existing = _single_org_by_name(db, resolved_name)
            if existing is None:
                canonical_org.name = resolved_name
                db.add(canonical_org)
                db.commit()
                db.refresh(canonical_org)
        return canonical_org

    org = _single_org_by_name(db, resolved_name)
    if org is not None:
        return org

    org = Organization(
        name=resolved_name,
        plan_type="starter",
        plan_status="active",
        plan_limit=DEFAULT_PLAN_LIMIT,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _single_user_by_email(db, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    users = list(db.execute(stmt).scalars().all())
    if len(users) > 1:
        raise AccountProvisioningError("Multiple users exist for the configured platform owner email")
    return users[0] if users else None


def _ensure_owner_user(db, *, org: Organization, email: str) -> User:
    user = _single_user_by_email(db, email)
    if user is None:
        user = User(
            org_id=org.id,
            email=email,
            password_hash=hash_password(uuid.uuid4().hex),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    user.org_id = org.id
    user.role = "owner"
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _ensure_owner_membership(db, *, user: User, org: Organization) -> Membership:
    stmt = select(Membership).where(Membership.user_id == user.id, Membership.org_id == org.id)
    membership = db.execute(stmt).scalars().first()
    if membership is None:
        membership = Membership(
            user_id=user.id,
            org_id=org.id,
            role="owner",
            status="active",
        )
    else:
        membership.role = "owner"
        membership.status = "active"
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def _invalidate_setup_tokens(db, *, user_id) -> None:
    stmt = select(AccountPasswordToken).where(
        AccountPasswordToken.user_id == user_id,
        AccountPasswordToken.purpose == "setup",
        AccountPasswordToken.used_at.is_(None),
    )
    now = utcnow()
    for token in db.execute(stmt).scalars().all():
        token.used_at = now


def _set_owner_password(db, *, user, password: str) -> None:
    if len(password) < 12:
        raise AccountProvisioningError("Owner password must be at least 12 characters")
    user.password_hash = hash_password(password)
    _invalidate_setup_tokens(db, user_id=user.id)
    db.add(user)
    db.commit()


def _enforce_single_owner_membership(db, *, membership: Membership) -> None:
    stmt = select(Membership).where(Membership.user_id == membership.user_id)
    for row in db.execute(stmt).scalars().all():
        if row.id == membership.id:
            row.role = "owner"
            row.status = "active"
        elif row.status == "active":
            row.status = "inactive"
        db.add(row)
    db.commit()
    db.refresh(membership)


def bootstrap_platform_owner(
    db,
    *,
    org_id: str | None = None,
    org_name: str | None = None,
    setup_base_url: str = "http://localhost:3000/account/setup",
    email: str | None = None,
    password: str | None = None,
) -> dict:
    normalized_email = (email or owner_email()).strip().lower()
    if normalized_email != owner_email():
        raise AccountProvisioningError("Owner bootstrap email must match PLATFORM_OWNER_EMAIL")

    org = resolve_owner_org(db, org_id=org_id, org_name=org_name)
    user = _ensure_owner_user(db, org=org, email=normalized_email)
    membership = _ensure_owner_membership(db, user=user, org=org)
    _enforce_single_owner_membership(db, membership=membership)

    setup_token = create_password_token(
        db,
        user=user,
        purpose="setup",
        ttl_hours=SETUP_TTL_HOURS,
    )

    setup_url = build_setup_url(setup_base_url, setup_token)
    credential_status = "setup_link_issued"
    if password is not None:
        _set_owner_password(db, user=user, password=password)
        setup_url = None
        credential_status = "password_set_directly"

    return {
        "status": "owner_bootstrap_ready",
        "method": "platform_owner_controlled_bootstrap",
        "org_id": str(org.id),
        "org_name": org.name,
        "user_id": str(user.id),
        "membership_id": str(membership.id),
        "email": user.email,
        "role": membership.role,
        "credential_status": credential_status,
        "setup_token": None if password is not None else setup_token,
        "setup_url": setup_url,
        "signin_url": "/signin",
        "internal_operations_url": "/internal/operations",
        "authority_notice": "Owner bootstrap creates identity and active organisation membership only; entitlement remains resolver-backed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap the VoxaRisk platform owner account without opening public registration."
    )
    parser.add_argument("--org-id", default=None, help="Existing organisation UUID to attach the owner to")
    parser.add_argument(
        "--org-name",
        default=None,
        help="Platform owner organisation name to reuse or create when --org-id is not provided",
    )
    parser.add_argument(
        "--setup-base-url",
        default="http://localhost:3000/account/setup",
        help="Base URL for the password setup page",
    )
    parser.add_argument(
        "--prompt-password",
        action="store_true",
        help="Set the owner password directly via a hidden terminal prompt",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Set the owner password directly. Prefer --prompt-password outside tests.",
    )
    args = parser.parse_args()

    password = args.password
    if args.prompt_password:
        first = getpass.getpass("Owner password: ")
        second = getpass.getpass("Confirm owner password: ")
        if first != second:
            print(json.dumps({"status": "failed", "error": "Owner passwords did not match"}, indent=2, sort_keys=True))
            return 1
        password = first

    db = SessionLocal()
    try:
        payload = bootstrap_platform_owner(
            db,
            org_id=args.org_id,
            org_name=args.org_name,
            setup_base_url=args.setup_base_url,
            password=password,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except AccountProvisioningError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
