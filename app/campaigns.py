
# app/campaigns.py

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

# Import à adapter selon ton projet :
# Ici, on suppose que tu as déjà une fonction send_email dans app/email_utils.py
from .email_utils import send_email  # fonction existante d’envoi d’email

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ==========================
# Schémas Pydantic
# ==========================

class CampaignBase(BaseModel):
    name: str
    subject: str
    from_name: str
    from_email: EmailStr
    segment: str
    content: str


class DraftOut(BaseModel):
    id: int
    status: str = "draft_saved"


class TestEmailIn(CampaignBase):
    to_email: EmailStr


class CampaignSendNowIn(CampaignBase):
    """
    Pour l’instant identique à CampaignBase.
    Tu pourras ajouter des champs (ex: filters, tags…) plus tard.
    """
    pass


class CampaignScheduleIn(CampaignBase):
    send_at: datetime


# ==========================
# Routes API
# ==========================

@router.post("/drafts", response_model=DraftOut)
async def save_draft(payload: CampaignBase):
    """
    Enregistre un brouillon de campagne.
    Pour l’instant : renvoie un id fictif.
    Plus tard : insérer en base et renvoyer l’id réel.
    """
    fake_id = 1
    return DraftOut(id=fake_id)


@router.post("/send-test")
async def send_test_email(payload: TestEmailIn):
    """
    Envoie un email de test à une seule adresse (to_email).
    """
    try:
        send_email(
            subject=payload.subject,
            body=payload.content,
            sender=payload.from_email,
            recipients=[payload.to_email],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": "Test email sent"}


@router.post("/send-now")
async def send_now(payload: CampaignSendNowIn):
    """
    Envoi immédiat de la campagne à tous les contacts.
    Pour le moment, la logique réelle n’est pas encore branchée.
    """
    try:
        # TODO :
        # 1) Récupérer les contacts en base
        # 2) Construire la liste des emails
        # 3) Appeler send_email(...) avec tous les destinataires
        #
        # Exemple futur :
        # contacts = get_all_contacts()
        # recipients = [c.email for c in contacts]
        # send_email(
        #     subject=payload.subject,
        #     body=payload.content,
        #     sender=payload.from_email,
        #     recipients=recipients,
        # )
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": "Campaign sent immediately"}


@router.post("/schedule")
async def schedule_campaign(payload: CampaignScheduleIn):
    """
    Planifie l'envoi d'une campagne pour plus tard.
    Pour l’instant, on renvoie uniquement un message de confirmation.
    """
    # TODO :
    # 1) Sauvegarder la campagne + date dans la DB
    # 2) Créer un job différé (Celery / RQ / cron)
    return {
        "status": "ok",
        "message": f"Campaign scheduled for {payload.send_at.isoformat()}",
    }


