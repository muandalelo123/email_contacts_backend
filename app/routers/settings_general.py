
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

DEFAULT_GENERAL = dict(
    id=None,
    display_name="iBCB RoketMail Admin",
    language="fr",
    timezone="Europe/Paris",
    theme="light",
    notify_on_errors=True,
    notify_on_quota=True,
    notify_on_login=True,
)

@router.get("/", response_model=SettingsGeneralRead)
def get_general_settings(db: Session = Depends(get_db)) -> SettingsGeneralRead:
    settings = db.query(SettingsGeneral).first()
    if not settings:
        return SettingsGeneralRead(**DEFAULT_GENERAL)
    return SettingsGeneralRead.model_validate(settings)

@router.put("/", response_model=SettingsGeneralRead)
def update_general_settings(
    payload: SettingsGeneralUpdate,
    db: Session = Depends(get_db),
) -> SettingsGeneralRead:
    settings = db.query(SettingsGeneral).first()
    data = payload.model_dump()

    if not settings:
        settings = SettingsGeneral(**data)
        db.add(settings)
    else:
        for key, value in data.items():
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return SettingsGeneralRead.model_validate(settings)


