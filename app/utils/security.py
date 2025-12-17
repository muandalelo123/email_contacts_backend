

# app/utils/security.py

# app/utils/security.py
"""
Utilitaires de sécurité :
- Hashage des secrets (API keys)
- Vérification des formats
- Génération de tokens, si besoin
"""

import hashlib
import hmac
import secrets


# ============================================================
# 🔐 FONCTION DE HASHAGE (SHA-256)
# ============================================================

def hash_secret(secret: str) -> str:
    """
    Hash SHA-256 d'un secret.

    Renvoie un hex-digest de 64 caractères.
    Utilisé pour stocker les API keys côté backend
    sans jamais conserver le secret en clair.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


# ============================================================
# 🔐 COMPARAISON SÉCURISÉE DES HASHES
# ============================================================

def verify_secret(secret: str, expected_hash: str) -> bool:
    """
    Compare un secret en clair avec un hash stocké.

    Utilise hmac.compare_digest pour éviter les attaques
    par timing (time-based side-channel).
    """
    return hmac.compare_digest(hash_secret(secret), expected_hash)


# ============================================================
# 🔐 GÉNÉRATEUR DE TOKEN SÉCURISÉ
# (si un jour tu veux générer autre chose que des API keys)
# ============================================================

def generate_token(length: int = 32) -> str:
    """
    Génère un token hexadécimal sécurisé.
    Peut être utilisé pour :
      - API Keys
      - Tokens de session
      - Codes d'invitations
      - Secrets temporaires
    """
    return secrets.token_hex(length)


# ============================================================
# 🔐 VALIDATEUR OPTIONNEL DE FORMAT "<prefix>.<secret>"
# ============================================================

def split_api_key(full_key: str):
    """
    Valide et découpe une clé API au format :
        <prefix>.<secret>

    Renvoie (prefix, secret)
    Sinon lève ValueError.
    """
    if "." not in full_key:
        raise ValueError("Invalid API key format: missing dot separator")

    prefix, secret = full_key.split(".", 1)

    if not prefix or not secret:
        raise ValueError("Invalid API key format")

    return prefix, secret


