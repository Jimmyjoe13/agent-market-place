"""
API Schemas
============

Schémas Pydantic pour les requêtes et réponses de l'API.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ===== Query Schemas =====


class QueryRequest(BaseModel):
    """Requête pour le RAG."""

    question: str = Field(
        ...,
        description="Question à poser au système RAG",
        min_length=1,
        max_length=5000,
    )
    system_prompt: str | None = Field(
        default=None,
        description="Prompt système personnalisé",
    )
    use_web_search: bool | None = Field(
        default=None,
        description="Forcer/désactiver la recherche web",
    )
    use_rag: bool | None = Field(
        default=None,
        description="Forcer l'utilisation du RAG (documents personnels)",
    )
    session_id: str | None = Field(
        default=None,
        description="ID de session existante",
    )
    temperature: float | None = Field(
        default=None,
        description="Température de génération (0.0 à 2.0)",
        ge=0.0,
        le=2.0,
    )
    max_tokens: int | None = Field(
        default=None,
        description="Nombre maximum de tokens à générer",
        ge=1,
        le=8192,
    )
    # Nouveaux champs pour les fonctionnalités avancées
    enable_reflection: bool = Field(
        default=False,
        description="Activer le mode réflexion approfondie (Chain of Thought)",
    )
    stream: bool = Field(
        default=False,
        description="Activer le streaming SSE",
    )
    provider: str | None = Field(
        default=None,
        description="Provider LLM à utiliser (mistral, openai, gemini)",
    )
    model: str | None = Field(
        default=None,
        description="Modèle spécifique à utiliser",
    )


class SourceResponse(BaseModel):
    """Source utilisée dans la réponse."""

    source_type: str
    content_preview: str
    similarity_score: float | None = None
    url: str | None = None


class QueryResponse(BaseModel):
    """Réponse du RAG."""

    answer: str
    sources: list[SourceResponse]
    conversation_id: str | None
    session_id: str
    metadata: dict[str, Any]
    # Nouveaux champs
    thought_process: str | None = Field(
        default=None,
        description="Processus de réflexion (si mode réflexion activé)",
    )
    routing: dict[str, Any] | None = Field(
        default=None,
        description="Informations de routage intelligent",
    )


# ===== Feedback Schemas =====


class FeedbackRequest(BaseModel):
    """Requête de feedback."""

    conversation_id: UUID = Field(
        ...,
        description="ID de la conversation",
    )
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Score de 1 à 5",
    )
    comment: str | None = Field(
        default=None,
        description="Commentaire optionnel",
    )
    flag_for_training: bool = Field(
        default=False,
        description="Marquer pour ré-injection",
    )


class FeedbackResponse(BaseModel):
    """Réponse de feedback."""

    success: bool
    message: str


# ===== Ingestion Schemas =====


class IngestGithubRequest(BaseModel):
    """Requête d'ingestion GitHub."""

    repositories: list[str] = Field(
        ...,
        description="Liste des repos (format: owner/repo)",
        min_length=1,
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Ignorer les doublons",
    )


class IngestTextRequest(BaseModel):
    """Requête d'ingestion de texte."""

    content: str = Field(
        ...,
        description="Contenu textuel à ingérer",
        min_length=10,
    )
    source_id: str = Field(
        ...,
        description="Identifiant de la source",
    )
    title: str | None = Field(
        default=None,
        description="Titre du document",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags pour catégorisation",
    )


class IngestResponse(BaseModel):
    """Réponse d'ingestion."""

    success: bool
    documents_created: int
    documents_skipped: int
    errors: int
    message: str


# ===== Analytics Schemas =====


class AnalyticsResponse(BaseModel):
    """Statistiques du système."""

    total_conversations: int
    avg_feedback_score: float | None
    flagged_count: int
    feedback_distribution: dict[str, int]
    daily_counts: dict[str, int]


# ===== Health Schemas =====


class HealthResponse(BaseModel):
    """État de santé de l'API."""

    status: str
    version: str
    services: dict[str, bool]


# ===== Error Schemas =====


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""

    error: str = Field(..., description="Code d'erreur (ex: INVALID_REQUEST)")
    message: str = Field(..., description="Message d'erreur descriptif")
    details: dict[str, Any] | None = Field(default=None, description="Détails supplémentaires")
