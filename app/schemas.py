
# app/schemas.py

from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, EmailStr

from .models import SendJobState


# ============================================================
# CAMPAIGNS
# ============================================================

class CampaignCreate(BaseModel):
    subject: str
    html: str
    from_code: str  # "gmail", "sendgrid", "mailgun", ...


class CampaignRead(BaseModel):
    id: int
    subject: str
    html: str
    from_code: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CONTACTS
# ============================================================

class ContactCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ContactUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ContactRead(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
# SEND JOBS
# ============================================================

class SendJobCreate(BaseModel):
    campaign_id: int
    contact_id: int
    sender_code: str


class SendJobRead(BaseModel):
    id: int
    campaign_id: int
    contact_id: int
    state: SendJobState
    sent_at: Optional[datetime]
    error_at: Optional[datetime]
    error_message: Optional[str]
    sender_code: str
    exc_info: Optional[str] = None  # Infos RQ

    class Config:
        from_attributes = True


# ============================================================
# CAMPAIGN STATUS + LOGS
# ============================================================

class CampaignStatus(BaseModel):
    campaign_id: int
    total: int
    sent: int
    errors: int
    pending: int
    in_queue: int


class CampaignLogRead(BaseModel):
    id: int
    campaign_id: int
    total: int
    sent: int
    errors: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============================================================
# 🔥 SETTINGS SMTP
# ============================================================

class SettingsSMTPBase(BaseModel):
    provider: str                     # "gmail", "smtp_custom", etc.
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = True
    from_name: Optional[str] = None
    from_email: Optional[str] = None


class SettingsSMTPRead(SettingsSMTPBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsSMTPUpdate(SettingsSMTPBase):
    """
    Même structure que SettingsSMTPBase.
    Permet une mise à jour simple via PUT /settings/smtp.
    """
    pass


# ============================================================
# 🔧 SETTINGS GÉNÉRAUX (profil, langue, notifications)
# ============================================================

class SettingsGeneralBase(BaseModel):
    display_name: Optional[str] = None
    language: str = "fr"          # "fr", "en", ...
    timezone: str = "Europe/Paris"
    theme: str = "light"          # "light" | "dark"
    notify_on_errors: bool = True
    notify_on_quota: bool = True
    notify_on_login: bool = True


class SettingsGeneralRead(SettingsGeneralBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsGeneralUpdate(SettingsGeneralBase):
    """
    Utilisé pour PUT /settings/general.
    """
    pass


# ============================================================
# 🔑 API KEYS
# ============================================================

class ApiKeyCreate(BaseModel):
    """
    Payload de création d'une clé API.
    Les scopes sont une liste de chaînes
    ex: ["emails:send", "campaigns:read"]
    """
    name: str
    scopes: List[str] = []


class ApiKeyRead(BaseModel):
    """
    Représentation d'une clé API côté lecture.

    - Pour GET /settings/api-keys : le champ `secret` vaut toujours None.
    - Pour POST /settings/api-keys : `secret` contient la clé complète
      "<key_prefix>.<secret>" une seule fois.
    """
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    scopes: List[str]
    secret: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# 💳 SETTINGS BILLING / PLAN
# ============================================================

class SettingsBillingBase(BaseModel):
    plan: str = "free"          # "free", "pro", "enterprise", ...
    monthly_quota: int = 5000   # quota mensuel d’emails
    used_quota: int = 0         # emails consommés dans la période en cours
    renews_at: datetime         # date de renouvellement du quota


class SettingsBillingRead(SettingsBillingBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsBillingUpdate(SettingsBillingBase):
    """
    Utilisé pour PUT /settings/billing.
    """
    pass


# ============================================================
# 🌐 DOMAIN & DELIVERABILITY SETTINGS (SPF / DKIM / DMARC)
# ============================================================

class DNSRecordDetail(BaseModel):
    status: str                 # "Configured" | "Not configured"
    expected: Optional[str] = None
    selector: Optional[str] = None


class DomainStatusResponse(BaseModel):
    domain: str
    records: Dict[str, DNSRecordDetail]


