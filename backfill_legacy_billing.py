from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from db import SessionLocal
from legacy_billing_backfill import backfill_legacy_billing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill legacy VoxaRisk billing fields into Phase 10 subscription truth.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply eligible backfills. Omit this flag for dry-run mode.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        decisions = backfill_legacy_billing(db, dry_run=not args.apply)
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "dry_run",
                    "decisions": [asdict(decision) for decision in decisions],
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
