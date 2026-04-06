from __future__ import annotations

from datetime import datetime

from redis import Redis
from rq import Queue
from rq.job import Job
from sqlalchemy.orm import Session

from . import email_router
from . import link_rotator
from .config import get_settings
from .db import SessionLocal
from .models import Campaign, Contact, SendJob, SendJobState, Unsubscribe

settings = get_settings()

redis_conn = Redis.from_url(str(settings.REDIS_URL))
queue = Queue("default", connection=redis_conn)

JOB_ID_PREFIX = "sendjob_"


def _build_job_id(send_job_id: int) -> str:
    return f"{JOB_ID_PREFIX}{send_job_id}"


def enqueue_send_job(send_job_id: int) -> None:
    # Temporairement exécuté en direct pour simplifier les tests
    # queue.enqueue(
    #     process_send_job,
    #     send_job_id,
    #     job_id=_build_job_id(send_job_id),
    # )
    process_send_job(send_job_id)


def process_send_job(send_job_id: int) -> None:
    db: Session = SessionLocal()

    try:
        job: SendJob | None = (
            db.query(SendJob)
            .filter(SendJob.id == send_job_id)
            .first()
        )

        if job is None:
            print(f"[JOB] send_job_id={send_job_id} not found")
            return

        if job.state == SendJobState.SENT:
            print(f"[JOB] send_job_id={send_job_id} already sent")
            return

        campaign: Campaign | None = job.campaign
        contact: Contact | None = job.contact

        if campaign is None or contact is None:
            job.state = SendJobState.ERROR
            job.error_at = datetime.utcnow()
            job.error_message = "Campaign or contact missing"
            db.add(job)
            db.commit()
            print(f"[JOB ERROR] send_job_id={send_job_id} campaign/contact missing")
            return

        print(
            f"[JOB] id={job.id}, "
            f"job.sender_code={job.sender_code}, "
            f"campaign.from_code={campaign.from_code}, "
            f"to={contact.email}"
        )

        unsubscribed = (
            db.query(Unsubscribe)
            .filter(Unsubscribe.email == contact.email)
            .first()
        )
        if unsubscribed:
            job.state = SendJobState.ERROR
            job.error_at = datetime.utcnow()
            job.error_message = "Contact unsubscribed"
            db.add(job)
            db.commit()
            print(f"[JOB ERROR] send_job_id={send_job_id} contact unsubscribed")
            return

        try:
            base_tracking_url = (
                getattr(settings, "APP_BASE_URL", None)
                or "http://localhost:8000"
            )

            tracked_html = link_rotator.replace_links_for_contact(
                db=db,
                campaign=campaign,
                html=campaign.html,
                contact_id=contact.id,
                base_tracking_url=base_tracking_url,
            )

            result = email_router.send_email_with_fallback(
                db=db,
                to=contact.email,
                subject=campaign.subject,
                html=tracked_html,
                sender_code=job.sender_code,
            )

            job.state = SendJobState.SENT
            job.sent_at = datetime.utcnow()
            job.error_at = None
            job.error_message = None
            job.sender_code = result.get("provider", job.sender_code)

            print(
                f"[JOB SUCCESS] send_job_id={send_job_id}, "
                f"provider={job.sender_code}, "
                f"sent_at={job.sent_at}"
            )

        except Exception as exc:  # noqa: BLE001
            job.state = SendJobState.ERROR
            job.error_at = datetime.utcnow()
            job.error_message = str(exc)

            print(
                f"[JOB ERROR] send_job_id={send_job_id}, "
                f"error={exc}"
            )

        db.add(job)
        db.commit()

    finally:
        db.close()


def fetch_rq_exc_info(send_job_id: int) -> str | None:
    try:
        rq_job = Job.fetch(_build_job_id(send_job_id), connection=redis_conn)
    except Exception:  # noqa: BLE001
        return None

    return rq_job.exc_info




