"""
Conversation Models
====================

Modèles Pydantic pour l'historique des conversations et le feedback loop.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FlagType(str, Enum):
    """Types de flags pour le feedback."""
    
    EXCELLENT = "excellent"
    NEEDS_IMPROVEMENT = "needs_improvement"
    INCORRECT = "incorrect"
    MISSING_CONTEXT = "missing_context"
    TO_VECTORIZE = "to_vectorize"


class FlagStatus(str, Enum):
    """Statut de traitement d'un flag."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class ContextSource(BaseModel):
    """
    Source de contexte utilisée pour générer une réponse.
    
    Attributes:
        source_type: Type de source (vector_store, perplexity, etc.).
        document_id: ID du document si applicable.
        content_preview: Aperçu du contenu utilisé.
        similarity_score: Score de similarité si applicable.
    """
    
    source_type: str = Field(..., description="Type de source de contexte")
    document_id: UUID | None = Field(default=None, description="ID du document source")
    content_preview: str = Field(
        default="",
        description="Aperçu du contenu (tronqué)",
        max_length=500,
    )
    similarity_score: float | None = Field(
        default=None,
        description="Score de similarité",
        ge=0.0,
        le=1.0,
    )
    url: str | None = Field(default=None, description="URL source si applicable")


class ConversationMetadata(BaseModel):
    """
    Métadonnées d'une conversation.
    
    Attributes:
        model_used: Modèle LLM utilisé.
        tokens_input: Nombre de tokens en entrée.
        tokens_output: Nombre de tokens en sortie.
        response_time_ms: Temps de réponse en millisecondes.
        perplexity_used: Si Perplexity a été utilisé.
    """
    
    model_used: str = Field(default="", description="Modèle LLM utilisé")
    tokens_input: int = Field(default=0, ge=0, description="Tokens en entrée")
    tokens_output: int = Field(default=0, ge=0, description="Tokens en sortie")
    response_time_ms: int = Field(default=0, ge=0, description="Temps de réponse (ms)")
    perplexity_used: bool = Field(default=False, description="Perplexity utilisé")
    vector_results_count: int = Field(default=0, ge=0, description="Nombre de résultats vectoriels")


class ConversationCreate(BaseModel):
    """
    Schéma pour créer une nouvelle conversation.
    
    Attributes:
        session_id: Identifiant de la session.
        user_query: Question de l'utilisateur.
        ai_response: Réponse générée par l'IA.
        context_sources: Sources de contexte utilisées.
        metadata: Métadonnées de la conversation.
    """
    
    session_id: str = Field(
        ...,
        description="Identifiant de la session",
        min_length=1,
        max_length=100,
    )
    user_query: str = Field(
        ...,
        description="Question de l'utilisateur",
        min_length=1,
    )
    ai_response: str = Field(
        ...,
        description="Réponse de l'IA",
        min_length=1,
    )
    context_sources: list[ContextSource] = Field(
        default_factory=list,
        description="Sources de contexte utilisées",
    )
    metadata: ConversationMetadata = Field(
        default_factory=ConversationMetadata,
        description="Métadonnées de la conversation",
    )


class Conversation(ConversationCreate):
    """
    Modèle complet d'une conversation.
    
    Attributes:
        id: Identifiant unique.
        feedback_score: Score de feedback (1-5).
        feedback_comment: Commentaire de feedback.
        flagged_for_training: Marqué pour ré-injection.
        training_processed_at: Date de traitement pour training.
        created_at: Date de création.
    """
    
    id: UUID = Field(..., description="Identifiant unique")
    feedback_score: int | None = Field(
        default=None,
        description="Score de feedback (1-5)",
        ge=1,
        le=5,
    )
    feedback_comment: str | None = Field(
        default=None,
        description="Commentaire de feedback",
    )
    flagged_for_training: bool = Field(
        default=False,
        description="Marqué pour ré-injection dans le Vector Store",
    )
    training_processed_at: datetime | None = Field(
        default=None,
        description="Date de traitement pour training",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date de création",
    )
    
    model_config = {"from_attributes": True}


class FeedbackFlag(BaseModel):
    """
    Flag de feedback pour amélioration continue.
    
    Attributes:
        id: Identifiant unique du flag.
        conversation_id: Référence à la conversation.
        flag_type: Type de flag.
        notes: Notes additionnelles.
        flagged_by: Utilisateur ayant créé le flag.
        status: Statut de traitement.
        created_at: Date de création.
        processed_at: Date de traitement.
    """
    
    id: UUID = Field(..., description="Identifiant unique")
    conversation_id: UUID = Field(..., description="ID de la conversation")
    flag_type: FlagType = Field(..., description="Type de flag")
    notes: str | None = Field(default=None, description="Notes additionnelles")
    flagged_by: str = Field(default="system", description="Créateur du flag")
    status: FlagStatus = Field(default=FlagStatus.PENDING, description="Statut")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = Field(default=None)
    
    model_config = {"from_attributes": True}


class ConversationAnalytics(BaseModel):
    """
    Statistiques sur les conversations.
    
    Attributes:
        total_conversations: Nombre total de conversations.
        avg_feedback_score: Score moyen de feedback.
        flagged_count: Nombre de conversations flaggées.
        feedback_distribution: Distribution des scores.
        daily_counts: Nombre par jour.
    """
    
    total_conversations: int = Field(default=0, ge=0)
    avg_feedback_score: float | None = Field(default=None, ge=1.0, le=5.0)
    flagged_count: int = Field(default=0, ge=0)
    feedback_distribution: dict[str, int] = Field(default_factory=dict)
    daily_counts: dict[str, int] = Field(default_factory=dict)
    
    @field_validator("feedback_distribution", "daily_counts", mode="before")
    @classmethod
    def convert_none_to_dict(cls, v: Any) -> dict:
        """Convertit None en dictionnaire vide."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class FeedbackCreate(BaseModel):
    """
    Schéma pour soumettre un feedback.
    
    Attributes:
        conversation_id: ID de la conversation.
        score: Score de 1 à 5.
        comment: Commentaire optionnel.
        flag_for_training: Marquer pour ré-injection.
    """
    
    conversation_id: UUID = Field(..., description="ID de la conversation")
    score: int = Field(..., ge=1, le=5, description="Score de feedback (1-5)")
    comment: str | None = Field(default=None, description="Commentaire optionnel")
    flag_for_training: bool = Field(
        default=False,
        description="Marquer pour ré-injection dans le Vector Store",
    )
    flag_type: FlagType | None = Field(
        default=None,
        description="Type de flag si flagged",
    )
    
    @field_validator("flag_type")
    @classmethod
    def validate_flag_type(cls, v: FlagType | None, info: Any) -> FlagType | None:
        """Valide que flag_type est fourni si flag_for_training est True."""
        if info.data.get("flag_for_training") and v is None:
            return FlagType.TO_VECTORIZE
        return v
