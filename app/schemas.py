
# app/schemas.py

from datetime import datetime
from typing import Optional, List, Dict, Literal

from pydantic import BaseModel, EmailStr

from .models import SendJobState


# ============================================================
# CAMPAIGNS
# ============================================================

class CampaignCreate(BaseModel):
    subject: str
    html: str
    from_code: str


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
    language: Optional[str] = None


class ContactUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None


class ContactRead(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# LEADS / LANDING
# ============================================================

class LeadSubmissionCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None

    submitted_at: Optional[datetime] = None
    category: Optional[str] = None
    source: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class LeadSubmissionRead(BaseModel):
    id: int
    contact_id: int
    submitted_at: Optional[datetime] = None
    category: Optional[str] = None
    source: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadSubmissionResponse(BaseModel):
    message: str
    contact_id: int
    submission_id: int


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
    sent_at: Optional[datetime] = None
    error_at: Optional[datetime] = None
    error_message: Optional[str] = None
    sender_code: str
    created_at: datetime
    exc_info: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# CAMPAIGN STATUS + LOGS (CORRIGÉ)
# ============================================================

class CampaignStatus(BaseModel):
    campaign_id: int
    subject: str
    status: str
    total_jobs: int
    pending_jobs: int
    sent_jobs: int
    error_jobs: int


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
# SETTINGS SMTP / PROVIDERS
# ============================================================

ProviderName = Literal["gmail", "smtp", "sendgrid", "ses"]


class SettingsSMTPBase(BaseModel):
    provider: ProviderName = "gmail"

    from_name: Optional[str] = None
    from_email: Optional[EmailStr] = None

    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = True

    sendgrid_api_key: Optional[str] = None

    ses_region: Optional[str] = None
    ses_access_key_id: Optional[str] = None
    ses_secret_access_key: Optional[str] = None


class SettingsSMTPRead(SettingsSMTPBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsSMTPUpdate(SettingsSMTPBase):
    pass


class SettingsSMTPReadMasked(SettingsSMTPBase):
    id: Optional[int] = None
    smtp_password: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    ses_secret_access_key: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# SETTINGS GÉNÉRAUX
# ============================================================

class SettingsGeneralBase(BaseModel):
    display_name: Optional[str] = None
    language: str = "fr"
    timezone: str = "Europe/Paris"
    theme: str = "light"
    notify_on_errors: bool = True
    notify_on_quota: bool = True
    notify_on_login: bool = True


class SettingsGeneralRead(SettingsGeneralBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsGeneralUpdate(SettingsGeneralBase):
    pass


# ============================================================
# API KEYS
# ============================================================

class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []


class ApiKeyRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    scopes: List[str]
    secret: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# BILLING
# ============================================================

class SettingsBillingBase(BaseModel):
    plan: str = "free"
    monthly_quota: int = 5000
    used_quota: int = 0
    renews_at: Optional[datetime] = None


class SettingsBillingRead(SettingsBillingBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


class SettingsBillingUpdate(SettingsBillingBase):
    pass


# ============================================================
# DOMAIN / DNS
# ============================================================

class DNSRecordDetail(BaseModel):
    status: str
    expected: Optional[str] = None
    selector: Optional[str] = None


class DomainStatusResponse(BaseModel):
    domain: str
    records: Dict[str, DNSRecordDetail]


# ============================================================
# FUNNELS / AUTOMATIONS
# ============================================================

class FunnelStepCreate(BaseModel):
    step_order: int
    delay_minutes: int = 0
    action_type: str = "email"
    subject: Optional[str] = None
    html: Optional[str] = None
    is_active: bool = True


class FunnelStepRead(FunnelStepCreate):
    id: int
    funnel_id: int
    campaign_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FunnelCreate(BaseModel):
    name: str
    category: str
    preferred_provider: ProviderName = "gmail"
    is_active: bool = True


class FunnelUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    preferred_provider: Optional[ProviderName] = None
    is_active: Optional[bool] = None


class FunnelRead(BaseModel):
    id: int
    name: str
    category: str
    preferred_provider: ProviderName
    is_active: bool
    created_at: datetime
    steps: List[FunnelStepRead] = []

    class Config:
        from_attributes = True


class FunnelRunRead(BaseModel):
    id: int
    funnel_id: int
    contact_id: int
    submission_id: Optional[int] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FunnelStepRunRead(BaseModel):
    id: int
    funnel_run_id: int
    funnel_step_id: int
    status: str
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    provider_used: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

