
# app/funnels_service.py

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .db import SessionLocal
from .jobs import process_send_job, queue
from .models import (
    Funnel,
    FunnelRun,
    FunnelStep,
    FunnelStepRun,
    LeadSubmission,
    SendJob,
    SendJobState,
)


FUNNEL_JOB_PREFIX = "funnelstep_"


def _build_funnel_job_id(step_run_id: int) -> str:
    return f"{FUNNEL_JOB_PREFIX}{step_run_id}"


def find_active_funnel(
    db: Session,
    category: str | None,
) -> Funnel | None:
    """
    Retourne le Funnel actif correspondant à la catégorie du lead.

    Pour l'instant, si plusieurs Funnels actifs existent pour la même
    catégorie, le plus récent est utilisé.
    """
    if not category:
        return None

    normalized_category = category.strip()

    if not normalized_category:
        return None

    return (
        db.query(Funnel)
        .filter(
            Funnel.category == normalized_category,
            Funnel.is_active.is_(True),
        )
        .order_by(Funnel.id.desc())
        .first()
    )


def create_and_schedule_funnel_run(
    db: Session,
    *,
    submission: LeadSubmission,
) -> FunnelRun | None:
    """
    Déclenche un Funnel à partir d'une LeadSubmission.

    Étapes:
    1. trouve le Funnel actif de la catégorie;
    2. évite de créer deux FunnelRun pour la même submission;
    3. crée FunnelRun;
    4. crée un FunnelStepRun pour chaque step actif;
    5. planifie chaque step via RQ.
    """
    funnel = find_active_funnel(db, submission.category)

    if funnel is None:
        return None

    existing_run = (
        db.query(FunnelRun)
        .filter(
            FunnelRun.funnel_id == funnel.id,
            FunnelRun.submission_id == submission.id,
        )
        .first()
    )

    if existing_run is not None:
        return existing_run

    run = FunnelRun(
        funnel_id=funnel.id,
        contact_id=submission.contact_id,
        submission_id=submission.id,
        status="scheduled",
        started_at=datetime.utcnow(),
    )

    db.add(run)
    db.flush()

    steps = (
        db.query(FunnelStep)
        .filter(
            FunnelStep.funnel_id == funnel.id,
            FunnelStep.is_active.is_(True),
        )
        .order_by(FunnelStep.step_order.asc())
        .all()
    )

    now = datetime.utcnow()

    step_runs: list[FunnelStepRun] = []

    for step in steps:
        scheduled_at = now + timedelta(
            minutes=max(step.delay_minutes or 0, 0)
        )

        step_run = FunnelStepRun(
            funnel_run_id=run.id,
            funnel_step_id=step.id,
            status="scheduled",
            scheduled_at=scheduled_at,
        )

        db.add(step_run)
        db.flush()

        step_runs.append(step_run)

    db.commit()
    db.refresh(run)

    # Planifier seulement après commit afin que les workers puissent
    # relire FunnelRun/FunnelStepRun depuis PostgreSQL.
    for step_run in step_runs:
        step = (
            db.query(FunnelStep)
            .filter(FunnelStep.id == step_run.funnel_step_id)
            .first()
        )

        if step is None:
            continue

        delay_minutes = max(step.delay_minutes or 0, 0)

        if delay_minutes == 0:
            queue.enqueue(
                process_funnel_step_run,
                step_run.id,
                job_id=_build_funnel_job_id(step_run.id),
            )
        else:
            queue.enqueue_in(
                timedelta(minutes=delay_minutes),
                process_funnel_step_run,
                step_run.id,
                job_id=_build_funnel_job_id(step_run.id),
            )

    return run


