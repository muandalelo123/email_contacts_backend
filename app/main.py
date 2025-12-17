
#app/main.py

# app/main.py
# app/main.py
# app/main.py
# app/main.py

import csv
import io
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from . import campaigns as campaigns_service
from . import jobs as jobs_service
from . import send_all
from .campaigns import router as campaigns_router  # router FastAPI pour /campaigns
from .config import get_settings
from .db import Base, engine, get_db
from .models import Campaign, Contact, SendJob, SendJobState
from .schemas import (
    CampaignCreate,
    CampaignRead,
    CampaignStatus,
    ContactCreate,
    ContactRead,
    ContactUpdate,
    SendJobRead,
)

# 🔹 nouveaux routers Settings
from .routers.settings_smtp import router as settings_smtp_router
from .routers.settings_general import router as settings_general_router
from .routers.settings_api_keys import router as settings_api_keys_router
from .routers.settings_billing import router as settings_billing_router
from .routers.settings_domain import router as settings_domain_router  # ✅ nouveau

# 🔑 vérification des API Keys
from .deps import verify_api_key

# ============================================================
# INITIALISATION APP / DB / CONFIG
# ============================================================

settings = get_settings()

# Création des tables si besoin
Base.metadata.create_all(bind=engine)

# Instance unique FastAPI
app = FastAPI(title="Email Marketing API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
# Builder (/campaigns/drafts, /send-test, /send-now, /schedule, etc.)
app.include_router(campaigns_router)

# Settings (SMTP + général + API keys + billing + domain)
app.include_router(settings_smtp_router)
app.include_router(settings_general_router)
app.include_router(settings_api_keys_router)
app.include_router(settings_billing_router)
app.include_router(settings_domain_router)  # ✅ nouveau

# ============================================================
# Schémas pour l'authentification et l'envoi "send-to-all"
# ============================================================


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SendEmailToAllRequest(BaseModel):
    subject: str
    body: str


# ============================================================
# AUTHENTIFICATION POUR LE FRONTEND
# (RESTE SANS CLÉ API POUR L'INSTANT)
# ============================================================


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    """
    Authentification simple basée sur ADMIN_EMAIL / ADMIN_PASSWORD
    définis dans le .env et exposés via app/config.py.
    """
    if (
        payload.email != settings.ADMIN_EMAIL
        or payload.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    # Token simple (non-JWT). Tu pourras le remplacer par un JWT plus tard.
    return LoginResponse(access_token="simple-backend-token")


# ============================================================
# LISTE DES CONTACTS (GET /contacts) – PROTÉGÉ PAR API KEY
# ============================================================


@app.get("/contacts", response_model=List[ContactRead])
def list_contacts(
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> List[ContactRead]:
    """
    Retourne la liste de tous les contacts.
    Utilisé par le frontend pour afficher le nombre de contacts.
    Requiert une clé API valide (header x-api-key).
    """
    contacts = db.query(Contact).all()
    return contacts


# ============================================================
# ENVOYER À TOUS (POST /emails/send-to-all) – PROTÉGÉ PAR API KEY
# ============================================================


@app.post("/emails/send-to-all")
def send_email_to_all(
    payload: SendEmailToAllRequest,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    """
    1) Crée une campagne à partir du subject + body envoyés par le frontend
    2) Crée les jobs d'envoi pour tous les contacts (PENDING)
    3) Enqueue ces jobs dans RQ pour qu'ils soient exécutés par le worker

    Requiert une clé API valide (header x-api-key).
    """
    # 1) Créer la campagne
    campaign = Campaign(
        subject=payload.subject,
        html=payload.body,
        from_code="DEFAULT",  # à adapter si tu as plusieurs expéditeurs
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # 2) Créer les jobs pour tous les contacts
    created = send_all.create_send_jobs_for_campaign(
        db,
        campaign_id=campaign.id,
        sender_code=campaign.from_code,
    )

    # 3) Mettre en file d'attente tous les jobs PENDING de cette campagne
    jobs = (
        db.query(SendJob)
        .filter(
            SendJob.campaign_id == campaign.id,
            SendJob.state == SendJobState.PENDING,
        )
        .all()
    )
    for j in jobs:
        jobs_service.enqueue_send_job(j.id)

    return {
        "campaign_id": campaign.id,
        "jobs_created": created,
        "enqueued": len(jobs),
    }


# ============================================================
# ENDPOINTS EXISTANTS (LEGACY) – PROTÉGÉS PAR API KEY
# ============================================================


@app.post("/campaigns/create", response_model=CampaignRead)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> CampaignRead:
    campaign = Campaign(
        subject=payload.subject,
        html=payload.html,
        from_code=payload.from_code,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.post("/contacts/import", response_model=List[ContactRead])
async def import_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> List[ContactRead]:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    created_contacts: List[Contact] = []
    for row in reader:
        email = row.get("email") or row.get("Email") or row.get("EMAIL")
        if not email:
            continue

        first_name = (
            row.get("first_name")
            or row.get("FirstName")
            or row.get("first")
            or ""
        )
        last_name = (
            row.get("last_name")
            or row.get("LastName")
            or row.get("last")
            or ""
        )

        # Skip if contact already exists
        if db.query(Contact).filter(Contact.email == email).first():
            continue

        c = Contact(email=email, first_name=first_name, last_name=last_name)
        db.add(c)
        created_contacts.append(c)

    db.commit()

    for c in created_contacts:
        db.refresh(c)

    return created_contacts


@app.post("/queue/enqueue/one", response_model=SendJobRead)
def enqueue_one_job(
    campaign_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> SendJobRead:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    job = SendJob(
        campaign_id=campaign.id,
        contact_id=contact.id,
        state=SendJobState.PENDING,
        sender_code=campaign.from_code,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    jobs_service.enqueue_send_job(job.id)
    exc_info = jobs_service.fetch_rq_exc_info(job.id)

    data = SendJobRead.model_validate(job).model_dump()
    data["exc_info"] = exc_info
    return data


@app.post("/send-to-all/{campaign_id}")
def send_to_all(
    campaign_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    created = send_all.create_send_jobs_for_campaign(
        db,
        campaign_id=campaign_id,
        sender_code=campaign.from_code,
    )
    return {"campaign_id": campaign_id, "jobs_created": created}


@app.post("/queue/process/{campaign_id}")
def enqueue_campaign_jobs(
    campaign_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    jobs = (
        db.query(SendJob)
        .filter(
            SendJob.campaign_id == campaign_id,
            SendJob.state == SendJobState.PENDING,
        )
        .all()
    )
    if not jobs:
        return {"campaign_id": campaign_id, "enqueued": 0}

    for j in jobs:
        jobs_service.enqueue_send_job(j.id)

    return {"campaign_id": campaign_id, "enqueued": len(jobs)}


@app.get("/campaigns/status/{campaign_id}", response_model=CampaignStatus)
def get_campaign_status(
    campaign_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> CampaignStatus:
    status_dict = campaigns_service.get_campaign_status(db, campaign_id)
    return CampaignStatus(**status_dict)


@app.get("/jobs/{job_id}", response_model=SendJobRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> SendJobRead:
    job = db.query(SendJob).filter(SendJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    exc_info = jobs_service.fetch_rq_exc_info(job.id)
    data = SendJobRead.model_validate(job).model_dump()
    data["exc_info"] = exc_info
    return data


@app.post("/jobs/retry-failed/{campaign_id}")
def retry_failed_jobs(
    campaign_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    failed_jobs = (
        db.query(SendJob)
        .filter(
            SendJob.campaign_id == campaign_id,
            SendJob.state == SendJobState.ERROR,
        )
        .all()
    )
    for j in failed_jobs:
        j.state = SendJobState.PENDING
        j.error_at = None
        j.error_message = None
        db.add(j)
        db.flush()
        jobs_service.enqueue_send_job(j.id)

    db.commit()
    return {"campaign_id": campaign_id, "retried": len(failed_jobs)}


