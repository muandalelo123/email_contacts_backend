

# app/routers/settings_api_keys.py

from datetime import datetime
from secrets import token_hex
from typing import List

import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ApiKey
from ..schemas import ApiKeyRead, ApiKeyCreate

router = APIRouter(
    prefix="/settings/api-keys",
    tags=["Settings - API Keys"],
)


def _scopes_str_to_list(scopes_str: str | None) -> list[str]:
    if not scopes_str:
        return []
    return [s.strip() for s in scopes_str.split(",") if s.strip()]


def _scopes_list_to_str(scopes: list[str] | None) -> str:
    if not scopes:
        return ""
    return ",".join(scopes)


def _hash_secret(secret: str) -> str:
    """
    Hash simple du secret (SHA256).
    En prod, tu peux utiliser une stratégie plus évoluée (pepper, etc).
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


# ============================================================
# LISTE DES CLÉS API
# ============================================================

@router.get("/", response_model=List[ApiKeyRead])
def list_api_keys(db: Session = Depends(get_db)) -> list[ApiKeyRead]:
    """
    Retourne la liste des clés API existantes.
    On ne renvoie jamais le secret complet, uniquement un prefix (key_prefix)
    et les métadonnées. Le champ `secret` restera toujours None ici.
    """
    rows = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()

    result: list[ApiKeyRead] = []
    for row in rows:
        result.append(
            ApiKeyRead(
                id=row.id,
                name=row.name,
                key_prefix=row.key_prefix,
                created_at=row.created_at,
                scopes=_scopes_str_to_list(row.scopes),
                secret=None,  # important : on NE renvoie jamais le secret ici
            )
        )
    return result


# ============================================================
# CRÉATION D'UNE NOUVELLE CLÉ API
# ============================================================

@router.post("/", response_model=ApiKeyRead)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
) -> ApiKeyRead:
    """
    Crée une nouvelle clé API.

    - Génère un prefix pseudo-aléatoire (ex: "rk_7fa3c9b4").
    - Génère un secret long (32 bytes hex).
    - Stocke uniquement le hash du secret en base.
    - Retourne UNE SEULE FOIS la clé complète : "<key_prefix>.<secret>".
    """

    # Génère un prefix pseudo-aléatoire (ex: "rk_7fa3c9b4")
    key_prefix = f"rk_{token_hex(4)}"

    # Génère un secret long (ex: "e2d4f9...") et la clé complète "<prefix>.<secret>"
    raw_secret = token_hex(32)
    full_key = f"{key_prefix}.{raw_secret}"

    secret_hash = _hash_secret(raw_secret)

    api_key = ApiKey(
        name=payload.name,
        key_prefix=key_prefix,
        secret_hash=secret_hash,
        created_at=datetime.utcnow(),
        scopes=_scopes_list_to_str(payload.scopes),
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # On renvoie la clé COMPLÈTE dans `secret` UNIQUEMENT à la création
    return ApiKeyRead(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        scopes=_scopes_str_to_list(api_key.scopes),
        secret=full_key,
    )


# ============================================================
# SUPPRESSION D'UNE CLÉ API
# ============================================================

@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Supprime une clé API par id.
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(api_key)
    db.commit()

    return {"detail": f"API key {key_id} deleted"}



