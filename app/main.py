
#app/main.py

# app/main.py
# app/main.py

import csv
import io
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from . import campaigns as campaigns_service
from . import jobs as jobs_service
from . import link_rotator
from . import send_all
from .campaigns import router as campaigns_router
from .config import get_settings
from .db import Base, engine, get_db
from .deps import verify_api_key
from .models import (
    Campaign,
    ClickEvent,
    Contact,
    LeadSubmission,
    Link,
    LinkVariant,
    SendJob,
    SendJobState,
    Unsubscribe,
)
from .routers.settings_api_keys import router as settings_api_keys_router
from .routers.settings_billing import router as settings_billing_router
from .routers.settings_domain import router as settings_domain_router
from .routers.settings_general import router as settings_general_router
from .routers.settings_smtp import router as settings_smtp_router
from .schemas import (
    CampaignCreate,
    CampaignRead,
    CampaignStatus,
    ContactRead,
    LeadSubmissionCreate,
    LeadSubmissionRead,
    LeadSubmissionResponse,
    SendJobRead,
)

# ============================================================
# INITIALISATION APP / DB / CONFIG
# ============================================================

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Email Marketing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # A restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router)
app.include_router(settings_smtp_router)
app.include_router(settings_general_router)
app.include_router(settings_api_keys_router)
app.include_router(settings_billing_router)
app.include_router(settings_domain_router)

# ============================================================
# SCHÉMAS LOCAUX
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


class UnsubscribeRequest(BaseModel):
    email: EmailStr
    reason: str | None = None


class LinkVariantCreate(BaseModel):
    url: str
    weight: int = 100
    is_active: bool = True


# ============================================================
# ROUTES UTILES
# ============================================================


@app.get("/")
def root():
    return {"status": "ok", "service": "Email Marketing API"}


@app.get("/health")
def health():
    return {"healthy": True}


# ============================================================
# HELPERS
# ============================================================


def split_full_name(full_name: str) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None

    parts = full_name.strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None

    return parts[0], " ".join(parts[1:])


