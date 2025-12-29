"""
RAG Engine V2
==============

Moteur principal du système RAG (Retrieval-Augmented Generation).
Version 2 avec orchestration intelligente, multi-providers et streaming.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from uuid import uuid4

from src.agents.perplexity_agent import PerplexityAgent, WebSearchResult
from src.config.logging_config import LoggerMixin
from src.config.settings import get_settings
from src.models.conversation import (
    ContextSource,
    ConversationCreate,
    ConversationMetadata,
)
from src.models.document import DocumentMatch
from src.providers.llm import (
    LLMProviderFactory,
    LLMConfig,
    LLMResponse,
    StreamChunk,
    BaseLLMProvider,
)
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.document_repository import DocumentRepository
from src.services.embedding_service import EmbeddingService
from src.services.orchestrator import (
    QueryOrchestrator,
    RoutingDecision,
    QueryIntent,
    get_orchestrator,
)


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


class RAGEngine(LoggerMixin):
    """
    Moteur RAG principal V2.
    
    Orchestre le pipeline complet avec routage intelligent:
    1. Analyse de l'intention (Orchestrateur)
    2. Recherche conditionnelle (RAG si nécessaire)
    3. Recherche web conditionnelle (si nécessaire)
    4. Fusion des contextes
    5. Génération de la réponse (multi-provider)
    6. Logging de la conversation
    
    Optimisations:
    - Routage intelligent pour éviter les appels inutiles
    - Support multi-providers (Mistral, OpenAI, Gemini)
    - Mode streaming pour une meilleure UX
    - Mode réflexion pour des réponses approfondies
    """
    
    DEFAULT_SYSTEM_PROMPT = """Tu es un copilote intelligent et bienveillant. Tu parles comme un collègue compétent, pas comme un robot.

## Ton Style
- Sois **naturel et conversationnel** : parle comme à un ami, pas comme une FAQ
- Évite les listes à puces systématiques et les emojis excessifs
- Privilégie des **phrases fluides** et un ton chaleureux
- Sois **direct** : va droit au but sans blabla inutile
- Montre de l'**empathie** : comprends le besoin derrière la question

## Comment tu fonctionnes
Tu as accès à des informations personnelles (CV, projets GitHub, profils) et des données web récentes. Utilise-les naturellement dans tes réponses, comme si tu connaissais bien la personne.

## Règles importantes
- **Ne récite jamais tes capacités** : réponds directement à la question
- **Pas de "voici ce que je peux faire"** : agis, ne te présente pas
- Si on te dit "bonjour", réponds simplement "Salut ! Qu'est-ce qui t'amène ?" pas une liste de fonctionnalités
- Si tu n'as pas l'info, dis-le simplement : "Je n'ai pas cette info, mais..."
- **Une seule réponse claire** vaut mieux que 10 options

## Exemples de ton à adopter
❌ "Voici les différentes façons dont je peux vous aider : 1. Recherche technique 2. Aide personnalisée..."
✅ "Salut ! Qu'est-ce que je peux faire pour toi aujourd'hui ?"

❌ "D'après mon analyse du contexte fourni, je peux vous informer que..."
✅ "D'après ce que je vois dans tes projets, tu travailles beaucoup avec Python..."

