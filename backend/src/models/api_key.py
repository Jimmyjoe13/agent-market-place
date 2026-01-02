"""
API Key Models
===============

Modèles Pydantic pour la gestion des clés API d'authentification.

Ce module définit les structures de données pour :
- Création de clés API (liées à un agent)
- Validation et réponses
- Statistiques d'utilisation

Architecture v2:
- Une clé API est liée à exactement un agent
- Un agent peut avoir plusieurs clés API
- La configuration LLM est sur l'agent, pas sur la clé
"""

from datetime import datetime
from enum import Enum
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

    Une clé API est liée à un agent existant.
    Si agent_id n'est pas fourni, un agent par défaut sera créé.

    Attributes:
        name: Nom descriptif de la clé.
        agent_id: ID de l'agent à associer (optionnel).
        scopes: Liste des permissions accordées.
        rate_limit_per_minute: Limite de requêtes par minute.
        expires_in_days: Nombre de jours avant expiration.
    """

    name: str = Field(
        ...,
        description="Nom descriptif de la clé API",
        min_length=3,
        max_length=100,
        examples=["Production App", "Test Environment"],
    )
    agent_id: UUID | None = Field(
        default=None,
        description="ID de l'agent à associer (optionnel, crée un agent si non fourni)",
    )
    scopes: list[ApiKeyScope] = Field(
        default=[ApiKeyScope.QUERY],
        description="Permissions accordées à cette clé",
        examples=[[ApiKeyScope.QUERY, ApiKeyScope.FEEDBACK]],
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Nombre maximum de requêtes par minute",
        ge=0,
        le=10000,
        examples=[60, 100, 500],
    )
    expires_in_days: int | None = Field(
        default=None,
        description="Nombre de jours avant expiration (null = jamais)",
        ge=1,
        le=365,
        examples=[30, 90, None],
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[ApiKeyScope]) -> list[ApiKeyScope]:
        """Valide qu'au moins un scope est fourni."""
        if not v:
            raise ValueError("Au moins un scope doit être spécifié")
        return list(set(v))


class ApiKeyResponse(BaseModel):
    """
    Réponse après création d'une clé API.

    ⚠️ IMPORTANT: Le champ `key` n'est retourné qu'une seule fois
    lors de la création. Il doit être sauvegardé immédiatement.
    """

    id: UUID = Field(..., description="Identifiant unique de la clé")
    agent_id: UUID = Field(..., description="Agent associé")
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
    expires_at: datetime | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(...)

    model_config = {"from_attributes": True}


class ApiKeyInfo(BaseModel):
    """
    Informations sur une clé API (sans le secret).

    Utilisé pour lister les clés existantes.
    Inclut les informations de base de l'agent associé.
    """

    id: UUID = Field(..., description="Identifiant unique")
    agent_id: UUID = Field(..., description="Agent associé")
    name: str = Field(..., description="Nom descriptif")
    prefix: str = Field(..., description="Préfixe visible")
    scopes: list[str] = Field(..., description="Permissions")
    rate_limit_per_minute: int = Field(..., description="Limite par minute")
    is_active: bool = Field(...)
    expires_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime | None = Field(default=None)

    # Info agent (chargée séparément)
    agent_name: str | None = Field(default=None, description="Nom de l'agent")
    agent_model_id: str = Field(default="mistral-large-latest", description="Modèle LLM")
    rag_enabled: bool = Field(default=True, description="RAG activé")

    model_config = {"from_attributes": True}


class ApiKeyValidation(BaseModel):
    """
    Résultat de la validation d'une clé API.

    Contient l'ID de la clé, ses permissions, et la configuration
    de l'agent associé si la clé est valide.
    """

    is_valid: bool = Field(..., description="La clé est-elle valide")
    key_id: UUID | None = Field(default=None, description="ID de la clé")
    agent_id: UUID | None = Field(default=None, description="ID de l'agent")
    user_id: UUID | None = Field(default=None, description="ID de l'utilisateur")
    scopes: list[str] = Field(default_factory=list, description="Permissions")
    rate_limit: int = Field(default=60, description="Limite par minute")
    rejection_reason: str | None = Field(default=None)

    # Configuration agent (si valide)
    model_id: str | None = Field(default=None, description="Modèle LLM")
    system_prompt: str | None = Field(default=None, description="Prompt système")
    rag_enabled: bool | None = Field(default=None, description="RAG activé")
    agent_name: str | None = Field(default=None, description="Nom de l'agent")


class ApiKeyUsageStats(BaseModel):
    """
    Statistiques d'utilisation d'une clé API.
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


# Backward compatibility - ancien AgentConfig (déprécié)
class AgentConfig(BaseModel):
    """
    [DEPRECATED] Utilisez src.models.agent.AgentConfig à la place.

    Conservé pour compatibilité avec le code existant.
    """

    model_id: str = Field(default="mistral-large-latest")
    system_prompt: str | None = Field(default=None, max_length=10000)
    rag_enabled: bool = Field(default=True)
    agent_name: str | None = Field(default=None, max_length=100)


class AgentConfigUpdate(BaseModel):
    """[DEPRECATED] Mise à jour via agent_id maintenant."""

    model_id: str | None = None
    system_prompt: str | None = None
    rag_enabled: bool | None = None
    agent_name: str | None = None
