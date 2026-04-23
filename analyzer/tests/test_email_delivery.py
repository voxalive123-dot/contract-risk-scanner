from __future__ import annotations

from email_delivery import EmailDeliveryConfigError, password_reset_url, send_password_reset_email
import email_delivery


def test_password_reset_url_uses_configured_base(monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_BASE_URL", "https://app.voxarisk.test/reset-password")

    assert password_reset_url("reset-token") == "https://app.voxarisk.test/reset-password?token=reset-token"


def test_send_password_reset_email_uses_starttls_smtp(monkeypatch):
    sent = {}

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            sent["host"] = host
            sent["port"] = port
            sent["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["username"] = username
            sent["password"] = password

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setenv("SMTP_HOST", "smtp.voxarisk.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "accounts@voxarisk.test")
    monkeypatch.setenv("SMTP_FROM_NAME", "VoxaRisk Accounts")
    monkeypatch.setattr(email_delivery.smtplib, "SMTP", FakeSmtp)

    provider = send_password_reset_email(
        to_email="customer@example.test",
        reset_url="https://app.voxarisk.test/reset-password?token=abc",
    )

    assert provider == "smtp"
    assert sent["host"] == "smtp.voxarisk.test"
    assert sent["port"] == 587
    assert sent["timeout"] == 10
    assert sent["starttls"] is True
    assert sent["username"] == "smtp-user"
    assert sent["password"] == "smtp-password"
    assert sent["message"]["To"] == "customer@example.test"
    assert sent["message"]["From"] == "VoxaRisk Accounts <accounts@voxarisk.test>"
    assert "https://app.voxarisk.test/reset-password?token=abc" in sent["message"].get_content()


def test_send_password_reset_email_uses_ssl_smtp_for_port_465(monkeypatch):
    sent = {}

    class FakeSmtpSsl:
        def __init__(self, host, port, timeout):
            sent["host"] = host
            sent["port"] = port
            sent["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def login(self, username, password):
            sent["username"] = username
            sent["password"] = password

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setenv("SMTP_HOST", "s917.lon1.mysecurecloudhost.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USERNAME", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "VoxaRisk")
    monkeypatch.setattr(email_delivery.smtplib, "SMTP_SSL", FakeSmtpSsl)

    provider = send_password_reset_email(
        to_email="admin.dashboard@voxarisk.com",
        reset_url="https://app.voxarisk.com/reset-password?token=abc",
    )

    assert provider == "smtp"
    assert sent["host"] == "s917.lon1.mysecurecloudhost.com"
    assert sent["port"] == 465
    assert sent["username"] == "admin.dashboard@voxarisk.com"
    assert sent["message"]["From"] == "VoxaRisk <admin.dashboard@voxarisk.com>"


def test_send_password_reset_email_requires_smtp_config(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)

    try:
        send_password_reset_email(
            to_email="customer@example.test",
            reset_url="https://app.voxarisk.test/reset-password?token=abc",
        )
    except EmailDeliveryConfigError as exc:
        assert "SMTP_HOST and SMTP_FROM_EMAIL are required" in str(exc)
    else:
        raise AssertionError("Expected missing SMTP config to fail closed")
