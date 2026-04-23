from __future__ import annotations

import json

import email_delivery
from email_delivery import EmailDeliveryConfigError, password_reset_url, send_password_reset_email


def test_password_reset_url_uses_configured_base(monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_BASE_URL", "https://app.voxarisk.test/reset-password")

    assert password_reset_url("reset-token") == "https://app.voxarisk.test/reset-password?token=reset-token"


def test_send_password_reset_email_uses_configured_smtp(monkeypatch):
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

    monkeypatch.setenv("MAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.voxarisk.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("MAIL_FROM_EMAIL", "accounts@voxarisk.test")
    monkeypatch.setenv("MAIL_FROM_NAME", "VoxaRisk Accounts")
    monkeypatch.setattr(email_delivery.smtplib, "SMTP", FakeSmtp)

    provider = send_password_reset_email(
        to_email="customer@example.test",
        reset_url="https://app.voxarisk.test/reset-password?token=abc",
    )

    assert provider == "smtp"
    assert sent["host"] == "smtp.voxarisk.test"
    assert sent["port"] == 2525
    assert sent["timeout"] == 10
    assert sent["starttls"] is True
    assert sent["username"] == "smtp-user"
    assert sent["password"] == "smtp-password"
    assert sent["message"]["To"] == "customer@example.test"
    assert sent["message"]["From"] == "VoxaRisk Accounts <accounts@voxarisk.test>"
    assert "https://app.voxarisk.test/reset-password?token=abc" in sent["message"].get_content()


def test_send_password_reset_email_uses_resend_api_provider(monkeypatch):
    sent = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_urlopen(request, timeout):
        sent["url"] = request.full_url
        sent["timeout"] = timeout
        sent["headers"] = dict(request.header_items())
        sent["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("MAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-test-key")
    monkeypatch.setenv("MAIL_FROM_EMAIL", "noreply@voxarisk.com")
    monkeypatch.setenv("MAIL_FROM_NAME", "VoxaRisk")
    monkeypatch.setenv("RESEND_API_URL", "https://api.resend.test/emails")
    monkeypatch.setattr(email_delivery.urllib.request, "urlopen", fake_urlopen)

    provider = send_password_reset_email(
        to_email="admin.dashboard@voxarisk.com",
        reset_url="https://app.voxarisk.com/reset-password?token=abc",
    )

    assert provider == "resend"
    assert sent["url"] == "https://api.resend.test/emails"
    assert sent["timeout"] == 10
    assert sent["headers"]["Authorization"] == "Bearer resend-test-key"
    assert sent["headers"]["User-agent"] == "VoxaRisk/1.0"
    assert sent["body"]["from"] == "VoxaRisk <noreply@voxarisk.com>"
    assert sent["body"]["to"] == ["admin.dashboard@voxarisk.com"]
    assert "https://app.voxarisk.com/reset-password?token=abc" in sent["body"]["text"]


def test_send_password_reset_email_requires_real_delivery_config_for_selected_provider(monkeypatch):
    monkeypatch.setenv("MAIL_PROVIDER", "resend")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("MAIL_FROM_EMAIL", "noreply@voxarisk.com")
    monkeypatch.delenv("SMTP_HOST", raising=False)

    try:
        send_password_reset_email(
            to_email="customer@example.test",
            reset_url="https://app.voxarisk.test/reset-password?token=abc",
        )
    except EmailDeliveryConfigError as exc:
        assert "RESEND_API_KEY and MAIL_FROM_EMAIL are required" in str(exc)
    else:
        raise AssertionError("Expected missing provider config to fail closed")
