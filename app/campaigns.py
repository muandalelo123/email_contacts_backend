# app/campaigns.py

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .email_utils import send_email
from .models import Campaign, SendJob, SendJobState

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
    Envoie un email de test à une seule adresse.
    """
    try:
        send_email(
            to=payload.to_email,
            subject=payload.subject,
            html=payload.content,
            sender_code="gmail",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": "Test email sent"}


@router.post("/send-now")
async def send_now(payload: CampaignSendNowIn):
    """
    Envoi immédiat de la campagne.
    Route placeholder pour l’instant.
    La vraie logique bulk est déjà gérée ailleurs dans ton projet.
    """
    try:
        # TODO:
        # Brancher ici plus tard la vraie logique de campagne
        # (récupération des contacts, création de jobs, queue, etc.)
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": "Campaign sent immediately"}


@router.post("/schedule")
async def schedule_campaign(payload: CampaignScheduleIn):
    """
    Planifie une campagne pour plus tard.
    """
    return {
        "status": "ok",
        "message": f"Campaign scheduled for {payload.send_at.isoformat()}",
    }


# ==========================
# Service interne utilisé par main.py
# ==========================

def get_campaign_status(db: Session, campaign_id: int) -> dict:
    """
    Fonction de service appelée depuis main.py :
        campaigns_service.get_campaign_status(db, campaign_id)

    Retourne un dictionnaire compatible avec le schéma CampaignStatus.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    jobs = db.query(SendJob).filter(SendJob.campaign_id == campaign_id).all()

    total_jobs = len(jobs)
    pending_jobs = sum(1 for j in jobs if j.state == SendJobState.PENDING)
    sent_jobs = sum(1 for j in jobs if j.state == SendJobState.SENT)
    error_jobs = sum(1 for j in jobs if j.state == SendJobState.ERROR)

    if total_jobs == 0:
        status = "draft"
    elif sent_jobs == total_jobs:
        status = "completed"
    elif error_jobs == total_jobs:
        status = "failed"
    elif pending_jobs > 0:
        status = "in_progress"
    elif sent_jobs > 0 and error_jobs > 0:
        status = "partially_completed"
    else:
        status = "unknown"

    return {
        "campaign_id": campaign.id,
        "subject": campaign.subject,
        "status": status,
        "total_jobs": total_jobs,
        "pending_jobs": pending_jobs,
        "sent_jobs": sent_jobs,
        "error_jobs": error_jobs,
    }



