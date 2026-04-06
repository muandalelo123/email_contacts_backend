
# app/email_utils.py
# app/email_utils.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from .config import get_settings

settings = get_settings()


def _send_via_smtp(to: str, subject: str, html: str) -> None:
    """
    Envoi via un serveur SMTP (Gmail / Workspace / serveur SMTP classique).
    """
    if not settings.SMTP_SERVER or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP settings are not configured")

    # Log complet de la config utilisée
    print(
        f"[SMTP] Using SMTP_USER={settings.SMTP_USER}, "
        f"server={settings.SMTP_SERVER}:{settings.SMTP_PORT}, "
        f"PASS_LEN={len(settings.SMTP_PASSWORD or '')}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SENDER_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to

    msg.attach(MIMEText(html, "html", "utf-8"))

    # Connexion SMTP
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=30) as server:
        # Debug SMTP complet (montre toutes les commandes/réponses)
        # server.set_debuglevel(1)

        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [to], msg.as_string())

    print(f"[SMTP] Email sent to {to}")


def _send_via_sendgrid(to: str, subject: str, html: str) -> None:
    """
    Envoi via SendGrid API.
    """
    if not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL:
        raise RuntimeError("SendGrid settings are not configured")

    print(f"[SENDGRID] Sending email to {to}")

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDER_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    if resp.status_code >= 400:
        raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.text}")

    print(f"[SENDGRID] Email accepted for {to}")


def _send_via_mailgun(to: str, subject: str, html: str) -> None:
    """
    Envoi via Mailgun API.
    """
    if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
        raise RuntimeError("Mailgun settings are not configured")

    print(f"[MAILGUN] Sending email to {to}")

    url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    auth = ("api", settings.MAILGUN_API_KEY)
    data = {
        "from": f"{settings.SENDER_NAME} <mailgun@{settings.MAILGUN_DOMAIN}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }

    resp = requests.post(url, auth=auth, data=data, timeout=10)

    if resp.status_code >= 400:
        raise RuntimeError(f"Mailgun error {resp.status_code}: {resp.text}")

    print(f"[MAILGUN] Email accepted for {to}")


def send_email(to: str, subject: str, html: str, sender_code: str) -> None:
    """
    Router principal.
    sender_code:
      - "gmail" / "smtp" -> _send_via_smtp
      - "sendgrid"
      - "mailgun"
      - fallback = SMTP
    """
    sender = (sender_code or "").lower()

    print(f"[EMAIL] sender_code={sender}, to={to}")

    if sender in {"gmail", "smtp"}:
        _send_via_smtp(to, subject, html)
    elif sender == "sendgrid":
        _send_via_sendgrid(to, subject, html)
    elif sender == "mailgun":
        _send_via_mailgun(to, subject, html)
    else:
        print(f"[EMAIL] Unknown sender '{sender}', fallback SMTP")
        _send_via_smtp(to, subject, html)








