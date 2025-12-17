

# app/deps.py

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import ApiKey

# IMPORTANT :
# On importe _hash_secret SANS importer tout le router pour éviter les circular imports.
# Si besoin, on peut déplacer _hash_secret dans un fichier utils séparé.
from .utils.security import hash_secret  # je t'explique plus bas


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Vérifie la clé API envoyée dans le header `x-api-key`.
    Format attendu : "<key_prefix>.<secret>"
    Exemple : "rk_7fa3c9b4.e2d4f9a3c2..."
    """

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )

    # Format "<prefix>.<secret>"
    try:
        key_prefix, raw_secret = x_api_key.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key format",
        )

    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_prefix == key_prefix, ApiKey.is_active == True)
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key (prefix not found)",
        )

    # Vérification du secret via hash
    if api_key.secret_hash != hash_secret(raw_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key (secret mismatch)",
        )

    return api_key


