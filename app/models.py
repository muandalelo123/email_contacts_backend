# app/models.py

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Enum as SqlEnum,
)
from sqlalchemy.orm import relationship

from .db import Base


# ============================================================
# ÉTATS DES ENVOIS
# ============================================================

class SendJobState(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ERROR = "error"


# ============================================================
# CAMPAGNES
# ============================================================

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(255), nullable=False)
    html = Column(Text, nullable=False)
    from_code = Column(String(50), nullable=False)  # ex: "smtp", "gmail", "sendgrid"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    jobs = relationship(
        "SendJob",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "CampaignLog",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


# ============================================================
# CONTACTS
# ============================================================

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    jobs = relationship("SendJob", back_populates="contact")


# ============================================================
# JOBS D'ENVOI
# ============================================================

class SendJob(Base):
    __tablename__ = "send_jobs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)

    state = Column(
        SqlEnum(SendJobState),
        default=SendJobState.PENDING,
        nullable=False,
    )
    sent_at = Column(DateTime, nullable=True)
    error_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # code du canal d'envoi utilisé : "smtp", "gmail", "sendgrid", "mailgun", etc.
    sender_code = Column(String(50), nullable=False)

    campaign = relationship("Campaign", back_populates="jobs")
    contact = relationship("Contact", back_populates="jobs")


# ============================================================
# LOGS DES CAMPAGNES
# ============================================================

class CampaignLog(Base):
    __tablename__ = "campaign_logs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)

    total = Column(Integer, nullable=False)
    sent = Column(Integer, nullable=False)
    errors = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="logs")


# ============================================================
# 🔥 PARAMÈTRES SMTP
# ============================================================

class SettingsSMTP(Base):
    __tablename__ = "settings_smtp"

    id = Column(Integer, primary_key=True, index=True)

    provider = Column(String(50), default="gmail")
    # gmail, smtp_custom, sendgrid_smtp, outlook_smtp, etc.

    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)

    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)  # stocké en clair pour l'instant

    use_tls = Column(Boolean, default=True)

    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)


# ============================================================
# 🔧 PARAMÈTRES GÉNÉRAUX (profil, langue, notifications)
# ============================================================

class SettingsGeneral(Base):
    __tablename__ = "settings_general"

    id = Column(Integer, primary_key=True, index=True)

    # Nom affiché dans l’interface (ex : "Claude / iBCB Admin")
    display_name = Column(String(255), nullable=True)

    # Langue par défaut de l’interface (ex: "fr", "en")
    language = Column(String(10), default="fr", nullable=False)

    # Fuseau horaire (ex: "Europe/Paris")
    timezone = Column(String(64), default="Europe/Paris", nullable=False)

    # Thème UI (light / dark)
    theme = Column(String(20), default="light", nullable=False)

    # Notifications (email ou UI) pour certains événements
    notify_on_errors = Column(Boolean, default=True, nullable=False)
    notify_on_quota = Column(Boolean, default=True, nullable=False)
    notify_on_login = Column(Boolean, default=True, nullable=False)


# ============================================================
# 🔑 CLÉS API
# ============================================================

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    # Nom lisible dans l’UI (ex : "Prod – iBCB RocketMail", "Zapier", etc.)
    name = Column(String(255), nullable=False)

    # Préfixe visible de la clé (utilisé côté UI / logs)
    # ex: "rk_7fa3c9b4"
    key_prefix = Column(String(50), unique=True, index=True, nullable=False)

    # Hash du secret (SHA256 du segment secret, jamais renvoyé tel quel)
    secret_hash = Column(String(128), nullable=False)

    # Scopes stockés sous forme de chaîne "campaigns:read,emails:send"
    scopes = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Clé active ou non (utile si tu veux désactiver sans supprimer)
    is_active = Column(Boolean, default=True, nullable=False)


# ============================================================
# 💳 PARAMÈTRES DE FACTURATION / PLAN
# ============================================================

class SettingsBilling(Base):
    __tablename__ = "settings_billing"

    id = Column(Integer, primary_key=True, index=True)

    # Plan actuel : "free", "pro", "enterprise", etc.
    plan = Column(String(50), default="free", nullable=False)

    # Quota d’emails mensuel
    monthly_quota = Column(Integer, default=5000, nullable=False)

    # Nombre d’emails déjà consommés dans la période courante
    used_quota = Column(Integer, default=0, nullable=False)

    # Date de renouvellement du quota (ex: début de mois)
    renews_at = Column(DateTime, default=datetime.utcnow, nullable=False)





