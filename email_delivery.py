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
class EmailMessagePayload:
    to_email: str
    subject: str
    text_body: str


@dataclass(frozen=True)
class SmtpEmailConfig:
    host: str
    port: int
    from_email: str
    from_name: str
    username: str | None
    password: str | None
    security: str
    timeout_seconds: float


def smtp_from_email() -> str:
    return os.getenv("SMTP_FROM_EMAIL", "").strip()


def smtp_from_name() -> str:
    return os.getenv("SMTP_FROM_NAME", "").strip() or "VoxaRisk"


def smtp_email_config() -> SmtpEmailConfig:
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = smtp_from_email()
    if not host or not from_email:
        raise EmailDeliveryConfigError("SMTP_HOST and SMTP_FROM_EMAIL are required")

    try:
        port = int(os.getenv("SMTP_PORT", "587").strip())
    except ValueError as exc:
        raise EmailDeliveryConfigError("SMTP_PORT must be an integer") from exc

    security = os.getenv("SMTP_SECURITY", "").strip().lower()
    if not security:
        security = "ssl" if port == 465 else "starttls"
    if security not in {"ssl", "starttls", "none"}:
        raise EmailDeliveryConfigError("SMTP_SECURITY must be ssl, starttls, or none")

    try:
        timeout_seconds = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10").strip())
    except ValueError as exc:
        raise EmailDeliveryConfigError("SMTP_TIMEOUT_SECONDS must be numeric") from exc

    return SmtpEmailConfig(
        host=host,
        port=port,
        from_email=from_email,
        from_name=smtp_from_name(),
        username=os.getenv("SMTP_USERNAME", "").strip() or None,
        password=os.getenv("SMTP_PASSWORD", "").strip() or None,
        security=security,
        timeout_seconds=timeout_seconds,
    )


def password_reset_url(token: str) -> str:
    base_url = os.getenv("PASSWORD_RESET_BASE_URL", "http://localhost:3000/reset-password").strip()
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'token': token})}"


def password_reset_message(*, to_email: str, reset_url: str) -> EmailMessagePayload:
    return EmailMessagePayload(
        to_email=to_email,
        subject="Reset your VoxaRisk password",
        text_body="\n".join(
            [
                "You requested a VoxaRisk password reset.",
                "",
                "Use this link to set a new password:",
                reset_url,
                "",
                "This link is time-limited and single-use.",
                "If you did not request this, you can ignore this email.",
            ]
        ),
    )


def _smtp_client(config: SmtpEmailConfig):
    if config.security == "ssl":
        return smtplib.SMTP_SSL(config.host, config.port, timeout=config.timeout_seconds)
    return smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds)


def send_email(message_payload: EmailMessagePayload) -> str:
    config = smtp_email_config()
    message = EmailMessage()
    message["Subject"] = message_payload.subject
    message["From"] = f"{config.from_name} <{config.from_email}>"
    message["To"] = message_payload.to_email
    message.set_content(message_payload.text_body)

    try:
        with _smtp_client(config) as smtp:
            if config.security == "starttls":
                smtp.starttls()
            if config.username and config.password:
                smtp.login(config.username, config.password)
            smtp.send_message(message)
    except smtplib.SMTPException as exc:
        raise EmailDeliveryError("SMTP email delivery failed") from exc
    except OSError as exc:
        raise EmailDeliveryError("SMTP email transport failed") from exc

    return "smtp"


def send_password_reset_email(*, to_email: str, reset_url: str) -> str:
    return send_email(password_reset_message(to_email=to_email, reset_url=reset_url))
