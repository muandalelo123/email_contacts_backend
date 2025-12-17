

# app/routers/settings_general.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SettingsGeneral
from ..schemas import SettingsGeneralRead, SettingsGeneralUpdate

router = APIRouter(
    prefix="/settings/general",
    tags=["Settings - General"],
)


@router.get("/", response_model=SettingsGeneralRead)
def get_general_settings(
    db: Session = Depends(get_db),
) -> SettingsGeneralRead:
    """
    Retourne les paramètres généraux :
    - profil (display_name)
    - langue
    - fuseau horaire
    - thème (light/dark)
    - notifications (erreurs, quota, connexion)
    """
    settings = db.query(SettingsGeneral).first()

    if not settings:
        # Valeurs par défaut non persistées
        return SettingsGeneralRead(
            id=None,
            display_name="iBCB RoketMail Admin",
            language="fr",
            timezone="Europe/Paris",
            theme="light",
            notify_on_errors=True,
            notify_on_quota=True,
            notify_on_login=True,
        )

    return SettingsGeneralRead.from_orm(settings)


@router.put("/", response_model=SettingsGeneralRead)
def update_general_settings(
    payload: SettingsGeneralUpdate,
    db: Session = Depends(get_db),
) -> SettingsGeneralRead:
    """
    Crée ou met à jour les paramètres généraux.
    Un seul enregistrement SettingsGeneral est utilisé pour toute l’application.
    """
    settings = db.query(SettingsGeneral).first()
    data = payload.model_dump()

    if not settings:
        # Création
        settings = SettingsGeneral(**data)
        db.add(settings)
    else:
        # Mise à jour champ par champ
        for key, value in data.items():
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return SettingsGeneralRead.from_orm(settings)



