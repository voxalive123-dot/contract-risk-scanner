from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from entitlement_spine import EntitlementResolution, resolve_entitlement_for_org
from models import Membership, Organization, User


SESSION_TTL_SECONDS = 60 * 60 * 8
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390_000


class AccountAuthError(Exception):
    pass


class AccountConfigError(AccountAuthError):
    pass


class InvalidCredentialsError(AccountAuthError):
    pass


class InvalidMembershipError(AccountAuthError):
    pass


@dataclass(frozen=True)
class AccountContext:
    user: User
    organization: Organization
    membership: Membership
    entitlement: EntitlementResolution


def account_session_config_missing_keys() -> list[str]:
    missing: list[str] = []
    if not os.getenv("ACCOUNT_SESSION_SECRET", "").strip():
        missing.append("ACCOUNT_SESSION_SECRET")
    return missing


def validate_account_session_config() -> None:
    missing = account_session_config_missing_keys()
    if missing:
        raise AccountConfigError(f"Missing account session configuration: {', '.join(missing)}")


def account_session_secret() -> str:
    validate_account_session_config()
    return os.getenv("ACCOUNT_SESSION_SECRET", "").strip()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


def _b64_json(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_b64_json(value: str) -> dict:
    padded = value + ("=" * (-len(value) % 4))
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("session payload must be an object")
    return decoded


def create_session_token(user: User, *, now: int | None = None) -> str:
    issued_at = int(now or time.time())
    payload = {
        "sub": str(user.id),
        "iat": issued_at,
        "exp": issued_at + SESSION_TTL_SECONDS,
    }
    body = _b64_json(payload)
    signature = hmac.new(
        account_session_secret().encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{body}.{encoded_signature}"


def decode_session_token(token: str, *, now: int | None = None) -> uuid.UUID:
    try:
        body, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise InvalidCredentialsError("Invalid session token") from exc

    expected = hmac.new(
        account_session_secret().encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    padded_sig = encoded_signature + ("=" * (-len(encoded_signature) % 4))
    try:
        actual = base64.urlsafe_b64decode(padded_sig.encode("ascii"))
    except ValueError as exc:
        raise InvalidCredentialsError("Invalid session signature") from exc

    if not hmac.compare_digest(actual, expected):
        raise InvalidCredentialsError("Invalid session signature")

    try:
        payload = _decode_b64_json(body)
        expires_at = int(payload["exp"])
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidCredentialsError("Invalid session payload") from exc

    if expires_at < int(now or time.time()):
        raise InvalidCredentialsError("Session expired")

    return user_id


def _active_membership_for_user(db: Session, user: User) -> Membership:
    stmt = select(Membership).where(
        Membership.user_id == user.id,
        Membership.status == "active",
    )
    memberships = list(db.execute(stmt).scalars().all())
    if len(memberships) != 1:
        raise InvalidMembershipError("User must have exactly one active membership")
    return memberships[0]


def account_context_for_user(db: Session, user: User) -> AccountContext:
    if not user.is_active:
        raise InvalidCredentialsError("Inactive user")

    membership = _active_membership_for_user(db, user)
    org = db.get(Organization, membership.org_id)
    if org is None:
        raise InvalidMembershipError("Membership organization does not exist")

    return AccountContext(
        user=user,
        organization=org,
        membership=membership,
        entitlement=resolve_entitlement_for_org(db, org),
    )


def authenticate_user(db: Session, *, email: str, password: str) -> AccountContext:
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        raise InvalidCredentialsError("Invalid credentials")

    stmt = select(User).where(func.lower(User.email) == normalized_email)
    users = list(db.execute(stmt).scalars().all())
    if len(users) != 1:
        raise InvalidCredentialsError("Invalid credentials")

    user = users[0]
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials")

    return account_context_for_user(db, user)


def account_context_from_token(db: Session, token: str) -> AccountContext:
    user_id = decode_session_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise InvalidCredentialsError("Invalid session user")
    return account_context_for_user(db, user)


def serialize_account_context(context: AccountContext) -> dict:
    entitlement = context.entitlement
    return {
        "user": {
            "id": str(context.user.id),
            "email": context.user.email,
            "is_active": context.user.is_active,
        },
        "organization": {
            "id": str(context.organization.id),
            "name": context.organization.name,
        },
        "membership": {
            "id": str(context.membership.id),
            "role": context.membership.role,
            "status": context.membership.status,
        },
        "entitlement": {
            "source": entitlement.source,
            "subscription_state": entitlement.subscription_state,
            "effective_plan": entitlement.effective_plan,
            "monthly_scan_limit": entitlement.monthly_scan_limit,
            "paid_access": entitlement.paid_access,
            "ai_review_notes_allowed": entitlement.ai_review_notes_allowed,
            "reason": entitlement.reason,
        },
    }
