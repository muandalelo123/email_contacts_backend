

# app/routers/settings_billing.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..db import get_db
from ..models import SettingsBilling
from ..schemas import SettingsBillingRead, SettingsBillingUpdate

router = APIRouter(
    prefix="/settings/billing",
    tags=["Settings - Billing"],
)


@router.get("/", response_model=SettingsBillingRead)
def get_billing_settings(db: Session = Depends(get_db)) -> SettingsBillingRead:
    """
    Retourne les paramètres de facturation (plan + quotas).
    Si aucun plan n'existe encore, renvoie un plan "Free" par défaut.
    """
    settings = db.query(SettingsBilling).first()

    if not settings:
        return SettingsBillingRead(
            id=None,
            plan="free",
            monthly_quota=5000,
            used_quota=0,
            renews_at=datetime.utcnow(),
        )

    return SettingsBillingRead.from_orm(settings)


@router.put("/", response_model=SettingsBillingRead)
def update_billing_settings(
    payload: SettingsBillingUpdate,
    db: Session = Depends(get_db),
) -> SettingsBillingRead:
    """
    Met à jour le plan et les quotas.
    Exemple :
    - free → 5000 emails / mois
    - pro → 50 000 emails / mois
    - enterprise → illimité
    """
    settings = db.query(SettingsBilling).first()

    if not settings:
        settings = SettingsBilling(**payload.model_dump())
        db.add(settings)
    else:
        for key, value in payload.model_dump().items():
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return SettingsBillingRead.from_orm(settings)


