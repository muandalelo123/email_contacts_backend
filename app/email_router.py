from __future__ import annotations

from typing import List

import requests
from sqlalchemy.orm import Session

from . import email_utils
from .models import SettingsSMTP


def _get_smtp_settings(db: Session) -> SettingsSMTP | None:
    return db.query(SettingsSMTP).order_by(SettingsSMTP.id.asc()).first()


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _build_provider_order(default_provider: str | None, sender_code: str | None) -> List[str]:
    sender_code = (sender_code or "").strip().lower()
    default_provider = (default_provider or "gmail").strip().lower()

    if sender_code in {"gmail", "smtp", "sendgrid", "ses"}:
        primary = sender_code
    else:
        primary = default_provider

    fallback = {
        "gmail": ["gmail", "sendgrid", "ses"],
        "smtp": ["smtp", "sendgrid", "ses"],
        "sendgrid": ["sendgrid", "gmail", "ses"],
        "ses": ["ses", "sendgrid", "gmail"],
    }

    return _dedupe_keep_order(fallback.get(primary, [default_provider, "sendgrid", "ses"]))


def _send_via_gmail_or_smtp(
    to: str,
    subject: str,
    html: str,
    sender_code: str,
) -> dict:
    email_utils.send_email(
        to=to,
        subject=subject,
        html=html,
        sender_code=sender_code,
    )
    return {"provider": sender_code, "message": "sent"}


def _send_via_sendgrid(
    db: Session,
    to: str,
    subject: str,
    html: str,
) -> dict:
    smtp_settings = _get_smtp_settings(db)
    if not smtp_settings or not smtp_settings.sendgrid_api_key:
        raise RuntimeError("SendGrid API key not configured")

    if not smtp_settings.from_email:
        raise RuntimeError("from_email is not configured in SettingsSMTP")

    from_name = smtp_settings.from_name or "iBCB RocketMail"

    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {
            "email": smtp_settings.from_email,
            "name": from_name,
        },
        "subject": subject,
        "content": [
            {
                "type": "text/html",
                "value": html,
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {smtp_settings.sendgrid_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.status_code >= 300:
        raise RuntimeError(f"SendGrid error {response.status_code}: {response.text}")

    return {"provider": "sendgrid", "message": "sent"}


def _send_via_ses(
    db: Session,
    to: str,
    subject: str,
    html: str,
) -> dict:
    smtp_settings = _get_smtp_settings(db)
    if not smtp_settings:
        raise RuntimeError("SES settings not configured")

    if not all([
        smtp_settings.ses_region,
        smtp_settings.ses_access_key_id,
        smtp_settings.ses_secret_access_key,
        smtp_settings.from_email,
    ]):
        raise RuntimeError("Amazon SES settings are incomplete")

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for SES") from exc

    client = boto3.client(
        "ses",
        region_name=smtp_settings.ses_region,
        aws_access_key_id=smtp_settings.ses_access_key_id,
        aws_secret_access_key=smtp_settings.ses_secret_access_key,
    )

    response = client.send_email(
        Source=smtp_settings.from_email,
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Html": {"Data": html},
            },
        },
    )

    message_id = response.get("MessageId")
    return {"provider": "ses", "message": "sent", "message_id": message_id}


def send_email_with_fallback(
    db: Session,
    to: str,
    subject: str,
    html: str,
    sender_code: str | None = None,
) -> dict:
    smtp_settings = _get_smtp_settings(db)
    default_provider = smtp_settings.provider if smtp_settings else "gmail"
    provider_order = _build_provider_order(default_provider, sender_code)

    last_error = None

    for provider in provider_order:
        try:
            if provider in {"gmail", "smtp"}:
                return _send_via_gmail_or_smtp(
                    to=to,
                    subject=subject,
                    html=html,
                    sender_code=provider,
                )

            if provider == "sendgrid":
                return _send_via_sendgrid(
                    db=db,
                    to=to,
                    subject=subject,
                    html=html,
                )

            if provider == "ses":
                return _send_via_ses(
                    db=db,
                    to=to,
                    subject=subject,
                    html=html,
                )

            raise RuntimeError(f"Unknown provider: {provider}")

        except Exception as exc:  # noqa: BLE001
            last_error = f"{provider}: {exc}"

    raise RuntimeError(last_error or "All providers failed")


