"""
User Model
===========

Modèles Pydantic pour la gestion des utilisateurs OAuth.

Ce module définit les structures de données pour :
- Création et mise à jour d'utilisateurs
- Profil utilisateur avec subscription
- Validation OAuth
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


class UserCreate(BaseModel):
    """
    Schéma pour la création d'un utilisateur via OAuth.
    
    Attributes:
        email: Email de l'utilisateur (identifiant principal).
        name: Nom d'affichage.
        avatar_url: URL de la photo de profil.
        provider: Provider OAuth utilisé.
        provider_id: ID unique du provider.
    """
    
    email: EmailStr = Field(
        ...,
        description="Email de l'utilisateur",
    )
    name: str | None = Field(
        default=None,
        description="Nom d'affichage",
        max_length=255,
    )
    avatar_url: str | None = Field(
        default=None,
        description="URL de la photo de profil",
    )
    provider: OAuthProvider = Field(
        default=OAuthProvider.EMAIL,
        description="Provider OAuth",
    )
    provider_id: str | None = Field(
        default=None,
        description="ID unique du provider",
    )


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""
    
    name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None
    provider_keys: dict[str, str] | None = None


class UserInfo(BaseModel):
    """
    Informations utilisateur (sans données sensibles).
    
    Utilisé pour les réponses API.
    """
    
    id: UUID = Field(..., description="Identifiant unique")
    email: EmailStr = Field(..., description="Email")
    name: str | None = Field(default=None, description="Nom d'affichage")
    avatar_url: str | None = Field(default=None, description="Photo de profil")
    provider: str = Field(..., description="Provider OAuth")
    role: UserRole = Field(default=UserRole.USER, description="Rôle")
    email_verified: bool = Field(default=False, description="Email vérifié")
    created_at: datetime = Field(..., description="Date de création")
    last_login_at: datetime | None = Field(default=None, description="Dernière connexion")
    provider_keys_summary: dict[str, bool] = Field(default_factory=dict, description="Résumé des clés BYOK configurées")
    
    model_config = {"from_attributes": True}


class UserWithSubscription(UserInfo):
    """
    Utilisateur avec informations d'abonnement.
    
    Utilisé pour le profil complet dans le dashboard.
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
    user: UserInfo = Field(..., description="Informations utilisateur")


class SessionInfo(BaseModel):
    """Informations de session utilisateur."""
    
    user_id: UUID = Field(..., description="ID utilisateur")
    email: str = Field(..., description="Email")
    name: str | None = Field(default=None, description="Nom")
    avatar_url: str | None = Field(default=None, description="Avatar")
    role: UserRole = Field(default=UserRole.USER, description="Rôle")
    plan_slug: str = Field(default="free", description="Plan actif")
    expires_at: datetime = Field(..., description="Expiration session")
