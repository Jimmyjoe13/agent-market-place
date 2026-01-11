"""
RAG Configuration
==================

Dataclasses pour la configuration et les réponses du RAG Engine.
"""

from dataclasses import dataclass, field
from typing import Any

from src.models.conversation import ContextSource
from src.services.orchestrator import RoutingDecision


@dataclass
class RAGResponse:
    """
    Réponse générée par le RAG Engine.

    Attributes:
        answer: Réponse textuelle générée.
        sources: Sources utilisées (vectorielles + web).
        conversation_id: ID de la conversation loggée.
        metadata: Métadonnées de génération.
        thought_process: Processus de réflexion (si mode réflexion activé).
        routing: Décision de routage utilisée.
    """

    answer: str
    sources: list[ContextSource]
    conversation_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    thought_process: str | None = None
    routing: RoutingDecision | None = None


@dataclass
class RAGConfig:
    """Configuration du RAG Engine."""

    # Recherche vectorielle
    vector_threshold: float = 0.7
    vector_max_results: int = 5

    # Recherche web
    use_web_search: bool = True
    web_max_tokens: int = 1024

    # Génération
    llm_model: str = "mistral-large-latest"
    llm_provider: str = "mistral"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # Orchestration
    use_smart_routing: bool = True

    # Mode réflexion
    enable_reflection: bool = False
    reflection_depth: int = 1

    # Streaming
    enable_streaming: bool = False

    # Logging
    log_conversations: bool = True
