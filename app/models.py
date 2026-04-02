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
# CONTACTS
# ============================================================

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)

    # Identité contact
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Champs utiles pour les leads capturés depuis les landing pages
    language = Column(String(10), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    jobs = relationship(
        "SendJob",
        back_populates="contact",
        cascade="all, delete-orphan",
    )

    lead_submissions = relationship(
        "LeadSubmission",
        back_populates="contact",
        cascade="all, delete-orphan",
    )


# ============================================================
# SOUMISSIONS DE LEADS (landing pages)
# Une même personne peut soumettre plusieurs formulaires
# depuis différentes landing pages / catégories.
# ============================================================

class LeadSubmission(Base):
    __tablename__ = "lead_submissions"

    id = Column(Integer, primary_key=True, index=True)

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    submitted_at = Column(DateTime, nullable=True)
    category = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    contact = relationship("Contact", back_populates="lead_submissions")


# ============================================================
# CAMPAGNES
# ============================================================

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(255), nullable=False)
    html = Column(Text, nullable=False)

    # code du canal d'envoi par défaut pour cette campagne
    # (ex: "smtp", "gmail", "sendgrid", "ses")
    from_code = Column(String(50), nullable=False)

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
# JOBS D'ENVOI
# ============================================================

class SendJob(Base):
    __tablename__ = "send_jobs"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    state = Column(
        SqlEnum(SendJobState),
        default=SendJobState.PENDING,
        nullable=False,
    )

    sent_at = Column(DateTime, nullable=True)
    error_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # code du canal d'envoi réellement utilisé : "smtp", "gmail", "sendgrid", "ses", etc.
    sender_code = Column(String(50), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="jobs")
    contact = relationship("Contact", back_populates="jobs")


# ============================================================
# LOGS DES CAMPAGNES
# ============================================================

class CampaignLog(Base):
    __tablename__ = "campaign_logs"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    total = Column(Integer, nullable=False)
    sent = Column(Integer, nullable=False)
    errors = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="logs")


# ============================================================
# PARAMÈTRES D'ENVOI (GLOBAL) — SMTP / SENDGRID / SES
# Cette table est "globale" : on garde un seul enregistrement (id=1).
# ============================================================

class SettingsSMTP(Base):
    __tablename__ = "settings_smtp"

    id = Column(Integer, primary_key=True, index=True)

    # Provider sélectionné par défaut
    provider = Column(String(50), default="gmail", nullable=False)

    # Identité expéditeur (commune)
    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)

    # -------- SMTP (gmail / smtp custom / outlook etc.) --------
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)  # à sécuriser plus tard
    use_tls = Column(Boolean, default=True, nullable=False)

    # -------- SendGrid (API) --------
    sendgrid_api_key = Column(String(255), nullable=True)

    # -------- Amazon SES --------
    ses_region = Column(String(64), nullable=True)
    ses_access_key_id = Column(String(255), nullable=True)
    ses_secret_access_key = Column(String(255), nullable=True)


# ============================================================
# PARAMÈTRES GÉNÉRAUX (profil, langue, notifications)
# ============================================================

class SettingsGeneral(Base):
    __tablename__ = "settings_general"

    id = Column(Integer, primary_key=True, index=True)

    display_name = Column(String(255), nullable=True)
    language = Column(String(10), default="fr", nullable=False)
    timezone = Column(String(64), default="Europe/Paris", nullable=False)
    theme = Column(String(20), default="light", nullable=False)

    notify_on_errors = Column(Boolean, default=True, nullable=False)
    notify_on_quota = Column(Boolean, default=True, nullable=False)
    notify_on_login = Column(Boolean, default=True, nullable=False)


# ============================================================
# CLÉS API
# ============================================================

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    key_prefix = Column(String(50), unique=True, index=True, nullable=False)
    secret_hash = Column(String(128), nullable=False)
    scopes = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


# ============================================================
# PARAMÈTRES DE FACTURATION / PLAN
# ============================================================

class SettingsBilling(Base):
    __tablename__ = "settings_billing"

    id = Column(Integer, primary_key=True, index=True)

    plan = Column(String(50), default="free", nullable=False)
    monthly_quota = Column(Integer, default=5000, nullable=False)
    used_quota = Column(Integer, default=0, nullable=False)
    renews_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============================================================
# UNSUBSCRIBES
# ============================================================

class Unsubscribe(Base):
    __tablename__ = "unsubscribes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)




# ============================================================
# LINK ROTATOR / CLICK TRACKING
# ============================================================

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label = Column(String(255), nullable=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign")
    variants = relationship(
        "LinkVariant",
        back_populates="link",
        cascade="all, delete-orphan",
    )
    clicks = relationship(
        "ClickEvent",
        back_populates="link",
        cascade="all, delete-orphan",
    )


class LinkVariant(Base):
    __tablename__ = "link_variants"

    id = Column(Integer, primary_key=True, index=True)

    link_id = Column(
        Integer,
        ForeignKey("links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = Column(Text, nullable=False)
    weight = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    link = relationship("Link", back_populates="variants")
    clicks = relationship(
        "ClickEvent",
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class ClickEvent(Base):
    __tablename__ = "click_events"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    link_id = Column(
        Integer,
        ForeignKey("links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variant_id = Column(
        Integer,
        ForeignKey("link_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    clicked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)

    link = relationship("Link", back_populates="clicks")
    variant = relationship("LinkVariant", back_populates="clicks")
    campaign = relationship("Campaign")
    contact = relationship("Contact")