def parse_datetime_safe(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ============================================================
# AUTHENTIFICATION
# ============================================================


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if (
        payload.email != settings.ADMIN_EMAIL
        or payload.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    return LoginResponse(access_token="simple-backend-token")


# ============================================================
# CONTACTS
# ============================================================


@app.get("/contacts", response_model=List[ContactRead])
def list_contacts(
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> List[ContactRead]:
    return db.query(Contact).all()


@app.get("/contacts/{contact_id}/submissions", response_model=List[LeadSubmissionRead])
def list_contact_submissions(
    contact_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
) -> List[LeadSubmissionRead]:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    submissions = (
        db.query(LeadSubmission)
        .filter(LeadSubmission.contact_id == contact_id)
        .order_by(LeadSubmission.created_at.desc())
        .all()
    )
    return submissions


# ============================================================
# LEADS / LANDING PAGES
# ============================================================


@app.post("/leads", response_model=LeadSubmissionResponse)
def create_lead_submission(
    payload: LeadSubmissionCreate,
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(Contact.email == payload.email).first()

    if not contact:
        contact = Contact(
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            language=payload.language,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
    else:
        updated = False

        if payload.first_name and not contact.first_name:
            contact.first_name = payload.first_name
            updated = True

        if payload.last_name and not contact.last_name:
            contact.last_name = payload.last_name
            updated = True

        if payload.language and not contact.language:
            contact.language = payload.language
            updated = True

        if updated:
            db.add(contact)
            db.commit()
            db.refresh(contact)

    submission = LeadSubmission(
        contact_id=contact.id,
        submitted_at=payload.submitted_at,
        category=payload.category,
        source=payload.source,
        ip_address=payload.ip_address,
        user_agent=payload.user_agent,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return LeadSubmissionResponse(
        message="Lead saved successfully",
        contact_id=contact.id,
        submission_id=submission.id,
    )


# ============================================================
# ENVOYER À TOUS
# ============================================================


@app.post("/emails/send-to-all")
def send_email_to_all(
    payload: SendEmailToAllRequest,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    campaign = Campaign(
        subject=payload.subject,
        html=payload.body,
        from_code="ses",  # corrigé : on force Amazon SES
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    created = send_all.create_send_jobs_for_campaign(
        db,
        campaign_id=campaign.id,
        sender_code=campaign.from_code,
    )

    jobs = (
        db.query(SendJob)
        .filter(
            SendJob.campaign_id == campaign.id,
            SendJob.state == SendJobState.PENDING,
        )
        .all()
    )

    for job in jobs:
        jobs_service.enqueue_send_job(job.id)

    return {
        "campaign_id": campaign.id,
        "jobs_created": created,
        "enqueued": len(jobs),
    }


# ============================================================
# CAMPAGNES
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


# ============================================================
# IMPORT CONTACTS CSV
# ============================================================


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

        language = (
            row.get("language")
            or row.get("Language")
            or row.get("LANGUAGE")
            or None
        )

        existing = db.query(Contact).filter(Contact.email == email).first()
        if existing:
            updated = False

            if first_name and not existing.first_name:
                existing.first_name = first_name
                updated = True

            if last_name and not existing.last_name:
                existing.last_name = last_name
                updated = True

            if language and not existing.language:
                existing.language = language
                updated = True

            if updated:
                db.add(existing)

            continue

        contact = Contact(
            email=email,
            first_name=first_name or None,
            last_name=last_name or None,
            language=language,
        )
        db.add(contact)
        created_contacts.append(contact)

    db.commit()

    for contact in created_contacts:
        db.refresh(contact)

    return created_contacts


# ============================================================
# QUEUE / JOBS
# ============================================================


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
def send_to_all_campaign(
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

    for job in jobs:
        jobs_service.enqueue_send_job(job.id)

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

    for job in failed_jobs:
        job.state = SendJobState.PENDING
        job.error_at = None
        job.error_message = None
        db.add(job)
        db.flush()
        jobs_service.enqueue_send_job(job.id)

    db.commit()
    return {"campaign_id": campaign_id, "retried": len(failed_jobs)}


# ============================================================
# UNSUBSCRIBE
# ============================================================


@app.get("/unsubscribe/{email}")
def unsubscribe_get(email: str, db: Session = Depends(get_db)):
    existing = db.query(Unsubscribe).filter(Unsubscribe.email == email).first()
    if existing:
        return {
            "message": "Email already unsubscribed",
            "email": email,
        }

    row = Unsubscribe(email=email)
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "message": "Email unsubscribed successfully",
        "email": email,
    }


@app.post("/unsubscribe")
def unsubscribe_post(payload: UnsubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(Unsubscribe).filter(Unsubscribe.email == payload.email).first()
    if existing:
        return {
            "message": "Email already unsubscribed",
            "email": payload.email,
        }

    row = Unsubscribe(
        email=payload.email,
        reason=payload.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "message": "Email unsubscribed successfully",
        "email": payload.email,
    }


# ============================================================
# LOGS
# ============================================================


@app.get("/logs")
def list_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    jobs = (
        db.query(SendJob)
        .order_by(SendJob.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "job_id": job.id,
            "campaign_id": job.campaign_id,
            "campaign_subject": job.campaign.subject if job.campaign else None,
            "contact_id": job.contact_id,
            "email": job.contact.email if job.contact else None,
            "state": job.state.value if hasattr(job.state, "value") else str(job.state),
            "provider": job.sender_code,
            "sent_at": job.sent_at,
            "error_at": job.error_at,
            "error_message": job.error_message,
            "created_at": job.created_at,
        }
        for job in jobs
    ]


# ============================================================
# EXPORT CONTACTS CSV
# ============================================================


@app.get("/contacts/export")
def export_contacts_csv(
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    contacts = db.query(Contact).order_by(Contact.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "id",
            "email",
            "first_name",
            "last_name",
            "language",
            "created_at",
        ]
    )

    for contact in contacts:
        writer.writerow(
            [
                contact.id,
                contact.email,
                contact.first_name or "",
                contact.last_name or "",
                contact.language or "",
                contact.created_at.isoformat() if contact.created_at else "",
            ]
        )

    output.seek(0)
    filename = f"contacts_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# LINK ROTATOR / CLICK TRACKING
# ============================================================


@app.get("/r/{link_id}")
def redirect_tracked_link(
    link_id: int,
    request: Request,
    contact_id: int | None = None,
    db: Session = Depends(get_db),
):
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    variant = link_rotator.choose_variant(db, link_id=link.id)

    destination = link.original_url
    variant_id = None

    if variant:
        destination = variant.url
        variant_id = variant.id

    link_rotator.register_click(
        db=db,
        campaign_id=link.campaign_id,
        contact_id=contact_id,
        link_id=link.id,
        variant_id=variant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return RedirectResponse(url=destination, status_code=307)


@app.post("/campaigns/{campaign_id}/links")
def create_campaign_link(
    campaign_id: int,
    original_url: str,
    label: str | None = None,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    link = link_rotator.ensure_link_and_variants(
        db=db,
        campaign_id=campaign_id,
        url=original_url,
        label=label,
    )

    return {
        "link_id": link.id,
        "campaign_id": link.campaign_id,
        "label": link.label,
        "original_url": link.original_url,
    }


@app.post("/links/{link_id}/variants")
def add_link_variant(
    link_id: int,
    payload: LinkVariantCreate,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    variant = LinkVariant(
        link_id=link.id,
        url=payload.url,
        weight=payload.weight,
        is_active=payload.is_active,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    return {
        "variant_id": variant.id,
        "link_id": variant.link_id,
        "url": variant.url,
        "weight": variant.weight,
        "is_active": variant.is_active,
    }


@app.get("/campaigns/{campaign_id}/clicks")
def get_campaign_clicks(
    campaign_id: int,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    links = db.query(Link).filter(Link.campaign_id == campaign_id).all()
    results = []

    for link in links:
        total_clicks = (
            db.query(ClickEvent)
            .filter(ClickEvent.link_id == link.id)
            .count()
        )

        variants = (
            db.query(LinkVariant)
            .filter(LinkVariant.link_id == link.id)
            .all()
        )

        variant_stats = []
        for variant in variants:
            clicks = (
                db.query(ClickEvent)
                .filter(ClickEvent.variant_id == variant.id)
                .count()
            )
            variant_stats.append(
                {
                    "variant_id": variant.id,
                    "url": variant.url,
                    "weight": variant.weight,
                    "is_active": variant.is_active,
                    "clicks": clicks,
                }
            )

        results.append(
            {
                "link_id": link.id,
                "label": link.label,
                "original_url": link.original_url,
                "total_clicks": total_clicks,
                "variants": variant_stats,
            }
        )

    return {
        "campaign_id": campaign_id,
        "links": results,
    }










