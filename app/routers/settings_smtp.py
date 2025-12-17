# app/routers/settings_smtp.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SettingsSMTP
from ..schemas import SettingsSMTPRead, SettingsSMTPUpdate

router = APIRouter(
    prefix="/settings/smtp",
    tags=["Settings - SMTP"],
)


@router.get("/", response_model=SettingsSMTPRead)
def get_smtp_settings(db: Session = Depends(get_db)) -> SettingsSMTPRead:
    """
    Retourne la configuration SMTP actuelle.
    Si aucune configuration n'existe, renvoie des valeurs par défaut (non persistées).
    """
    settings = db.query(SettingsSMTP).first()

    if not settings:
        # Valeurs par défaut sûres (non enregistrées en base)
        return SettingsSMTPRead(
            id=None,
            provider="gmail",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            use_tls=True,
            from_name="iBCB RoketMail",
            from_email=None,
        )

    return SettingsSMTPRead.model_validate(settings)


@router.put("/", response_model=SettingsSMTPRead)
def update_smtp_settings(
    payload: SettingsSMTPUpdate,
    db: Session = Depends(get_db),
) -> SettingsSMTPRead:
    """
    Crée ou met à jour la configuration SMTP globale.
    Un seul enregistrement SettingsSMTP est utilisé pour toute l’application.
    """
    settings = db.query(SettingsSMTP).first()
    data = payload.model_dump()

    if not settings:
        # Création
        settings = SettingsSMTP(**data)
        db.add(settings)
    else:
        # Mise à jour champ par champ
        for key, value in data.items():
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return SettingsSMTPRead.model_validate(settings)



