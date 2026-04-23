from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import (
    AccountContext,
    InvalidCredentialsError,
    InvalidMembershipError,
    account_context_for_user,
    hash_password,
)
from models import AccountPasswordToken, Membership, Organization, User


SETUP_TTL_HOURS = 72
RESET_TTL_HOURS = 2


class AccountProvisioningError(Exception):
    pass


class AccountTokenError(AccountProvisioningError):
    pass


@dataclass(frozen=True)
class ProvisionedAccount:
    user: User
    organization: Organization
    membership: Membership
    setup_token: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_account_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def _new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def _single_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    users = list(db.execute(stmt).scalars().all())
    if len(users) > 1:
        raise AccountProvisioningError("Multiple users exist for this email")
    return users[0] if users else None


def _membership_for_user_org(db: Session, *, user: User, org: Organization) -> Membership | None:
    stmt = select(Membership).where(Membership.user_id == user.id, Membership.org_id == org.id)
    return db.execute(stmt).scalars().first()


def _invalidate_existing_tokens(db: Session, *, user: User, purpose: str) -> None:
    stmt = select(AccountPasswordToken).where(
        AccountPasswordToken.user_id == user.id,
        AccountPasswordToken.purpose == purpose,
        AccountPasswordToken.used_at.is_(None),
    )
    for token in db.execute(stmt).scalars().all():
        token.used_at = utcnow()


def create_password_token(
    db: Session,
    *,
    user: User,
    purpose: str,
    ttl_hours: int,
) -> str:
    if purpose not in {"setup", "reset"}:
        raise AccountProvisioningError("Unsupported password token purpose")

    _invalidate_existing_tokens(db, user=user, purpose=purpose)
    raw_token = _new_raw_token()
    token = AccountPasswordToken(
        user_id=user.id,
        token_hash=hash_account_token(raw_token),
        purpose=purpose,
        expires_at=utcnow() + timedelta(hours=ttl_hours),
    )
    db.add(token)
    db.commit()
    return raw_token


def provision_customer_account(
    db: Session,
    *,
    org_id: uuid.UUID | str,
    email: str,
    role: str = "owner",
) -> ProvisionedAccount:
    try:
        normalized_org_id = uuid.UUID(str(org_id))
    except ValueError as exc:
        raise AccountProvisioningError("Organization ID is invalid") from exc

    org = db.get(Organization, normalized_org_id)
    if org is None:
        raise AccountProvisioningError("Organization not found")

    normalized_email = email.strip().lower()
    if not normalized_email:
        raise AccountProvisioningError("Email is required")

    user = _single_user_by_email(db, normalized_email)
    if user is None:
        user = User(
            org_id=org.id,
            email=normalized_email,
            password_hash=hash_password(_new_raw_token()),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    membership = _membership_for_user_org(db, user=user, org=org)
    if membership is None:
        membership = Membership(
            user_id=user.id,
            org_id=org.id,
            role=role,
            status="active",
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
    elif membership.status != "active":
        raise AccountProvisioningError("Existing membership is not active")

    setup_token = create_password_token(
        db,
        user=user,
        purpose="setup",
        ttl_hours=SETUP_TTL_HOURS,
    )
    db.refresh(user)
    db.refresh(membership)
    return ProvisionedAccount(
        user=user,
        organization=org,
        membership=membership,
        setup_token=setup_token,
    )


def complete_password_token(
    db: Session,
    *,
    raw_token: str,
    password: str,
    purpose: str,
) -> AccountContext:
    if not raw_token.strip() or not password:
        raise AccountTokenError("Invalid token or password")

    stmt = select(AccountPasswordToken).where(
        AccountPasswordToken.token_hash == hash_account_token(raw_token),
        AccountPasswordToken.purpose == purpose,
    )
    token = db.execute(stmt).scalars().first()
    if token is None or token.used_at is not None:
        raise AccountTokenError("Invalid or used token")

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise AccountTokenError("Expired token")

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AccountTokenError("Invalid token user")

    try:
        context = account_context_for_user(db, user)
    except (InvalidCredentialsError, InvalidMembershipError) as exc:
        raise AccountTokenError("Invalid token user") from exc

    user.password_hash = hash_password(password)
    token.used_at = utcnow()
    db.add(user)
    db.add(token)
    db.commit()
    db.refresh(user)
    return account_context_for_user(db, user)


def request_password_reset(db: Session, *, email: str) -> str | None:
    try:
        user = _single_user_by_email(db, email)
    except AccountProvisioningError:
        return None

    if user is None or not user.is_active:
        return None

    try:
        account_context_for_user(db, user)
    except Exception:
        return None

    return create_password_token(
        db,
        user=user,
        purpose="reset",
        ttl_hours=RESET_TTL_HOURS,
    )
