"""
Agent Model
============

Modèles Pydantic pour la configuration des agents IA.

Ce module définit les structures de données pour :
- Création et configuration des agents
- Liaison avec api_keys
- Paramètres LLM et RAG
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """
    Schéma pour la création d'un nouvel agent.

    Un agent représente une configuration IA avec :
    - Un modèle LLM spécifique
    - Un prompt système personnalisé
    - Des paramètres RAG
    - Des limites de budget
    """

    name: str = Field(
        ...,
        description="Nom de l'agent",
        min_length=2,
        max_length=100,
        examples=["Assistant Support", "Expert Technique"],
    )
    description: str | None = Field(
        default=None,
        description="Description de l'agent",
        max_length=500,
    )
    model_id: str = Field(
        default="mistral-large-latest",
        description="Identifiant du modèle LLM",
        examples=["mistral-large-latest", "gpt-4o", "deepseek-chat"],
    )
    system_prompt: str | None = Field(
        default=None,
        description="Prompt système personnalisé",
        max_length=10000,
    )
    temperature: float = Field(
        default=0.7,
        description="Température du modèle (0-2)",
        ge=0,
        le=2,
    )
    rag_enabled: bool = Field(
        default=True,
        description="Active la recherche dans les documents",
    )
    max_monthly_tokens: int = Field(
        default=0,
        description="Limite de tokens par mois (0 = illimité)",
        ge=0,
    )
    max_daily_requests: int = Field(
        default=0,
        description="Limite de requêtes par jour (0 = illimité)",
        ge=0,
    )


class AgentUpdate(BaseModel):
    """Mise à jour partielle d'un agent."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    model_id: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    rag_enabled: bool | None = None
    max_monthly_tokens: int | None = Field(default=None, ge=0)
    max_daily_requests: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class AgentInfo(BaseModel):
    """
    Informations sur un agent (pour les réponses API).
    """

    id: UUID = Field(..., description="Identifiant unique")
    user_id: UUID = Field(..., description="Propriétaire")
    name: str = Field(..., description="Nom de l'agent")
    description: str | None = Field(default=None)

    # Configuration LLM
    model_id: str = Field(..., description="Modèle LLM")
    system_prompt: str | None = Field(default=None)
    temperature: float = Field(default=0.7)
    rag_enabled: bool = Field(default=True)

    # Budget
    max_monthly_tokens: int = Field(default=0)
    max_daily_requests: int = Field(default=0)
    tokens_used_this_month: int = Field(default=0)
    requests_today: int = Field(default=0)

    # Statut
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(...)
    updated_at: datetime | None = Field(default=None)

    model_config = {"from_attributes": True}


class AgentWithStats(AgentInfo):
    """
    Agent avec statistiques d'utilisation.
    """

    api_keys_count: int = Field(default=0, description="Nombre de clés API")
    documents_count: int = Field(default=0, description="Nombre de documents")
    conversations_count: int = Field(default=0, description="Conversations (30j)")


class AgentConfig(BaseModel):
    """
    Configuration de l'agent pour validation de clé API.

    Utilisé lors de la validation d'une clé pour récupérer
    les paramètres de l'agent associé.
    """

    agent_id: UUID = Field(..., description="ID de l'agent")
    model_id: str = Field(default="mistral-large-latest")
    system_prompt: str | None = Field(default=None)
    temperature: float = Field(default=0.7)
    rag_enabled: bool = Field(default=True)
    agent_name: str | None = Field(default=None)


class AgentListResponse(BaseModel):
    """Réponse paginée pour la liste des agents."""

    agents: list[AgentInfo] = Field(..., description="Liste des agents")
    total: int = Field(..., description="Nombre total")
