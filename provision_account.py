from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode

from account_provisioning import AccountProvisioningError, provision_customer_account
from db import SessionLocal


def build_setup_url(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision a controlled VoxaRisk account and password setup token."
    )
    parser.add_argument("--org-id", required=True, help="Existing organisation UUID")
    parser.add_argument("--email", required=True, help="Customer user email")
    parser.add_argument("--role", default="owner", help="Membership role to assign")
    parser.add_argument(
        "--setup-base-url",
        default="http://localhost:3000/account/setup",
        help="Base URL for the customer password setup page",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        provisioned = provision_customer_account(
            db,
            org_id=args.org_id,
            email=args.email,
            role=args.role,
        )
        payload = {
            "status": "provisioned",
            "method": "operator_controlled_account_provisioning",
            "org_id": str(provisioned.organization.id),
            "user_id": str(provisioned.user.id),
            "membership_id": str(provisioned.membership.id),
            "email": provisioned.user.email,
            "role": provisioned.membership.role,
            "setup_token": provisioned.setup_token,
            "setup_url": build_setup_url(args.setup_base_url, provisioned.setup_token),
            "authority_notice": "Provisioning creates identity and membership only; paid access is resolver-backed.",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except AccountProvisioningError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())