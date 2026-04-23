from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode

from account_provisioning import request_password_reset
from db import SessionLocal


def build_reset_url(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Issue a controlled VoxaRisk password reset token for an existing account."
    )
    parser.add_argument("--email", required=True, help="Existing customer user email")
    parser.add_argument(
        "--reset-base-url",
        default="http://localhost:3000/reset-password",
        help="Base URL for the customer password reset page",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        reset_token = request_password_reset(db, email=args.email)
        if not reset_token:
            print(
                json.dumps(
                    {
                        "status": "not_issued",
                        "reason": "account_not_found_or_membership_not_valid",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1

        payload = {
            "status": "issued",
            "method": "operator_controlled_password_reset",
            "email": args.email.strip().lower(),
            "reset_token": reset_token,
            "reset_url": build_reset_url(args.reset_base_url, reset_token),
            "authority_notice": "Password reset changes credentials only; membership and entitlement remain resolver-backed.",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())