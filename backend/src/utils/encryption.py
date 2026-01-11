"""
Encryption Utilities
=====================

Gère le chiffrement et le déchiffrement des données sensibles (clés API BYOK).
Utilise l'algorithme Fernet (AES-128 en mode CBC avec HMAC-SHA256).
"""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Exception pour les erreurs de chiffrement/déchiffrement."""

    pass


class MissingEncryptionKeyError(EncryptionError):
    """Clé de chiffrement manquante dans les variables d'environnement."""

    pass


def get_encryption_key() -> bytes:
    """
    Récupère la clé de chiffrement depuis les variables d'environnement.

    Raises:
        MissingEncryptionKeyError: Si ENCRYPTION_KEY n'est pas définie.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise MissingEncryptionKeyError(
            "ENCRYPTION_KEY is required. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return key.encode()


def encrypt_value(value: str) -> str:
    """
    Chiffre une chaîne de caractères.

    Args:
        value: Valeur en clair.

    Returns:
        Valeur chiffrée en base64 (string).

    Raises:
        EncryptionError: En cas d'erreur de chiffrement.
    """
    if not value:
        return ""

    try:
        f = Fernet(get_encryption_key())
        return f.encrypt(value.encode()).decode()
    except MissingEncryptionKeyError:
        raise
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise EncryptionError(f"Failed to encrypt value: {e}") from e


def decrypt_value(encrypted_value: str) -> str:
    """
    Déchiffre une valeur.

    Args:
        encrypted_value: Valeur chiffrée en base64.

    Returns:
        Valeur en clair.

    Raises:
        EncryptionError: En cas d'erreur de déchiffrement (clé invalide, données corrompues).
    """
    if not encrypted_value:
        return ""

    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted_value.encode()).decode()
    except MissingEncryptionKeyError:
        raise
    except InvalidToken as e:
        logger.error("Decryption failed: Invalid token or corrupted data")
        raise EncryptionError("Data integrity check failed during decryption") from e
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise EncryptionError(f"Failed to decrypt value: {e}") from e
