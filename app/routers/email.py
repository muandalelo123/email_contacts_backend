
# app/routers/emails.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_api_key
from ..schemas import EmailPayload  # à adapter

router = APIRouter(prefix="/emails", tags=["Emails"])

@router.post("/send")
def send_email(
    payload: EmailPayload,
    db: Session = Depends(get_db),
    api_key=Depends(verify_api_key),
):
    # ta logique d'envoi d'email
    return {"detail": "Email envoyé"}


