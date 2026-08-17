
# app/routers/funnels.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import verify_api_key

from ..models import Campaign, Funnel, FunnelStep

from ..schemas import (
    FunnelCreate,
    FunnelRead,
    FunnelStepCreate,
    FunnelStepRead,
    FunnelUpdate,
)


router = APIRouter(
    prefix="/funnels",
    tags=["funnels"],
    dependencies=[Depends(verify_api_key)],
)


# ============================================================
# FUNNELS
# ============================================================


@router.post("", response_model=FunnelRead, status_code=status.HTTP_201_CREATED)
def create_funnel(
    payload: FunnelCreate,
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    category = payload.category.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Funnel name is required",
        )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Funnel category is required",
        )

    funnel = Funnel(
        name=name,
        category=category,
        preferred_provider=payload.preferred_provider,
        is_active=payload.is_active,
    )

    db.add(funnel)
    db.commit()
    db.refresh(funnel)

    return funnel


@router.get("", response_model=List[FunnelRead])
def list_funnels(
    db: Session = Depends(get_db),
):
    return (
        db.query(Funnel)
        .order_by(Funnel.created_at.desc(), Funnel.id.desc())
        .all()
    )


@router.get("/{funnel_id}", response_model=FunnelRead)
def get_funnel(
    funnel_id: int,
    db: Session = Depends(get_db),
):
    funnel = (
        db.query(Funnel)
        .filter(Funnel.id == funnel_id)
        .first()
    )

    if funnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    return funnel


@router.put("/{funnel_id}", response_model=FunnelRead)
def update_funnel(
    funnel_id: int,
    payload: FunnelUpdate,
    db: Session = Depends(get_db),
):
    funnel = (
        db.query(Funnel)
        .filter(Funnel.id == funnel_id)
        .first()
    )

    if funnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funnel name cannot be empty",
            )

    if "category" in updates:
        updates["category"] = updates["category"].strip()
        if not updates["category"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funnel category cannot be empty",
            )

    for field, value in updates.items():
        setattr(funnel, field, value)

    db.add(funnel)
    db.commit()
    db.refresh(funnel)

    return funnel


# ============================================================
# FUNNEL STEPS
# ============================================================

@router.post(
    "/{funnel_id}/steps",
    response_model=FunnelStepRead,
    status_code=status.HTTP_201_CREATED,
)
def create_funnel_step(
    funnel_id: int,
    payload: FunnelStepCreate,
    db: Session = Depends(get_db),
):
    funnel = (
        db.query(Funnel)
        .filter(Funnel.id == funnel_id)
        .first()
    )

    if funnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    if payload.step_order < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step_order must be >= 1",
        )

    if payload.delay_minutes < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="delay_minutes must be >= 0",
        )

    existing = (
        db.query(FunnelStep)
        .filter(
            FunnelStep.funnel_id == funnel_id,
            FunnelStep.step_order == payload.step_order,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step order {payload.step_order} already exists",
        )

    if payload.action_type != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only email action_type is supported for now",
        )

    if not payload.subject or not payload.subject.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email subject is required",
        )

    if not payload.html or not payload.html.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email HTML is required",
        )

    try:
        campaign = Campaign(
            subject=payload.subject.strip(),
            html=payload.html,
            from_code=funnel.preferred_provider,
        )

        db.add(campaign)
        db.flush()

        step = FunnelStep(
            funnel_id=funnel_id,
            campaign_id=campaign.id,
            step_order=payload.step_order,
            delay_minutes=payload.delay_minutes,
            action_type=payload.action_type,
            subject=payload.subject.strip(),
            html=payload.html,
            is_active=payload.is_active,
        )

        db.add(step)
        db.commit()
        db.refresh(step)

        return step

    except Exception:
        db.rollback()
        raise
@router.get(
    "/{funnel_id}/steps",
    response_model=List[FunnelStepRead],
)
def list_funnel_steps(
    funnel_id: int,
    db: Session = Depends(get_db),
):
    funnel_exists = (
        db.query(Funnel.id)
        .filter(Funnel.id == funnel_id)
        .first()
    )

    if funnel_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel not found",
        )

    return (
        db.query(FunnelStep)
        .filter(FunnelStep.funnel_id == funnel_id)
        .order_by(FunnelStep.step_order.asc())
        .all()
    )


@router.delete(
    "/{funnel_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_funnel_step(
    funnel_id: int,
    step_id: int,
    db: Session = Depends(get_db),
):
    step = (
        db.query(FunnelStep)
        .filter(
            FunnelStep.id == step_id,
            FunnelStep.funnel_id == funnel_id,
        )
        .first()
    )

    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel step not found",
        )

    db.delete(step)
    db.commit()

    return None



