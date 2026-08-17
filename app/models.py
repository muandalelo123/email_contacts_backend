# app/models.py

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
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

    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language = Column(String(10), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
# SEGMENTS
# ============================================================

class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ContactSegment(Base):
    __tablename__ = "contact_segments"

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    segment_id = Column(
        Integer,
        ForeignKey("segments.id", ondelete="CASCADE"),
        primary_key=True,
    )

    source = Column(String(100), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=True)


# ============================================================
# SOUMISSIONS DE LEADS
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

    # Provider préféré de la campagne.
    # Ex: smtp, gmail, sendgrid, ses.
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

    # Après fallback, ce champ contient le provider réellement utilisé.
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
# PARAMÈTRES D'ENVOI
# ============================================================

class SettingsSMTP(Base):
    __tablename__ = "settings_smtp"

    id = Column(Integer, primary_key=True, index=True)

    provider = Column(String(50), default="gmail", nullable=False)

    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)

    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)
    use_tls = Column(Boolean, default=True, nullable=False)

    sendgrid_api_key = Column(String(255), nullable=True)

    ses_region = Column(String(64), nullable=True)
    ses_access_key_id = Column(String(255), nullable=True)
    ses_secret_access_key = Column(String(255), nullable=True)


# ============================================================
# PARAMÈTRES GÉNÉRAUX
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


# ============================================================
# FUNNELS / AUTOMATIONS
# ============================================================

class Funnel(Base):
    __tablename__ = "funnels"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False, index=True)

    preferred_provider = Column(
        String(50),
        default="gmail",
        nullable=False,
    )

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    steps = relationship(
        "FunnelStep",
        back_populates="funnel",
        cascade="all, delete-orphan",
        order_by="FunnelStep.step_order",
    )

    runs = relationship(
        "FunnelRun",
        back_populates="funnel",
        cascade="all, delete-orphan",
    )


class FunnelStep(Base):
    __tablename__ = "funnel_steps"

    id = Column(Integer, primary_key=True, index=True)

    funnel_id = Column(
        Integer,
        ForeignKey("funnels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Campaign-template utilisée par cette étape.
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    step_order = Column(Integer, nullable=False)

    # Délai depuis le démarrage du Funnel.
    # 0 = immédiat
    # 60 = 1 heure
    # 1440 = 1 jour
    delay_minutes = Column(Integer, default=0, nullable=False)

    action_type = Column(
        String(50),
        default="email",
        nullable=False,
    )

    subject = Column(String(255), nullable=True)
    html = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    funnel = relationship("Funnel", back_populates="steps")
    campaign = relationship("Campaign")

    step_runs = relationship(
        "FunnelStepRun",
        back_populates="funnel_step",
        cascade="all, delete-orphan",
    )


class FunnelRun(Base):
    __tablename__ = "funnel_runs"

    id = Column(Integer, primary_key=True, index=True)

    funnel_id = Column(
        Integer,
        ForeignKey("funnels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    submission_id = Column(
        Integer,
        ForeignKey("lead_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    funnel = relationship("Funnel", back_populates="runs")
    contact = relationship("Contact")
    submission = relationship("LeadSubmission")

    step_runs = relationship(
        "FunnelStepRun",
        back_populates="funnel_run",
        cascade="all, delete-orphan",
    )


class FunnelStepRun(Base):
    __tablename__ = "funnel_step_runs"

    id = Column(Integer, primary_key=True, index=True)

    funnel_run_id = Column(
        Integer,
        ForeignKey("funnel_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    funnel_step_id = Column(
        Integer,
        ForeignKey("funnel_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(50),
        default="scheduled",
        nullable=False,
        index=True,
    )

    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)

    provider_used = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    funnel_run = relationship(
        "FunnelRun",
        back_populates="step_runs",
    )

    funnel_step = relationship(
        "FunnelStep",
        back_populates="step_runs",
    )