## Langue
Réponds dans la langue de la question. Tutoie si l'utilisateur tutoie, vouvoie sinon."""
    
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
        self._llm_factory = LLMProviderFactory()
        self._orchestrator = get_orchestrator()
        self._embedding_service = EmbeddingService()
        self._document_repo = DocumentRepository()
        self._conversation_repo = ConversationRepository()
        self._perplexity = PerplexityAgent()
        
        # Provider LLM principal
        self._llm_provider: BaseLLMProvider | None = None
        
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
    
    def _get_llm_provider(self) -> BaseLLMProvider:
        """Récupère ou crée le provider LLM."""
        if self._llm_provider is None:
            llm_config = LLMConfig(
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                enable_reflection=self.config.enable_reflection,
                stream=self.config.enable_streaming,
            )
            self._llm_provider = self._llm_factory.get_provider(
                self.config.llm_provider,
                llm_config,
            )
        return self._llm_provider
    
    def _detect_provider_from_model(self, model_id: str) -> str:
        """Détecte le provider à partir du model_id."""
        model_lower = model_id.lower()
        
        if model_lower.startswith("gpt") or model_lower.startswith("o1"):
            return "openai"
        elif model_lower.startswith("deepseek"):
            return "deepseek"
        elif model_lower.startswith("gemini"):
            return "gemini"
        elif model_lower.startswith("claude"):
            return "anthropic"
        else:
            # Default to Mistral for mistral-* and unknown models
            return "mistral"
    
    async def query_async(
        self,
        question: str,
        system_prompt: str | None = None,
        use_web: bool | None = None,
        use_rag: bool | None = None,
        enable_reflection: bool | None = None,
        user_id: str | None = None,
        api_key_id: str | None = None,
        model_id: str | None = None,
    ) -> RAGResponse:
        """
        Traite une requête de manière asynchrone avec routage intelligent.
        
        Args:
            question: Question de l'utilisateur.
            system_prompt: Prompt système personnalisé.
            use_web: Forcer/désactiver la recherche web.
            use_rag: Forcer/désactiver le RAG.
            enable_reflection: Activer le mode réflexion.
            user_id: ID utilisateur pour l'isolation contextuelle.
            api_key_id: ID de la clé API/agent pour isolation documents.
            model_id: Modèle LLM à utiliser (override agent_config).
            
        Returns:
            RAGResponse avec la réponse et les sources.
        """
        start_time = time.time()
        sources: list[ContextSource] = []
        
        self.logger.info("Processing query", query_length=len(question))
        
        # 1. Routage intelligent
        routing = await self._orchestrator.route(
            question,
            force_rag=use_rag if use_rag is not None else False,
            force_web=use_web if use_web is not None else False,
            force_reflection=enable_reflection if enable_reflection is not None else self.config.enable_reflection,
        )
        
        self.logger.info(
            "Routing decision",
            intent=routing.intent.value,
            use_rag=routing.should_use_rag,
            use_web=routing.should_use_web,
            confidence=routing.confidence,
            routing_latency_ms=routing.latency_ms,
        )
        
        # 2. Recherche vectorielle (si nécessaire)
        vector_context = ""
        if routing.should_use_rag:
            vector_context, vector_sources = await self._search_vector_store(
                question, user_id, api_key_id
            )
            sources.extend(vector_sources)
        
        # 3. Recherche web (si nécessaire)
        web_context = ""
        if routing.should_use_web:
            web_result = await self._search_web(question)
            if web_result:
                web_context = web_result.content
                sources.append(ContextSource(
                    source_type="perplexity",
                    content_preview=web_context[:500],
                    url=web_result.sources[0] if web_result.sources else None,
                ))
        
        # 4. Construire le contexte fusionné
        full_context = self._build_context(vector_context, web_context)
        
        # 5. Générer la réponse
        # Utiliser le model_id agent si fourni
        if model_id:
            # Créer un provider spécifique pour cet agent
            provider_type = self._detect_provider_from_model(model_id)
            llm_config = LLMConfig(
                model=model_id,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                enable_reflection=routing.use_reflection,
            )
            provider = self._llm_factory.get_provider(provider_type, llm_config, cache=False)
        else:
            provider = self._get_llm_provider()
        
        messages = provider.build_messages(
            question,
            context=full_context if full_context else None,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        
        # Mode réflexion ou standard
        if routing.use_reflection:
            llm_response = await provider.generate_with_reflection(messages)
        else:
            llm_response = await provider.generate(
                messages,
                system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            )
        
        answer = llm_response.content
        thought_process = llm_response.thought_process
        
        # 6. Calculer les métriques
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # 7. Logger la conversation
        conversation_id = None
        if self.config.log_conversations:
            conversation_id = await self._log_conversation(
                question,
                answer,
                sources,
                {
                    "input": llm_response.tokens_input,
                    "output": llm_response.tokens_output,
                },
                elapsed_ms,
                user_id,
                thought_process=thought_process,
                routing_decision=routing,
            )
        
        self.logger.info(
            "Query completed",
            elapsed_ms=elapsed_ms,
            sources_count=len(sources),
            tokens_input=llm_response.tokens_input,
            tokens_output=llm_response.tokens_output,
            routing_intent=routing.intent.value,
        )
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            conversation_id=conversation_id,
            metadata={
                "elapsed_ms": elapsed_ms,
                "tokens_input": llm_response.tokens_input,
                "tokens_output": llm_response.tokens_output,
                "vector_results": len([s for s in sources if s.source_type == "vector_store"]),
                "web_search_used": bool(web_context),
                "model_used": llm_response.model_used,
                "routing_intent": routing.intent.value,
                "routing_confidence": routing.confidence,
                "routing_latency_ms": routing.latency_ms,
            },
            thought_process=thought_process,
            routing=routing,
        )
    
    async def query_stream(
        self,
        question: str,
        system_prompt: str | None = None,
        use_web: bool | None = None,
        use_rag: bool | None = None,
        enable_reflection: bool | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Traite une requête en mode streaming.
        
        Émet des événements SSE pour chaque étape:
        - routing: Décision de routage
        - search_start: Début d'une recherche
        - search_complete: Fin d'une recherche
        - chunk: Morceau de réponse
        - thought: Pensée interne (mode réflexion)
        - complete: Réponse terminée
        
        Args:
            question: Question de l'utilisateur.
            system_prompt: Prompt système personnalisé.
            use_web: Forcer la recherche web.
            use_rag: Forcer le RAG.
            enable_reflection: Mode réflexion.
            user_id: ID utilisateur.
            
        Yields:
            Dictionnaires d'événements SSE.
        """
        start_time = time.time()
        sources: list[ContextSource] = []
        
        # 1. Routage
        yield {"event": "routing", "data": {"status": "started"}}
        
        routing = await self._orchestrator.route(
            question,
            force_rag=use_rag if use_rag is not None else False,
            force_web=use_web if use_web is not None else False,
            force_reflection=enable_reflection if enable_reflection is not None else self.config.enable_reflection,
        )
        
        yield {
            "event": "routing",
            "data": {
                "status": "completed",
                "intent": routing.intent.value,
                "use_rag": routing.should_use_rag,
                "use_web": routing.should_use_web,
                "confidence": routing.confidence,
            },
        }
        
        # 2. Recherches parallèles si nécessaire
        vector_context = ""
        web_context = ""
        
        async def search_rag():
            nonlocal vector_context, sources
            if routing.should_use_rag:
                yield {"event": "search_start", "data": {"type": "rag"}}
                context, src = await self._search_vector_store(question, user_id)
                vector_context = context
                sources.extend(src)
                yield {
                    "event": "search_complete",
                    "data": {"type": "rag", "results": len(src)},
                }
        
        async def search_web():
            nonlocal web_context, sources
            if routing.should_use_web:
                yield {"event": "search_start", "data": {"type": "web"}}
                result = await self._search_web(question)
                if result:
                    web_context = result.content
                    sources.append(ContextSource(
                        source_type="perplexity",
                        content_preview=web_context[:500],
                        url=result.sources[0] if result.sources else None,
                    ))
                yield {
                    "event": "search_complete",
                    "data": {"type": "web", "found": bool(result)},
                }
        
        # Exécuter les recherches
        if routing.should_use_rag:
            yield {"event": "search_start", "data": {"type": "rag"}}
            vector_context, vector_sources = await self._search_vector_store(
                question, user_id
            )
            sources.extend(vector_sources)
            yield {
                "event": "search_complete",
                "data": {"type": "rag", "results": len(vector_sources)},
            }
        
        if routing.should_use_web:
            yield {"event": "search_start", "data": {"type": "web"}}
            web_result = await self._search_web(question)
            if web_result:
                web_context = web_result.content
                sources.append(ContextSource(
                    source_type="perplexity",
                    content_preview=web_context[:500],
                    url=web_result.sources[0] if web_result.sources else None,
                ))
            yield {
                "event": "search_complete",
                "data": {"type": "web", "found": bool(web_result)},
            }
        
        # 3. Génération en streaming
        yield {"event": "generation_start", "data": {}}
        
        full_context = self._build_context(vector_context, web_context)
        provider = self._get_llm_provider()
        messages = provider.build_messages(
            question,
            context=full_context if full_context else None,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        
        full_response = ""
        thought_content = ""
        
        async for chunk in provider.generate_stream(messages):
            if chunk.is_thought:
                thought_content += chunk.content
                yield {
                    "event": "thought",
                    "data": {"content": chunk.content},
                }
            else:
                full_response += chunk.content
                yield {
                    "event": "chunk",
                    "data": {"content": chunk.content},
                }
        
        # 4. Finalisation
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Logger la conversation
        conversation_id = None
        if self.config.log_conversations:
            conversation_id = await self._log_conversation(
                question,
                full_response,
                sources,
                {"input": 0, "output": 0},  # Tokens non disponibles en streaming
                elapsed_ms,
                user_id,
                thought_process=thought_content if thought_content else None,
            )
        
        yield {
            "event": "complete",
            "data": {
                "conversation_id": conversation_id,
                "sources": [
                    {
                        "source_type": s.source_type,
                        "content_preview": s.content_preview,
                        "similarity_score": s.similarity_score,
                        "url": s.url,
                    }
                    for s in sources
                ],
                "metadata": {
                    "elapsed_ms": elapsed_ms,
                    "routing_intent": routing.intent.value,
                },
            },
        }
    
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
        user_id: str | None = None,
        api_key_id: str | None = None,
    ) -> tuple[str, list[ContextSource]]:
        """Recherche dans le Vector Store avec isolation par agent."""
        try:
            # Générer l'embedding de la requête
            query_embedding = self._embedding_service.embed_query(query)
            
            # Rechercher les documents similaires (filtrés par api_key_id si fourni)
            matches = self._document_repo.search_similar(
                query_embedding,
                threshold=self.config.vector_threshold,
                limit=self.config.vector_max_results,
                user_id=user_id,
                api_key_id=api_key_id,  # Isolation par agent
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
    
    async def _log_conversation(
        self,
        question: str,
        answer: str,
        sources: list[ContextSource],
        tokens: dict[str, int],
        elapsed_ms: int,
        user_id: str | None = None,
        thought_process: str | None = None,
        routing_decision: Any | None = None,
    ) -> str | None:
        """Enregistre la conversation avec les données de réflexion et routage."""
        try:
            # Préparer les données de routage
            routing_info = None
            if routing_decision:
                routing_info = {
                    "intent": routing_decision.intent.value,
                    "confidence": routing_decision.confidence,
                    "use_rag": routing_decision.should_use_rag,
                    "use_web": routing_decision.should_use_web,
                    "use_reflection": routing_decision.use_reflection,
                    "latency_ms": routing_decision.latency_ms,
                    "reasoning": routing_decision.reasoning,
                }
            
            conv = ConversationCreate(
                session_id=self._session_id,
                user_query=question,
                ai_response=answer,
                context_sources=sources,
                user_id=user_id,
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
                    # Données de réflexion
                    reflection_data={
                        "thought_process": thought_process,
                    } if thought_process else None,
                    reflection_enabled=thought_process is not None,
                    # Données de routage
                    routing_info=routing_info,
                    llm_provider=self.config.llm_provider if self.config.llm_provider else "mistral",
                ),
            )
            
            created = self._conversation_repo.log_conversation(conv)
            return str(created.id)
            
        except Exception as e:
            self.logger.error("Failed to log conversation", error=str(e))
            return None
