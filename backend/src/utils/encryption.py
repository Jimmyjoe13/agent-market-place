"""
Encryption Utilities
=====================

Gère le chiffrement et le déchiffrement des données sensibles (clés API BYOK).
Utilise l'algorithme Fernet (AES-128 en mode CBC avec HMAC-SHA256).
"""

import os
from cryptography.fernet import Fernet
from src.config.settings import get_settings

def get_encryption_key() -> bytes:
    """
    Récupère la clé de chiffrement depuis les variables d'environnement.
    Génère une clé par défaut si non fournie (pas recommandé pour la prod).
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # En fallback, on utilise une dérivation du SECRET_KEY ou une clé fixe
        # Pour le développement, on peut logger un warning
        return b'7-xL-pQ9U3z_S8m_X5w-v3-H6_Y9_q1_V8_z9_H4_M='
    
    return key.encode()

def encrypt_value(value: str) -> str:
    """
    Chiffre une chaîne de caractères.
    
    Args:
        value: Valeur en clair.
        
    Returns:
        Valeur chiffrée en base64 (string).
    """
    if not value:
        return ""
        
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """
    Déchiffre une valeur.
    
    Args:
        encrypted_value: Valeur chiffrée en base64.
        
    Returns:
        Valeur en clair.
    """
    if not encrypted_value:
        return ""
        
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # Si le déchiffrement échoue (clé différente ou data corrompue)
        return ""