def process_funnel_step_run(step_run_id: int) -> None:
    """
    Fonction exécutée par le worker RQ.

    Elle:
    - charge le FunnelStepRun;
    - crée un SendJob;
    - réutilise le moteur d'envoi existant;
    - récupère le provider réellement utilisé;
    - met à jour FunnelStepRun;
    - met éventuellement FunnelRun à completed.
    """
    db: Session = SessionLocal()

    try:
        step_run = (
            db.query(FunnelStepRun)
            .filter(FunnelStepRun.id == step_run_id)
            .first()
        )

        if step_run is None:
            print(
                f"[FUNNEL] step_run_id={step_run_id} not found"
            )
            return

        # Idempotence basique.
        if step_run.status == "sent":
            print(
                f"[FUNNEL] step_run_id={step_run_id} already sent"
            )
            return

        funnel_run = step_run.funnel_run
        funnel_step = step_run.funnel_step

        if funnel_run is None or funnel_step is None:
            step_run.status = "error"
            step_run.executed_at = datetime.utcnow()
            step_run.error_message = "FunnelRun or FunnelStep missing"

            db.add(step_run)
            db.commit()
            return

        if not funnel_step.is_active:
            step_run.status = "skipped"
            step_run.executed_at = datetime.utcnow()

            db.add(step_run)
            db.commit()
            return

        if funnel_step.action_type != "email":
            step_run.status = "error"
            step_run.executed_at = datetime.utcnow()
            step_run.error_message = (
                f"Unsupported action_type: {funnel_step.action_type}"
            )

            db.add(step_run)
            db.commit()
            return

        if funnel_step.campaign_id is None:
            step_run.status = "error"
            step_run.executed_at = datetime.utcnow()
            step_run.error_message = "FunnelStep campaign_id is missing"

            db.add(step_run)
            db.commit()
            return

        step_run.status = "processing"
        db.add(step_run)
        db.commit()

        send_job = SendJob(
            campaign_id=funnel_step.campaign_id,
            contact_id=funnel_run.contact_id,
            state=SendJobState.PENDING,
            sender_code=funnel_run.funnel.preferred_provider,
        )

        db.add(send_job)
        db.commit()
        db.refresh(send_job)

        print(
            f"[FUNNEL] step_run_id={step_run.id}, "
            f"send_job_id={send_job.id}, "
            f"campaign_id={funnel_step.campaign_id}, "
            f"contact_id={funnel_run.contact_id}"
        )

        # Nous sommes déjà dans un worker RQ.
        # On réutilise directement le pipeline SendJob.
        process_send_job(send_job.id)

        db.expire_all()

        refreshed_job = (
            db.query(SendJob)
            .filter(SendJob.id == send_job.id)
            .first()
        )

        refreshed_step_run = (
            db.query(FunnelStepRun)
            .filter(FunnelStepRun.id == step_run_id)
            .first()
        )

        if refreshed_step_run is None:
            return

        refreshed_step_run.executed_at = datetime.utcnow()

        if (
            refreshed_job is not None
            and refreshed_job.state == SendJobState.SENT
        ):
            refreshed_step_run.status = "sent"
            refreshed_step_run.provider_used = refreshed_job.sender_code
            refreshed_step_run.error_message = None
        else:
            refreshed_step_run.status = "error"

            if refreshed_job is not None:
                refreshed_step_run.provider_used = refreshed_job.sender_code
                refreshed_step_run.error_message = (
                    refreshed_job.error_message
                    or "SendJob failed"
                )
            else:
                refreshed_step_run.error_message = "SendJob not found"

        db.add(refreshed_step_run)
        db.commit()

        _refresh_funnel_run_status(
            db,
            funnel_run_id=funnel_run.id,
        )

    except Exception as exc:
        db.rollback()

        try:
            step_run = (
                db.query(FunnelStepRun)
                .filter(FunnelStepRun.id == step_run_id)
                .first()
            )

            if step_run is not None:
                step_run.status = "error"
                step_run.executed_at = datetime.utcnow()
                step_run.error_message = str(exc)

                db.add(step_run)
                db.commit()

        except Exception:
            db.rollback()

        print(
            f"[FUNNEL ERROR] step_run_id={step_run_id}, "
            f"error={exc}"
        )

        raise

    finally:
        db.close()


def _refresh_funnel_run_status(
    db: Session,
    *,
    funnel_run_id: int,
) -> None:
    """
    Recalcule le statut global du FunnelRun.
    """
    run = (
        db.query(FunnelRun)
        .filter(FunnelRun.id == funnel_run_id)
        .first()
    )

    if run is None:
        return

    step_runs = (
        db.query(FunnelStepRun)
        .filter(FunnelStepRun.funnel_run_id == funnel_run_id)
        .all()
    )

    if not step_runs:
        run.status = "completed"
        run.completed_at = datetime.utcnow()

    elif any(step.status == "error" for step in step_runs):
        run.status = "error"

    elif all(
        step.status in {"sent", "skipped"}
        for step in step_runs
    ):
        run.status = "completed"
        run.completed_at = datetime.utcnow()

    elif any(step.status == "processing" for step in step_runs):
        run.status = "running"

    else:
        run.status = "scheduled"

    db.add(run)
    db.commit()




