# app/routers/settings_smtp.py

# app/routers/settings_smtp.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_api_key
from ..models import SettingsSMTP
from ..schemas import SettingsSMTPRead, SettingsSMTPUpdate

router = APIRouter(
    prefix="/settings/smtp",
    tags=["Settings - SMTP"],
)


def _get_or_create_global_settings(db: Session) -> SettingsSMTP:
    """
    Settings globaux : une seule ligne (id=1).
    Si absente, on la crée avec des valeurs par défaut.
    """
    settings = db.query(SettingsSMTP).filter(SettingsSMTP.id == 1).first()
    if settings:
        return settings

    settings = SettingsSMTP(
        id=1,
        provider="gmail",
        from_name="iBCB RoketMail",
        from_email=None,

        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username=None,
        smtp_password=None,
        use_tls=True,

        # providers alternatifs (optionnels)
        sendgrid_api_key=None,
        ses_region=None,
        ses_access_key_id=None,
        ses_secret_access_key=None,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/", response_model=SettingsSMTPRead)
def get_smtp_settings(
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> SettingsSMTPRead:
    """
    Retourne la configuration SMTP globale (id=1).
    """
    settings = _get_or_create_global_settings(db)
    return SettingsSMTPRead.model_validate(settings)


@router.put("/", response_model=SettingsSMTPRead)
def update_smtp_settings(
    payload: SettingsSMTPUpdate,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> SettingsSMTPRead:
    """
    Met à jour la configuration SMTP globale (id=1).
    """
    settings = _get_or_create_global_settings(db)

    data = payload.model_dump()

    # Mise à jour champ par champ (upsert global)
    for key, value in data.items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return SettingsSMTPRead.model_validate(settings)



