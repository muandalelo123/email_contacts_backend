# email_router.py

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

    return _dedupe_keep_order(
        fallback.get(primary, [default_provider, "sendgrid", "ses"])
    )


def _send_via_gmail_or_smtp(
    to: str,
    subject: str,
    html: str,
    sender_code: str,
) -> dict:
    print(f"[SMTP] provider={sender_code}, to={to}")

    email_utils.send_email(
        to=to,
        subject=subject,
        html=html,
        sender_code=sender_code,
    )

    print(f"[SMTP] send_email completed via {sender_code}")
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

    print(f"[SENDGRID] to={to}")
    print(f"[SENDGRID] from={smtp_settings.from_email}")
    print(f"[SENDGRID] api_key_prefix={smtp_settings.sendgrid_api_key[:10]}...")

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

    print(f"[SENDGRID RESPONSE] status={response.status_code}")
    print(f"[SENDGRID RESPONSE] body={response.text}")

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

    if not all(
        [
            smtp_settings.ses_region,
            smtp_settings.ses_access_key_id,
            smtp_settings.ses_secret_access_key,
            smtp_settings.from_email,
        ]
    ):
        raise RuntimeError("Amazon SES settings are incomplete")

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for SES") from exc

    print(f"[SES] to={to}, from={smtp_settings.from_email}, region={smtp_settings.ses_region}")

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
    print(f"[SES] message_id={message_id}")
    return {"provider": "ses", "message": "sent", "message_id": message_id}


def send_email_with_fallback(
    db: Session,
    to: str,
    subject: str,
    html: str,
    sender_code: str | None = None,
) -> dict:
    smtp_settings = _get_smtp_settings(db)

    # Temporairement forcé pour les tests
    default_provider = "sendgrid"

    provider_order = _build_provider_order(default_provider, sender_code)
    print(f"[EMAIL ROUTER] sender_code={sender_code}, provider_order={provider_order}")

    last_error = None

    for provider in provider_order:
        try:
            print(f"[EMAIL ROUTER] trying provider={provider}")

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

        except Exception as exc:
            last_error = f"{provider}: {exc}"
            print(f"[EMAIL ROUTER ERROR] {last_error}")

    raise RuntimeError(last_error or "All providers failed")



