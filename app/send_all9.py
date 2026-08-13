from sqlalchemy.orm import Session

from .models import Campaign, Contact, SendJob, SendJobState, Unsubscribe


def create_send_jobs_for_campaign(db: Session, campaign_id: int, sender_code: str) -> int:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise ValueError("Campaign not found")

    unsubscribed_emails = {
        row.email
        for row in db.query(Unsubscribe).all()
    }

    contacts = (
        db.query(Contact)
        .order_by(Contact.id.asc())
        .all()
    )

    count = 0
    for contact in contacts:
        if contact.email in unsubscribed_emails:
            continue

        existing_job = (
            db.query(SendJob)
            .filter(
                SendJob.campaign_id == campaign.id,
                SendJob.contact_id == contact.id,
            )
            .first()
        )
        if existing_job:
            continue

        job = SendJob(
            campaign_id=campaign.id,
            contact_id=contact.id,
            state=SendJobState.PENDING,
            sender_code=sender_code,
        )
        db.add(job)
        count += 1

        if count % 500 == 0:
            db.flush()

    db.commit()
    return count



