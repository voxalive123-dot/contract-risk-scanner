from __future__ import annotations

import argparse
import json

from email_delivery import EmailDeliveryConfigError, EmailDeliveryError, password_reset_message, send_email, smtp_email_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VoxaRisk SMTP delivery from the current environment.")
    parser.add_argument("--to", required=True, help="Recipient email address for the SMTP self-test")
    args = parser.parse_args()

    try:
        config = smtp_email_config()
        provider = send_email(
            password_reset_message(
                to_email=args.to,
                reset_url="https://example.invalid/reset-password?token=smtp-self-test",
            )
        )
    except (EmailDeliveryConfigError, EmailDeliveryError) as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "provider": "smtp",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "sent",
                "provider": provider,
                "host": config.host,
                "port": config.port,
                "security": config.security,
                "from_email": config.from_email,
                "to_email": args.to,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
