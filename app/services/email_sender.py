

# app/services/email_sender.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.models import SettingsSMTP


def get_smtp_settings(db: Session) -> SettingsSMTP:
    """
    Retourne la configuration SMTP stockée dans la base.
    Si aucune configuration n'existe, renvoie None.
    """
    return db.query(SettingsSMTP).first()


def send_email(
    db: Session,
    to_email: str,
    subject: str,
    html_body: str,
) -> dict:
    """
    Envoie un email en utilisant les réglages SMTP enregistrés en base.
    Compatible Gmail, Outlook, SendGrid (mode SMTP), ou serveur custom.
    """

    settings = get_smtp_settings(db)
    if not settings:
        raise ValueError("Aucune configuration SMTP trouvée dans la base.")

    if not settings.smtp_host or not settings.smtp_port:
        raise ValueError("Configuration SMTP incomplète (host/port manquants).")

    if not settings.smtp_username or not settings.smtp_password:
        raise ValueError("SMTP username/password manquants.")

    # Construction du message MIME
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.from_name} <{settings.from_email}>"
    msg["To"] = to_email

    mime_html = MIMEText(html_body, "html")
    msg.attach(mime_html)

    # Envoi selon le protocole choisi
    try:
        if settings.use_tls:
            # STARTTLS (Gmail, Outlook…)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.from_email, to_email, msg.as_string())
        else:
            # Connexion simple (serveurs SMTP internes)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.from_email, to_email, msg.as_string())

    except smtplib.SMTPAuthenticationError:
        raise ValueError("Échec d'authentification SMTP : identifiants incorrects.")
    except smtplib.SMTPConnectError:
        raise ValueError("Impossible de se connecter au serveur SMTP.")
    except Exception as exc:
        raise ValueError(f"Erreur SMTP : {str(exc)}")

    return {
        "status": "success",
        "sent_to": to_email,
        "provider": settings.provider,
    }


