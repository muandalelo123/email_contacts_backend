




from sqlalchemy.orm import Session

from .models import (
    Campaign,
    Contact,
    ContactSegment,
    Segment,
    SendJob,
    SendJobState,
    Unsubscribe,
)


def create_send_jobs_for_campaign(
    db: Session,
    campaign_id: int,
    sender_code: str,
    segment_code: str,
) -> int:
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id)
        .first()
    )

    if not campaign:
        raise ValueError("Campaign not found")

    segment = (
        db.query(Segment)
        .filter(Segment.code == segment_code)
        .first()
    )

    if not segment:
        raise ValueError(f"Segment not found: {segment_code}")

    unsubscribed_emails = {
        row.email.strip().lower()
        for row in db.query(Unsubscribe).all()
        if row.email
    }

    contacts = (
        db.query(Contact)
        .join(
            ContactSegment,
            ContactSegment.contact_id == Contact.id,
        )
        .filter(
            ContactSegment.segment_id == segment.id
        )
        .order_by(Contact.id.asc())
        .all()
    )

    count = 0

    for contact in contacts:
        email = contact.email.strip().lower()

        if email in unsubscribed_emails:
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

    db.commit()

    return count



