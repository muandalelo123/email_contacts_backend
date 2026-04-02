

# app/deps.py

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import ApiKey
from .utils.security import hash_secret


def _split_api_key(x_api_key: str) -> tuple[str, str]:
    """
    Parse une clé au format "<prefix>.<secret>".
    Retourne (prefix, secret).

    Erreurs:
      - 401 si header manquant
      - 400 si format invalide
    """
    if not isinstance(x_api_key, str) or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )

    key = x_api_key.strip()

    try:
        key_prefix, raw_secret = key.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key format",
        )

    if not key_prefix or not raw_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key format",
        )

    return key_prefix, raw_secret


def _verify_against_env(x_api_key: str, key_prefix: str):
    """
    Fallback DEV : compare la clé complète à Settings.API_KEY.
    Retourne un objet "compatible" si OK, sinon lève 401.
    """
    settings = get_settings()
    expected = (getattr(settings, "API_KEY", None) or "").strip()

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: API_KEY missing",
        )

    if x_api_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return {
        "id": None,
        "name": "env-api-key",
        "key_prefix": key_prefix,
        "scopes": ["*"],
        "is_active": True,
    }


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Vérifie la clé API envoyée dans le header `x-api-key`.

    Stratégie robuste (dev + prod) :
    1) Valide le format "<prefix>.<secret>"
    2) Tente une validation via DB (table api_keys)
    3) Si DB ne valide pas (prefix absent / secret mismatch / schema KO) -> fallback .env

    Retour :
      - en mode DB: retourne l'objet ApiKey
      - en fallback: retourne un dict minimal compatible
    """
    key_prefix, raw_secret = _split_api_key(x_api_key or "")

    # 1) Tentative DB
    try:
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_prefix == key_prefix, ApiKey.is_active == True)  # noqa: E712
            .first()
        )

        # Si pas trouvé -> DEV fallback possible
        if not api_key:
            return _verify_against_env(x_api_key or "", key_prefix)

        # Si schema pas prêt -> tombe en exception -> fallback
        secret_hash = getattr(api_key, "secret_hash")

        # Secret mismatch -> DEV fallback possible
        if secret_hash != hash_secret(raw_secret):
            return _verify_against_env(x_api_key or "", key_prefix)

        return api_key

    except Exception:
        # DB indisponible / colonne manquante / autre souci -> fallback .env
        return _verify_against_env(x_api_key or "", key_prefix)


