"""
RAG Engine
===========

Moteur principal du système RAG (Retrieval-Augmented Generation).
Orchestre la recherche vectorielle, la recherche web et la génération.
"""

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from mistralai import Mistral

from src.agents.perplexity_agent import PerplexityAgent, WebSearchResult
from src.config.logging_config import LoggerMixin
from src.config.settings import get_settings
from src.models.conversation import (
    ContextSource,
    ConversationCreate,
    ConversationMetadata,
)
from src.models.document import DocumentMatch
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.document_repository import DocumentRepository
from src.services.embedding_service import EmbeddingService


@dataclass
class RAGResponse:
    """
    Réponse générée par le RAG Engine.
    
    Attributes:
        answer: Réponse textuelle générée.
        sources: Sources utilisées (vectorielles + web).
        conversation_id: ID de la conversation loggée.
        metadata: Métadonnées de génération.
    """
    answer: str
    sources: list[ContextSource]
    conversation_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


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
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    
    # Logging
    log_conversations: bool = True


class RAGEngine(LoggerMixin):
    """
    Moteur RAG principal.
    
    Orchestre le pipeline complet:
    1. Embedding de la requête
    2. Recherche vectorielle (contexte personnel)
    3. Recherche web Perplexity (contexte récent)
    4. Fusion des contextes
    5. Génération de la réponse avec Mistral
    6. Logging de la conversation
    """
    
    def __init__(self, config: RAGConfig | None = None) -> None:
        """
        Initialise le RAG Engine.
        
        Args:
            config: Configuration personnalisée.
        """
        settings = get_settings()
        self.config = config or RAGConfig(
            vector_threshold=settings.similarity_threshold,
            vector_max_results=settings.max_results,
            llm_model=settings.llm_model,
            llm_temperature=settings.llm_temperature,
            llm_max_tokens=settings.llm_max_tokens,
        )
        
        # Services
        self._mistral = Mistral(api_key=settings.mistral_api_key)
        self._embedding_service = EmbeddingService()
        self._document_repo = DocumentRepository()
        self._conversation_repo = ConversationRepository()
        self._perplexity = PerplexityAgent()
        
        # Session courante
        self._session_id = str(uuid4())
    
    @property
    def session_id(self) -> str:
        """ID de la session courante."""
        return self._session_id
    
    def new_session(self) -> str:
        """Crée une nouvelle session."""
        self._session_id = str(uuid4())
        return self._session_id
    
    async def query_async(
        self,
        question: str,
        system_prompt: str | None = None,
        use_web: bool | None = None,
    ) -> RAGResponse:
        """
        Traite une requête de manière asynchrone.
        
        Args:
            question: Question de l'utilisateur.
            system_prompt: Prompt système personnalisé.
            use_web: Forcer/désactiver la recherche web.
            
        Returns:
            RAGResponse avec la réponse et les sources.
        """
        start_time = time.time()
        sources: list[ContextSource] = []
        
        self.logger.info("Processing query", query_length=len(question))
        
        # 1. Recherche vectorielle
        vector_context, vector_sources = await self._search_vector_store(question)
        sources.extend(vector_sources)
        
        # 2. Recherche web (si activée)
        web_context = ""
        if (use_web is None and self.config.use_web_search) or use_web:
            web_result = await self._search_web(question)
            if web_result:
                web_context = web_result.content
                sources.append(ContextSource(
                    source_type="perplexity",
                    content_preview=web_context[:500],
                    url=web_result.sources[0] if web_result.sources else None,
                ))
        
        # 3. Construire le contexte fusionné
        full_context = self._build_context(vector_context, web_context)
        
        # 4. Générer la réponse
        answer, tokens = await self._generate_response(
            question,
            full_context,
            system_prompt,
        )
        
        # 5. Calculer les métriques
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # 6. Logger la conversation
        conversation_id = None
        if self.config.log_conversations:
            conversation_id = await self._log_conversation(
                question,
                answer,
                sources,
                tokens,
                elapsed_ms,
            )
        
        self.logger.info(
            "Query completed",
            elapsed_ms=elapsed_ms,
            sources_count=len(sources),
            tokens=tokens,
        )
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            conversation_id=conversation_id,
            metadata={
                "elapsed_ms": elapsed_ms,
                "tokens_input": tokens.get("input", 0),
                "tokens_output": tokens.get("output", 0),
                "vector_results": len(vector_sources),
                "web_search_used": bool(web_context),
            },
        )
    
    def query(
        self,
        question: str,
        system_prompt: str | None = None,
        use_web: bool | None = None,
    ) -> RAGResponse:
        """
        Version synchrone de query_async.
        
        Args:
            question: Question de l'utilisateur.
            system_prompt: Prompt système personnalisé.
            use_web: Forcer/désactiver la recherche web.
            
        Returns:
            RAGResponse avec la réponse et les sources.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.query_async(question, system_prompt, use_web)
        )
    
    async def _search_vector_store(
        self,
        query: str,
    ) -> tuple[str, list[ContextSource]]:
        """Recherche dans le Vector Store."""
        try:
            # Générer l'embedding de la requête
            query_embedding = self._embedding_service.embed_query(query)
            
            # Rechercher les documents similaires
            matches = self._document_repo.search_similar(
                query_embedding,
                threshold=self.config.vector_threshold,
                limit=self.config.vector_max_results,
            )
            
            if not matches:
                return "", []
            
            # Construire le contexte
            context_parts = []
            sources = []
            
            for match in matches:
                context_parts.append(match.content)
                sources.append(ContextSource(
                    source_type="vector_store",
                    document_id=match.id,
                    content_preview=match.content[:300],
                    similarity_score=match.similarity,
                ))
            
            return "\n\n---\n\n".join(context_parts), sources
            
        except Exception as e:
            self.logger.error("Vector search failed", error=str(e))
            return "", []
    
    async def _search_web(self, query: str) -> WebSearchResult | None:
        """Recherche web via Perplexity."""
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
    
    def _build_context(
        self,
        vector_context: str,
        web_context: str,
    ) -> str:
        """Fusionne les contextes."""
        parts = []
        
        if vector_context:
            parts.append(f"""=== CONTEXTE PERSONNEL ===
{vector_context}""")
        
        if web_context:
            parts.append(f"""=== INFORMATIONS WEB RÉCENTES ===
{web_context}""")
        
        return "\n\n".join(parts) if parts else ""
    
    async def _generate_response(
        self,
        question: str,
        context: str,
        custom_system: str | None,
    ) -> tuple[str, dict[str, int]]:
        """Génère la réponse avec Mistral."""
        
        default_system = """Tu es un assistant IA expert et personnalisé.

