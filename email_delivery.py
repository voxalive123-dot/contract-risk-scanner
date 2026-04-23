from __future__ import annotations

import os
import smtplib
import json
import urllib.error
import urllib.request
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
    use_tls: bool
    timeout_seconds: float


@dataclass(frozen=True)
class ResendEmailConfig:
    api_key: str
    api_url: str
    from_email: str
    from_name: str
    timeout_seconds: float


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def mail_provider_name() -> str:
    return os.getenv("MAIL_PROVIDER", "smtp").strip().lower() or "smtp"


def mail_from_email() -> str:
    return (
        os.getenv("MAIL_FROM_EMAIL", "").strip()
        or os.getenv("SMTP_FROM_EMAIL", "").strip()
    )


def mail_from_name() -> str:
    return (
        os.getenv("MAIL_FROM_NAME", "").strip()
        or os.getenv("SMTP_FROM_NAME", "").strip()
        or "VoxaRisk"
    )


def smtp_email_config() -> SmtpEmailConfig:
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = mail_from_email()
    if not host or not from_email:
        raise EmailDeliveryConfigError("SMTP_HOST and MAIL_FROM_EMAIL are required")

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
        from_name=mail_from_name(),
        username=os.getenv("SMTP_USERNAME", "").strip() or None,
        password=os.getenv("SMTP_PASSWORD", "").strip() or None,
        use_tls=_env_bool("SMTP_USE_TLS", True),
        timeout_seconds=timeout_seconds,
    )


def resend_email_config() -> ResendEmailConfig:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_email = mail_from_email()
    if not api_key or not from_email:
        raise EmailDeliveryConfigError("RESEND_API_KEY and MAIL_FROM_EMAIL are required")

    try:
        timeout_seconds = float(os.getenv("MAIL_API_TIMEOUT_SECONDS", "10").strip())
    except ValueError as exc:
        raise EmailDeliveryConfigError("MAIL_API_TIMEOUT_SECONDS must be numeric") from exc

    return ResendEmailConfig(
        api_key=api_key,
        api_url=os.getenv("RESEND_API_URL", "https://api.resend.com/emails").strip()
        or "https://api.resend.com/emails",
        from_email=from_email,
        from_name=mail_from_name(),
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


def send_email_via_smtp(message_payload: EmailMessagePayload) -> None:
    config = smtp_email_config()
    message = EmailMessage()
    message["Subject"] = message_payload.subject
    message["From"] = f"{config.from_name} <{config.from_email}>"
    message["To"] = message_payload.to_email
    message.set_content(message_payload.text_body)

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


def send_email_via_resend(message_payload: EmailMessagePayload) -> None:
    config = resend_email_config()
    body = json.dumps(
        {
            "from": f"{config.from_name} <{config.from_email}>",
            "to": [message_payload.to_email],
            "subject": message_payload.subject,
            "text": message_payload.text_body,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        config.api_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            if response.status >= 400:
                raise EmailDeliveryError(f"Resend returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise EmailDeliveryError(f"Resend returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise EmailDeliveryError("Resend email transport failed") from exc
    except OSError as exc:
        raise EmailDeliveryError("Resend email transport failed") from exc


def send_email(message_payload: EmailMessagePayload) -> str:
    provider = mail_provider_name()
    if provider == "smtp":
        send_email_via_smtp(message_payload)
        return provider
    if provider == "resend":
        send_email_via_resend(message_payload)
        return provider
    raise EmailDeliveryConfigError("MAIL_PROVIDER must be smtp or resend")


def send_password_reset_email(*, to_email: str, reset_url: str) -> str:
    return send_email(password_reset_message(to_email=to_email, reset_url=reset_url))
