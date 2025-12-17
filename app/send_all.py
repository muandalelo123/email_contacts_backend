from sqlalchemy.orm import Session

from .models import Campaign, Contact, SendJob, SendJobState


def create_send_jobs_for_campaign(db: Session, campaign_id: int, sender_code: str) -> int:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise ValueError("Campaign not found")

    contacts = db.query(Contact).all()
    count = 0
    for contact in contacts:
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
