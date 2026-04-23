from __future__ import annotations

import argparse
import json

from db import SessionLocal
from entitlement_diagnostics import build_entitlement_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect VoxaRisk organisation entitlement state without mutating records.",
    )
    parser.add_argument("org_id", help="Organisation UUID to inspect.")
    parser.add_argument(
        "--webhook-limit",
        type=int,
        default=5,
        help="Maximum number of related webhook events to include.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        diagnostics = build_entitlement_diagnostics(
            db,
            org_id=args.org_id,
            webhook_limit=args.webhook_limit,
        )
        print(json.dumps(diagnostics, indent=2, sort_keys=True, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
