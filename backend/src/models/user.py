"""
User / Profile Model
=====================

Modèles Pydantic pour la gestion des profils utilisateurs.

Ce module définit les structures de données pour :
- Création et mise à jour de profils
- Profil utilisateur avec subscription
- Validation OAuth

Architecture v2:
- La table s'appelle désormais `profiles` et est liée à `auth.users`
- Création automatique par trigger lors de l'inscription
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """Rôles utilisateur disponibles."""
    
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class OAuthProvider(str, Enum):
    """Providers OAuth supportés."""
    
    GOOGLE = "google"
    GITHUB = "github"
    EMAIL = "email"
    SYSTEM = "system"


class ProfileCreate(BaseModel):
    """
    Schéma pour la création d'un profil via OAuth.
    
    Note: En v2, les profils sont créés automatiquement par trigger
    lors de l'inscription via auth.users. Ce schéma est utilisé
    principalement pour les mises à jour initiales.
    """
    
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None)
    provider: OAuthProvider = Field(default=OAuthProvider.EMAIL)
    provider_id: str | None = Field(default=None)


class ProfileUpdate(BaseModel):
    """Schéma pour la mise à jour d'un profil."""
    
    name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None
    provider_keys: dict[str, str] | None = None


class ProfileInfo(BaseModel):
    """
    Informations profil (sans données sensibles).
    
    Utilisé pour les réponses API.
    """
    
    id: UUID = Field(..., description="Identifiant unique (= auth.users.id)")
    email: EmailStr = Field(..., description="Email")
    name: str | None = Field(default=None, description="Nom d'affichage")
    avatar_url: str | None = Field(default=None, description="Photo de profil")
    provider: str = Field(..., description="Provider OAuth")
    role: UserRole = Field(default=UserRole.USER, description="Rôle")
    email_verified: bool = Field(default=False, description="Email vérifié")
    created_at: datetime = Field(..., description="Date de création")
    last_login_at: datetime | None = Field(default=None, description="Dernière connexion")
    
    # BYOK summary
    provider_keys_summary: dict[str, bool] = Field(
        default_factory=dict,
        description="Résumé des clés BYOK configurées (provider: bool)",
    )
    
    model_config = {"from_attributes": True}


class ProfileWithSubscription(ProfileInfo):
    """
    Profil avec informations d'abonnement.
    
    Utilisé pour le dashboard complet.
    """
    
    plan_slug: str = Field(default="free", description="Plan actif")
    plan_name: str = Field(default="Free", description="Nom du plan")
    subscription_status: str = Field(default="active", description="Statut abonnement")
    billing_period: str = Field(default="monthly", description="Période facturation")
    current_period_end: datetime | None = Field(default=None, description="Fin période")
    
    # Usage du mois
    requests_used: int = Field(default=0, description="Requêtes utilisées")
    requests_limit: int = Field(default=100, description="Limite requêtes")
    documents_used: int = Field(default=0, description="Documents créés")
    documents_limit: int = Field(default=10, description="Limite documents")
    api_keys_used: int = Field(default=0, description="Clés API créées")
    api_keys_limit: int = Field(default=1, description="Limite clés")
    agents_used: int = Field(default=0, description="Agents créés")
    agents_limit: int = Field(default=1, description="Limite agents")


class OAuthCallback(BaseModel):
    """
    Données reçues du callback OAuth.
    
    NextAuth.js envoie ces données après authentification.
    """
    
    code: str = Field(..., description="Code d'autorisation OAuth")
    state: str | None = Field(default=None, description="State pour CSRF")
    provider: OAuthProvider = Field(..., description="Provider OAuth")


class OAuthTokenResponse(BaseModel):
    """Réponse après échange du code OAuth."""
    
    access_token: str = Field(..., description="Token d'accès")
    token_type: str = Field(default="Bearer", description="Type de token")
    expires_in: int = Field(..., description="Expiration en secondes")
    refresh_token: str | None = Field(default=None, description="Token de refresh")
    user: ProfileInfo = Field(..., description="Informations utilisateur")


class SessionInfo(BaseModel):
    """Informations de session utilisateur."""
    
    user_id: UUID = Field(..., description="ID utilisateur")
    email: str = Field(..., description="Email")
    name: str | None = Field(default=None, description="Nom")
    avatar_url: str | None = Field(default=None, description="Avatar")
    role: UserRole = Field(default=UserRole.USER, description="Rôle")
    plan_slug: str = Field(default="free", description="Plan actif")
    expires_at: datetime = Field(..., description="Expiration session")


# ==========================================
# Backward Compatibility Aliases
# Ces alias sont conservés pour ne pas casser le code existant
# ==========================================

# UserCreate est un alias de ProfileCreate
UserCreate = ProfileCreate

# UserUpdate est un alias de ProfileUpdate  
UserUpdate = ProfileUpdate

# UserInfo est un alias de ProfileInfo
UserInfo = ProfileInfo

# UserWithSubscription est un alias de ProfileWithSubscription
UserWithSubscription = ProfileWithSubscription
