"""
RAG Retriever
==============

Responsable de la récupération de contexte depuis différentes sources :
- Vector Store (documents personnels)
- Recherche Web (Perplexity)
"""

from dataclasses import dataclass

from src.agents.perplexity_agent import PerplexityAgent, WebSearchResult
from src.config.logging_config import LoggerMixin
from src.models.conversation import ContextSource
from src.repositories.document_repository import DocumentRepository
from src.services.embedding_service import EmbeddingService
from src.services.rag.config import RAGConfig


@dataclass
class RetrievalResult:
    """Résultat d'une recherche de contexte."""

    context: str
    sources: list[ContextSource]


class RAGRetriever(LoggerMixin):
    """
    Gestionnaire de récupération de contexte pour le RAG.

    Responsabilités :
    - Recherche vectorielle dans le Vector Store
    - Recherche web via Perplexity
    - Fusion des contextes
    """

    def __init__(self, config: RAGConfig) -> None:
        """
        Initialise le retriever.

        Args:
            config: Configuration RAG.
        """
        self.config = config
        self._embedding_service = EmbeddingService()
        self._document_repo = DocumentRepository()
        self._perplexity = PerplexityAgent()

    async def search_vector_store(
        self,
        query: str,
        user_id: str | None = None,
        api_key_id: str | None = None,
    ) -> RetrievalResult:
        """
        Recherche dans le Vector Store avec isolation par agent.

        Args:
            query: Requête de recherche.
            user_id: ID utilisateur pour filtrage.
            api_key_id: ID de la clé API/agent pour isolation.

        Returns:
            RetrievalResult avec le contexte et les sources.
        """
        try:
            # Générer l'embedding de la requête
            query_embedding = self._embedding_service.embed_query(query)

            # Rechercher les documents similaires
            matches = self._document_repo.search_similar(
                query_embedding,
                threshold=self.config.vector_threshold,
                limit=self.config.vector_max_results,
                user_id=user_id,
                api_key_id=api_key_id,
            )

            if not matches:
                return RetrievalResult(context="", sources=[])

            # Construire le contexte
            context_parts = []
            sources = []

            for match in matches:
                context_parts.append(match.content)
                sources.append(
                    ContextSource(
                        source_type="vector_store",
                        document_id=match.id,
                        content_preview=match.content[:300],
                        similarity_score=match.similarity,
                    )
                )

            return RetrievalResult(
                context="\n\n---\n\n".join(context_parts),
                sources=sources,
            )

        except Exception as e:
            self.logger.error("Vector search failed", error=str(e))
            return RetrievalResult(context="", sources=[])

    async def search_web(self, query: str) -> WebSearchResult | None:
        """
        Recherche web via Perplexity.

        Args:
            query: Requête de recherche.

        Returns:
            WebSearchResult ou None si désactivé/erreur.
        """
        if not self._perplexity.is_enabled:
            return None

        try:
            return await self._perplexity.search(
                query,
                max_tokens=self.config.web_max_tokens,
            )
        except Exception as e:
            self.logger.error("Web search failed", error=str(e))
            return None

    def build_context(
        self,
        vector_context: str,
        web_context: str,
    ) -> str:
        """
        Fusionne les contextes vectoriel et web.

        Args:
            vector_context: Contexte des documents personnels.
            web_context: Contexte de la recherche web.

        Returns:
            Contexte fusionné formaté.
        """
        parts = []

        if vector_context:
            parts.append(
                f"""=== CONTEXTE PERSONNEL ===
{vector_context}"""
            )

        if web_context:
            parts.append(
                f"""=== INFORMATIONS WEB RÉCENTES ===
{web_context}"""
            )

        return "\n\n".join(parts) if parts else ""
