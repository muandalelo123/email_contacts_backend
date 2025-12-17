
# app/api/settings.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List

router = APIRouter(prefix="/settings", tags=["Settings"])

# ---- Schémas de base ----

class ProfileSettings(BaseModel):
  full_name: str
  email: EmailStr
  phone: Optional[str] = None
  avatar_url: Optional[str] = None

class PasswordChangeRequest(BaseModel):
  current_password: str
  new_password: str

class TwoFASettings(BaseModel):
  enabled: bool

class ApiKey(BaseModel):
  id: int
  name: str
  key_prefix: str
  created_at: str
  scopes: List[str]

class ApiKeyCreate(BaseModel):
  name: str
  scopes: List[str]

class PlanInfo(BaseModel):
  plan_name: str
  monthly_limit: int
  used_this_month: int
  renews_at: str

class EmailProviderSettings(BaseModel):
  provider: str  # "gmail", "sendgrid", "ses", "smtp_custom"
  smtp_host: Optional[str] = None
  smtp_port: Optional[int] = None
  smtp_username: Optional[str] = None
  use_tls: Optional[bool] = None

class Preferences(BaseModel):
  language: str
  timezone: str
  theme: str  # "light" | "dark"
  notify_on_errors: bool
  notify_on_quota: bool

# ---- Endpoints Profil ----

@router.get("/profile", response_model=ProfileSettings)
def get_profile_settings():
  # TODO: remplacer par récupération depuis la DB
  return ProfileSettings(
    full_name="John Doe",
    email="john@example.com",
    phone=None,
    avatar_url=None
  )

@router.put("/profile", response_model=ProfileSettings)
def update_profile_settings(payload: ProfileSettings):
  # TODO: sauvegarder en DB puis retourner la version mise à jour
  return payload

# ---- Endpoints Sécurité ----

@router.post("/security/change-password")
def change_password(payload: PasswordChangeRequest):
  # TODO: vérifier current_password, changer en DB, logger l'action
  return {"detail": "Password updated (placeholder)"}

@router.get("/security/2fa", response_model=TwoFASettings)
def get_2fa_settings():
  return TwoFASettings(enabled=False)

@router.put("/security/2fa", response_model=TwoFASettings)
def update_2fa_settings(payload: TwoFASettings):
  # TODO: activer/désactiver en DB
  return payload

# ---- Endpoints API Keys ----

@router.get("/api-keys", response_model=List[ApiKey])
def list_api_keys():
  # TODO: récupérer les clés en DB
  return []

@router.post("/api-keys", response_model=ApiKey)
def create_api_key(payload: ApiKeyCreate):
  # TODO: générer la clé, stocker en DB, ne renvoyer que le prefix
  return ApiKey(
    id=1,
    name=payload.name,
    key_prefix="rk_1234",
    created_at="2025-01-01T00:00:00Z",
    scopes=payload.scopes,
  )

@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int):
  # TODO: supprimer en DB
  return {"detail": f"API key {key_id} deleted (placeholder)"}

# ---- Endpoints Plan & Facturation ----

@router.get("/plan", response_model=PlanInfo)
def get_plan_info():
  # TODO: récupérer le plan réel
  return PlanInfo(
    plan_name="Free",
    monthly_limit=5000,
    used_this_month=1200,
    renews_at="2025-02-01T00:00:00Z",
  )

# ---- Endpoints Email provider ----

@router.get("/email-provider", response_model=EmailProviderSettings)
def get_email_provider():
  # TODO: récupérer config réelle
  return EmailProviderSettings(provider="gmail")

@router.put("/email-provider", response_model=EmailProviderSettings)
def update_email_provider(payload: EmailProviderSettings):
  # TODO: sauvegarder la config
  return payload

# ---- Endpoints Préférences ----

@router.get("/preferences", response_model=Preferences)
def get_preferences():
  return Preferences(
    language="fr",
    timezone="Europe/Paris",
    theme="light",
    notify_on_errors=True,
    notify_on_quota=True,
  )

@router.put("/preferences", response_model=Preferences)
def update_preferences(payload: Preferences):
  # TODO: sauvegarder en DB
  return payload



