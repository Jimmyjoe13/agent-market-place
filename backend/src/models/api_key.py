"""
API Key Models
===============

Modèles Pydantic pour la gestion des clés API d'authentification.

Ce module définit les structures de données pour :
- Création de clés API
- Validation et réponses
- Statistiques d'utilisation

Example:
    >>> from src.models.api_key import ApiKeyCreate, ApiKeyScope
    >>> key = ApiKeyCreate(name="Production App", scopes=[ApiKeyScope.QUERY])
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ApiKeyScope(str, Enum):
    """
    Permissions disponibles pour les clés API.
    
    Attributes:
        QUERY: Permet d'interroger le système RAG.
        INGEST: Permet d'ingérer des documents.
        FEEDBACK: Permet de soumettre des feedbacks.
        ADMIN: Accès complet, incluant la gestion des clés.
    """
    
    QUERY = "query"
    INGEST = "ingest"
    FEEDBACK = "feedback"
    ADMIN = "admin"


class ApiKeyCreate(BaseModel):
    """
    Schéma pour la création d'une nouvelle clé API.
    
    Attributes:
        name: Nom descriptif de la clé (ex: "Production App").
        scopes: Liste des permissions accordées.
        rate_limit_per_minute: Limite de requêtes par minute.
        monthly_quota: Quota mensuel (0 = illimité).
        expires_in_days: Nombre de jours avant expiration (None = jamais).
        metadata: Métadonnées personnalisées.
    
    Example:
        >>> key = ApiKeyCreate(
        ...     name="Mon Application",
        ...     scopes=[ApiKeyScope.QUERY, ApiKeyScope.FEEDBACK],
        ...     rate_limit_per_minute=50
        ... )
    """
    
    name: str = Field(
        ...,
        description="Nom descriptif de la clé API",
        min_length=3,
        max_length=100,
        examples=["Production App", "Test Environment"],
    )
    scopes: list[ApiKeyScope] = Field(
        default=[ApiKeyScope.QUERY],
        description="Permissions accordées à cette clé",
        examples=[[ApiKeyScope.QUERY, ApiKeyScope.FEEDBACK]],
    )
    rate_limit_per_minute: int = Field(
        default=100,
        description="Nombre maximum de requêtes par minute (0 = illimité)",
        ge=0,
        le=10000,
        examples=[100, 500, 0],
    )
    monthly_quota: int = Field(
        default=0,
        description="Quota mensuel de requêtes (0 = illimité)",
        ge=0,
        examples=[10000, 100000, 0],
    )
    expires_in_days: int | None = Field(
        default=None,
        description="Nombre de jours avant expiration (null = jamais)",
        ge=1,
        le=365,
        examples=[30, 90, None],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Métadonnées personnalisées (owner, team, etc.)",
        examples=[{"team": "backend", "environment": "production"}],
    )
    
    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[ApiKeyScope]) -> list[ApiKeyScope]:
        """Valide qu'au moins un scope est fourni."""
        if not v:
            raise ValueError("Au moins un scope doit être spécifié")
        return list(set(v))  # Dédupliquer


class ApiKeyResponse(BaseModel):
    """
    Réponse après création d'une clé API.
    
    ⚠️ IMPORTANT: Le champ `key` n'est retourné qu'une seule fois
    lors de la création. Il doit être sauvegardé immédiatement.
    
    Attributes:
        id: Identifiant unique de la clé.
        name: Nom descriptif.
        key: Clé complète (retournée uniquement à la création).
        prefix: Préfixe visible pour identification.
        scopes: Permissions accordées.
        rate_limit_per_minute: Limite de requêtes.
        expires_at: Date d'expiration.
        created_at: Date de création.
    """
    
    id: UUID = Field(..., description="Identifiant unique de la clé")
    name: str = Field(..., description="Nom descriptif")
    key: str | None = Field(
        default=None,
        description="Clé complète (⚠️ affichée une seule fois)",
        examples=["rag_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"],
    )
    prefix: str = Field(
        ...,
        description="Préfixe visible pour identification",
        examples=["rag_a1b2c3d4"],
    )
    scopes: list[str] = Field(..., description="Permissions accordées")
    rate_limit_per_minute: int = Field(..., description="Limite par minute")
    monthly_quota: int = Field(default=0, description="Quota mensuel")
    expires_at: datetime | None = Field(
        default=None,
        description="Date d'expiration",
    )
    is_active: bool = Field(default=True, description="Clé active")
    created_at: datetime = Field(..., description="Date de création")
    
    model_config = {"from_attributes": True}


class ApiKeyInfo(BaseModel):
    """
    Informations sur une clé API (sans le secret).
    
    Utilisé pour lister les clés existantes.
    """
    
    id: UUID = Field(..., description="Identifiant unique")
    name: str = Field(..., description="Nom descriptif")
    prefix: str = Field(..., description="Préfixe visible")
    scopes: list[str] = Field(..., description="Permissions")
    rate_limit_per_minute: int = Field(..., description="Limite par minute")
    monthly_quota: int = Field(default=0, description="Quota mensuel")
    monthly_usage: int = Field(default=0, description="Usage du mois")
    is_active: bool = Field(..., description="Clé active")
    expires_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime | None = Field(default=None, description="Date de création")
    model_config = {"from_attributes": True}



class ApiKeyValidation(BaseModel):
    """
    Résultat de la validation d'une clé API.
    Contient l'ID de la clé et ses permissions si valide.
    """
    
    is_valid: bool = Field(..., description="La clé est-elle valide")
    id: UUID | None = Field(default=None, description="ID de la clé")
    user_id: UUID | None = Field(default=None, description="ID de l'utilisateur")
    scopes: list[str] = Field(default_factory=list, description="Permissions accordées")
    rate_limit: int = Field(default=100, description="Limite de requêtes par minute")
    rejection_reason: str | None = Field(
        default=None,
        description="Raison du rejet si invalide",
    )


class ApiKeyUsageStats(BaseModel):
    """
    Statistiques d'utilisation d'une clé API.
    
    Attributes:
        total_requests: Nombre total de requêtes.
        avg_response_time: Temps de réponse moyen (ms).
        error_rate: Pourcentage d'erreurs.
        requests_by_endpoint: Répartition par endpoint.
        requests_by_day: Répartition par jour.
    """
    
    total_requests: int = Field(default=0, ge=0)
    avg_response_time: float | None = Field(default=None, ge=0)
    error_rate: float = Field(default=0, ge=0, le=100)
    requests_by_endpoint: dict[str, int] = Field(default_factory=dict)
    requests_by_day: dict[str, int] = Field(default_factory=dict)


class ApiKeyListResponse(BaseModel):
    """Réponse paginée pour la liste des clés."""
    
    keys: list[ApiKeyInfo] = Field(..., description="Liste des clés")
    total: int = Field(..., description="Nombre total de clés")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
