
# app/jobs.py

from __future__ import annotations

from datetime import datetime

from redis import Redis
from rq import Queue
from rq.job import Job
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal
from .models import Campaign, Contact, SendJob, SendJobState
from . import email_utils

# Chargement des settings
settings = get_settings()

# Connexion Redis + file RQ
redis_conn = Redis.from_url(str(settings.REDIS_URL))
queue = Queue("default", connection=redis_conn)

# Préfixe commun aux IDs des jobs RQ (sans ":" pour éviter l'erreur RQ)
JOB_ID_PREFIX = "sendjob_"


def _build_job_id(send_job_id: int) -> str:
    """Construit l'identifiant RQ pour un SendJob donné."""
    return f"{JOB_ID_PREFIX}{send_job_id}"


def enqueue_send_job(send_job_id: int) -> None:
    """
    Enfile un job d'envoi pour un SendJob donné.
    L'ID du job RQ est dérivé de l'ID en base pour faciliter le suivi.
    """
    queue.enqueue(
        process_send_job,
        send_job_id,
        job_id=_build_job_id(send_job_id),
    )


def process_send_job(send_job_id: int) -> None:
    """
    Fonction exécutée par le worker RQ.
    Elle ouvre sa propre session DB pour traiter un SendJob.
    """
    db: Session = SessionLocal()
    try:
        job: SendJob | None = (
            db.query(SendJob)
            .filter(SendJob.id == send_job_id)
            .first()
        )

        if job is None:
            # Rien à traiter
            return

        # Si déjà envoyé, ne rien faire
        if job.state == SendJobState.SENT:
            return

        campaign: Campaign = job.campaign
        contact: Contact = job.contact

        try:
            # Envoi de l'email
            email_utils.send_email(
                to=contact.email,
                subject=campaign.subject,
                html=campaign.html,
                sender_code=job.sender_code,
            )
            job.state = SendJobState.SENT
            job.sent_at = datetime.utcnow()
            job.error_at = None
            job.error_message = None
        except Exception as exc:  # noqa: BLE001
            job.state = SendJobState.ERROR
            job.error_at = datetime.utcnow()
            job.error_message = str(exc)

        db.add(job)
        db.commit()
    finally:
        db.close()


def fetch_rq_exc_info(send_job_id: int) -> str | None:
    """
    Récupère le traceback (exc_info) du job RQ associé à un SendJob, s'il existe.
    Retourne None sinon.
    """
    try:
        rq_job = Job.fetch(_build_job_id(send_job_id), connection=redis_conn)
    except Exception:  # noqa: BLE001
        return None

    return rq_job.exc_info


