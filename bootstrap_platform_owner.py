from __future__ import annotations

import argparse
import json
import os
from urllib.parse import urlencode

from account_provisioning import AccountProvisioningError, provision_customer_account
from db import SessionLocal

DEFAULT_OWNER_EMAIL = "voxalive123@gmail.com"


def owner_email() -> str:
    return os.getenv("PLATFORM_OWNER_EMAIL", DEFAULT_OWNER_EMAIL).strip().lower() or DEFAULT_OWNER_EMAIL


def build_setup_url(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def bootstrap_platform_owner(
    db,
    *,
    org_id: str,
    setup_base_url: str = "http://localhost:3000/account/setup",
    email: str | None = None,
) -> dict:
    normalized_email = (email or owner_email()).strip().lower()
    if normalized_email != owner_email():
        raise AccountProvisioningError("Owner bootstrap email must match PLATFORM_OWNER_EMAIL")

    provisioned = provision_customer_account(
        db,
        org_id=org_id,
        email=normalized_email,
        role="owner",
    )
    return {
        "status": "owner_bootstrap_ready",
        "method": "platform_owner_controlled_bootstrap",
        "org_id": str(provisioned.organization.id),
        "user_id": str(provisioned.user.id),
        "membership_id": str(provisioned.membership.id),
        "email": provisioned.user.email,
        "role": provisioned.membership.role,
        "setup_token": provisioned.setup_token,
        "setup_url": build_setup_url(setup_base_url, provisioned.setup_token),
        "authority_notice": "Owner bootstrap creates identity and active organisation membership only; entitlement remains resolver-backed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap the VoxaRisk platform owner account without opening public registration."
    )
    parser.add_argument("--org-id", required=True, help="Existing organisation UUID to attach the owner to")
    parser.add_argument(
        "--setup-base-url",
        default="http://localhost:3000/account/setup",
        help="Base URL for the password setup page",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        payload = bootstrap_platform_owner(
            db,
            org_id=args.org_id,
            setup_base_url=args.setup_base_url,
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