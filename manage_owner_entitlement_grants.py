from __future__ import annotations

import argparse
import json
from datetime import datetime

from db import SessionLocal
from owner_entitlement_grants import (
    OwnerGrantError,
    create_owner_entitlement_grant,
    list_owner_entitlement_grants,
    revoke_owner_entitlement_grant,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date/time must be ISO-8601, e.g. 2026-05-01T12:00:00+00:00") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create, revoke, or list VoxaRisk owner entitlement grants."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    grant_parser = subparsers.add_parser("grant", help="Create an owner entitlement grant")
    grant_parser.add_argument("--email", help="Target user email")
    grant_parser.add_argument("--org-id", help="Target organization UUID")
    grant_parser.add_argument("--plan", required=True, choices=["executive", "enterprise"], help="Grant plan level")
    grant_parser.add_argument("--grant-type", default="trial", choices=["trial", "complimentary", "internal"])
    grant_parser.add_argument("--starts-at", type=_parse_datetime)
    grant_parser.add_argument("--expires-at", type=_parse_datetime)
    grant_parser.add_argument("--scan-quota-override", type=int)
    grant_parser.add_argument("--indefinite", action="store_true", help="Allow an indefinite complimentary/internal grant")
    grant_parser.add_argument("--reason", required=True, help="Operator reason for the grant")

    revoke_parser = subparsers.add_parser("revoke", help="Revoke an existing owner entitlement grant")
    revoke_parser.add_argument("--grant-id", required=True, help="Grant UUID to revoke")
    revoke_parser.add_argument("--reason", required=True, help="Operator reason for the revocation")

    list_parser = subparsers.add_parser("list", help="List owner entitlement grants")
    list_parser.add_argument("--active-only", action="store_true")
    list_parser.add_argument("--email")
    list_parser.add_argument("--org-id")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.command == "grant":
            grant = create_owner_entitlement_grant(
                db,
                org_id=args.org_id,
                email=args.email,
                granted_plan=args.plan,
                grant_type=args.grant_type,
                starts_at=args.starts_at,
                expires_at=args.expires_at,
                scan_quota_override=args.scan_quota_override,
                allow_indefinite=args.indefinite,
                reason=args.reason,
            )
            print(json.dumps({"status": "granted", "grant": str(grant.id)}, indent=2, sort_keys=True))
            return 0

        if args.command == "revoke":
            grant = revoke_owner_entitlement_grant(
                db,
                grant_id=args.grant_id,
                reason=args.reason,
            )
            print(json.dumps({"status": "revoked", "grant": str(grant.id)}, indent=2, sort_keys=True))
            return 0

        rows = list_owner_entitlement_grants(
            db,
            active_only=args.active_only,
            email=args.email,
            org_id=args.org_id,
        )
        print(json.dumps({"count": len(rows), "grants": rows}, indent=2, sort_keys=True))
        return 0
    except OwnerGrantError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
