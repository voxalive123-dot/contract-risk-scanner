from __future__ import annotations

import argparse
import getpass
import json

from account_provisioning import AccountProvisioningError
from bootstrap_platform_owner import bootstrap_platform_owner
from db import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair the verified VoxaRisk platform owner account.")
    parser.add_argument("--email", required=True, help="Platform owner email to repair")
    parser.add_argument("--org-id", default=None, help="Existing organisation UUID to attach the owner to")
    parser.add_argument("--org-name", default=None, help="Platform owner organisation name to reuse or create")
    parser.add_argument(
        "--setup-base-url",
        default="https://www.voxarisk.com/account/setup",
        help="Base URL for the password setup page",
    )
    parser.add_argument("--prompt-password", action="store_true", help="Set a new owner password via hidden prompt")
    parser.add_argument("--password", default=None, help="Set a new owner password directly. Prefer --prompt-password.")
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
            email=args.email,
            password=password,
        )
        payload["status"] = "platform_owner_repair_ready"
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except AccountProvisioningError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
