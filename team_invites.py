from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import AccountContext, hash_password
from models import Membership, OrganizationInvite, User


INVITE_TTL_DAYS = 7
ALLOWED_ROLES = {"owner", "admin", "member"}
INVITER_ROLES = {"owner", "admin"}
INVITABLE_ROLES_BY_INVITER = {
    "owner": {"admin", "member"},
    "admin": {"member"},
}
DEFAULT_INVITE_ACCEPT_BASE_URL = "http://localhost:3000/team/accept"


class TeamInviteError(Exception):
    pass


class TeamInvitePermissionError(TeamInviteError):
    pass


class TeamInviteTokenError(TeamInviteError):
    pass


@dataclass(frozen=True)
class TeamInviteResult:
    invite: OrganizationInvite
    raw_token: str
    accept_url: str


@dataclass(frozen=True)
class AcceptedInviteResult:
    user: User
    membership: Membership


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def _new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise TeamInviteError("Valid invited email is required")
    return normalized


def normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in ALLOWED_ROLES:
        raise TeamInviteError("Unsupported membership role")
    return normalized


def require_team_invite_permission(context: AccountContext, requested_role: str) -> None:
    inviter_role = (context.membership.role or "").strip().lower()
    if inviter_role not in INVITER_ROLES:
        raise TeamInvitePermissionError("Only owner or admin members can invite team members")
    if requested_role not in INVITABLE_ROLES_BY_INVITER.get(inviter_role, set()):
        raise TeamInvitePermissionError("Inviter role cannot assign requested membership role")


def build_accept_url(raw_token: str, *, base_url: str | None = None) -> str:
    candidate = (base_url or os.getenv("TEAM_INVITE_ACCEPT_BASE_URL") or DEFAULT_INVITE_ACCEPT_BASE_URL).strip()
    separator = "&" if "?" in candidate else "?"
    return f"{candidate}{separator}{urlencode({'token': raw_token})}"


def _existing_pending_invite(db: Session, *, org_id, email: str) -> OrganizationInvite | None:
    stmt = (
        select(OrganizationInvite)
        .where(
            OrganizationInvite.org_id == org_id,
            func.lower(OrganizationInvite.invited_email) == email,
            OrganizationInvite.status == "pending",
            OrganizationInvite.accepted_at.is_(None),
        )
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def create_team_invite(
    db: Session,
    *,
    context: AccountContext,
    invited_email: str,
    role: str,
    accept_base_url: str | None = None,
) -> TeamInviteResult:
    email = normalize_email(invited_email)
    normalized_role = normalize_role(role)
    require_team_invite_permission(context, normalized_role)

    existing = _existing_pending_invite(db, org_id=context.organization.id, email=email)
    if existing:
        raise TeamInviteError("A pending invite already exists for this email")

    raw_token = _new_raw_token()
    invite = OrganizationInvite(
        org_id=context.organization.id,
        invited_email=email,
        role=normalized_role,
        token_hash=hash_invite_token(raw_token),
        status="pending",
        invited_by_user_id=context.user.id,
        expires_at=utcnow() + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return TeamInviteResult(
        invite=invite,
        raw_token=raw_token,
        accept_url=build_accept_url(raw_token, base_url=accept_base_url),
    )


def _single_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email)
    users = list(db.execute(stmt).scalars().all())
    if len(users) > 1:
        raise TeamInviteTokenError("Invite email is ambiguous")
    return users[0] if users else None


def _active_memberships_for_user(db: Session, user: User) -> list[Membership]:
    stmt = select(Membership).where(
        Membership.user_id == user.id,
        Membership.status == "active",
    )
    return list(db.execute(stmt).scalars().all())


def accept_team_invite(
    db: Session,
    *,
    raw_token: str,
    email: str,
    password: str,
) -> AcceptedInviteResult:
    normalized_email = normalize_email(email)
    if not raw_token.strip() or len(password) < 12:
        raise TeamInviteTokenError("Invalid invite token or password")

    stmt = select(OrganizationInvite).where(
        OrganizationInvite.token_hash == hash_invite_token(raw_token),
    )
    invite = db.execute(stmt).scalars().first()
    if invite is None or invite.status != "pending" or invite.accepted_at is not None:
        raise TeamInviteTokenError("Invite token is invalid or already used")

    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        invite.status = "expired"
        db.add(invite)
        db.commit()
        raise TeamInviteTokenError("Invite token has expired")

    if normalize_email(invite.invited_email) != normalized_email:
        raise TeamInviteTokenError("Invite token does not match this email")

    user = _single_user_by_email(db, normalized_email)
    if user is None:
        user = User(
            org_id=invite.org_id,
            email=normalized_email,
            password_hash=hash_password(password),
            role=invite.role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        raise TeamInviteTokenError("Invite user is not active")
    else:
        active_memberships = _active_memberships_for_user(db, user)
        if active_memberships:
            raise TeamInviteTokenError("Invite user already has an active membership")
        user.org_id = invite.org_id
        user.role = invite.role
        user.password_hash = hash_password(password)
        db.add(user)

    membership = Membership(
        user_id=user.id,
        org_id=invite.org_id,
        role=invite.role,
        status="active",
    )
    db.add(membership)
    invite.status = "accepted"
    invite.accepted_at = utcnow()
    invite.accepted_user_id = user.id
    db.add(invite)
    db.commit()
    db.refresh(user)
    db.refresh(membership)
    return AcceptedInviteResult(user=user, membership=membership)


def team_snapshot(db: Session, context: AccountContext) -> dict:
    memberships = list(
        db.execute(
            select(Membership)
            .where(Membership.org_id == context.organization.id)
            .order_by(Membership.created_at.asc())
        ).scalars().all()
    )
    users_by_id = {
        user.id: user
        for user in db.execute(
            select(User).where(User.id.in_([m.user_id for m in memberships]))
        ).scalars().all()
    } if memberships else {}
    pending_invites = list(
        db.execute(
            select(OrganizationInvite)
            .where(
                OrganizationInvite.org_id == context.organization.id,
                OrganizationInvite.status == "pending",
                OrganizationInvite.accepted_at.is_(None),
            )
            .order_by(OrganizationInvite.created_at.desc())
        ).scalars().all()
    )
    return {
        "organization_id": str(context.organization.id),
        "memberships": [
            {
                "id": str(membership.id),
                "email": users_by_id.get(membership.user_id).email if users_by_id.get(membership.user_id) else None,
                "role": membership.role,
                "status": membership.status,
            }
            for membership in memberships
        ],
        "pending_invites": [
            {
                "id": str(invite.id),
                "email": invite.invited_email,
                "role": invite.role,
                "status": invite.status,
                "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
            }
            for invite in pending_invites
        ],
    }