Tu as accès à deux types de contextes:
1. CONTEXTE PERSONNEL: Informations provenant de documents personnels (GitHub, CV, profils)
2. INFORMATIONS WEB RÉCENTES: Données actualisées du web

Utilise ces contextes pour fournir des réponses précises, personnalisées et à jour.
Si le contexte ne contient pas l'information, dis-le clairement.
Réponds en français sauf si la question est en anglais."""

        messages = [
            {"role": "system", "content": custom_system or default_system},
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Voici le contexte disponible:\n\n{context}",
            })
            messages.append({
                "role": "assistant", 
                "content": "J'ai bien pris en compte le contexte. Quelle est votre question?",
            })
        
        messages.append({"role": "user", "content": question})
        
        response = self._mistral.chat.complete(
            model=self.config.llm_model,
            messages=messages,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
        )
        
        answer = response.choices[0].message.content
        tokens = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        }
        
        return answer, tokens
    
    async def _log_conversation(
        self,
        question: str,
        answer: str,
        sources: list[ContextSource],
        tokens: dict[str, int],
        elapsed_ms: int,
    ) -> str | None:
        """Enregistre la conversation."""
        try:
            conv = ConversationCreate(
                session_id=self._session_id,
                user_query=question,
                ai_response=answer,
                context_sources=sources,
                metadata=ConversationMetadata(
                    model_used=self.config.llm_model,
                    tokens_input=tokens.get("input", 0),
                    tokens_output=tokens.get("output", 0),
                    response_time_ms=elapsed_ms,
                    perplexity_used=any(
                        s.source_type == "perplexity" for s in sources
                    ),
                    vector_results_count=sum(
                        1 for s in sources if s.source_type == "vector_store"
                    ),
                ),
            )
            
            created = self._conversation_repo.log_conversation(conv)
            return str(created.id)
            
        except Exception as e:
            self.logger.error("Failed to log conversation", error=str(e))
            return None
