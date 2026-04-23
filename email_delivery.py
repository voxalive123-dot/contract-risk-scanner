from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import urlencode


class EmailDeliveryConfigError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


@dataclass(frozen=True)
class SmtpEmailConfig:
    host: str
    port: int
    from_email: str
    from_name: str
    username: str | None
    password: str | None
    use_tls: bool
    timeout_seconds: float


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def smtp_email_config() -> SmtpEmailConfig:
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not host or not from_email:
        raise EmailDeliveryConfigError("SMTP_HOST and SMTP_FROM_EMAIL are required")

    try:
        port = int(os.getenv("SMTP_PORT", "587").strip())
    except ValueError as exc:
        raise EmailDeliveryConfigError("SMTP_PORT must be an integer") from exc

    try:
        timeout_seconds = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10").strip())
    except ValueError as exc:
        raise EmailDeliveryConfigError("SMTP_TIMEOUT_SECONDS must be numeric") from exc

    return SmtpEmailConfig(
        host=host,
        port=port,
        from_email=from_email,
        from_name=os.getenv("SMTP_FROM_NAME", "VoxaRisk").strip() or "VoxaRisk",
        username=os.getenv("SMTP_USERNAME", "").strip() or None,
        password=os.getenv("SMTP_PASSWORD", "").strip() or None,
        use_tls=_env_bool("SMTP_USE_TLS", True),
        timeout_seconds=timeout_seconds,
    )


def password_reset_url(token: str) -> str:
    base_url = os.getenv("PASSWORD_RESET_BASE_URL", "http://localhost:3000/reset-password").strip()
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def send_password_reset_email(*, to_email: str, reset_url: str) -> None:
    config = smtp_email_config()
    message = EmailMessage()
    message["Subject"] = "Reset your VoxaRisk password"
    message["From"] = f"{config.from_name} <{config.from_email}>"
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                "You requested a VoxaRisk password reset.",
                "",
                "Use this link to set a new password:",
                reset_url,
                "",
                "This link is time-limited and single-use.",
                "If you did not request this, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds) as smtp:
            if config.use_tls:
                smtp.starttls()
            if config.username and config.password:
                smtp.login(config.username, config.password)
            smtp.send_message(message)
    except smtplib.SMTPException as exc:
        raise EmailDeliveryError("Password reset email could not be delivered") from exc
    except OSError as exc:
        raise EmailDeliveryError("Password reset email transport failed") from exc
