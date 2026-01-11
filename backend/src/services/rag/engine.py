"""
RAG Engine V3 (Refactored)
===========================

Moteur principal du système RAG, refactorisé en architecture modulaire.
Délègue les responsabilités aux modules Retriever et Generator.

~450 lignes au lieu de 1013 dans la version originale.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from src.config.logging_config import LoggerMixin
from src.config.settings import get_settings
from src.models.conversation import (
    ContextSource,
    ConversationCreate,
    ConversationMetadata,
)
from src.repositories.agent_memory_repository import AgentMemoryRepository
from src.repositories.conversation_repository import ConversationRepository
from src.services.circuit_breaker import get_circuit_breaker
from src.services.orchestrator import get_orchestrator
from src.services.rag.config import RAGConfig, RAGResponse
from src.services.rag.generator import RAGGenerator
from src.services.rag.retriever import RAGRetriever
from src.services.trace_service import get_trace_service


class RAGEngine(LoggerMixin):
    """
    Moteur RAG principal V3 (Refactored).

    Orchestre le pipeline complet avec architecture modulaire :
    - RAGRetriever : Recherche vectorielle et web
    - RAGGenerator : Génération LLM
    - Orchestrator : Routage intelligent
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

        # Modules
        self._retriever = RAGRetriever(self.config)
        self._generator = RAGGenerator(self.config)
        self._orchestrator = get_orchestrator()

        # Services
        self._conversation_repo = ConversationRepository()
        self._memory_repo = AgentMemoryRepository()
        self._trace_service = get_trace_service()
        self._breaker = get_circuit_breaker()

        # Session
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
        use_rag: bool | None = None,
        enable_reflection: bool | None = None,
        user_id: str | None = None,
        api_key_id: str | None = None,
        model_id: str | None = None,
        agent_id: str | None = None,
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
            model_id: Modèle LLM à utiliser.
            agent_id: ID de l'agent pour la mémoire conversationnelle.

        Returns:
            RAGResponse avec la réponse et les sources.
        """
        start_time = time.time()
        sources: list[ContextSource] = []

        self.logger.info("Processing query", query_length=len(question))

        # 1. Routage intelligent
        routing = await self._orchestrator.route(
            question,
            force_rag=use_rag is True,
            force_web=use_web is True,
            disable_rag=use_rag is False,
            disable_web=use_web is False,
            force_reflection=(
                enable_reflection
                if enable_reflection is not None
                else self.config.enable_reflection
            ),
        )

        self.logger.info(
            "Routing decision",
            intent=routing.intent.value,
            use_rag=routing.should_use_rag,
            use_web=routing.should_use_web,
            confidence=routing.confidence,
        )

        # 2. Recherche vectorielle (si nécessaire)
        vector_context = ""
        if routing.should_use_rag:
            result = await self._retriever.search_vector_store(
                question, user_id, api_key_id
            )
            vector_context = result.context
            sources.extend(result.sources)

        # 3. Recherche web (si nécessaire)
        web_context = ""
        if routing.should_use_web:
            web_result = await self._retriever.search_web(question)
            if web_result:
                web_context = web_result.content
                sources.append(
                    ContextSource(
                        source_type="perplexity",
                        content_preview=web_context[:500],
                        url=web_result.sources[0] if web_result.sources else None,
                    )
                )

        # 4. Fusionner le contexte
        full_context = self._retriever.build_context(vector_context, web_context)

        # 5. Récupérer le provider LLM
        provider, provider_type = self._generator.get_provider(
            model_id=model_id,
            user_id=user_id,
            enable_reflection=routing.use_reflection,
        )

        # 6. Récupérer la mémoire de l'agent
        memory_messages: list[dict[str, str]] = []
        if agent_id:
            memory_messages = self._memory_repo.get_as_llm_messages(agent_id)

        # 7. Construire les messages
        messages = self._generator.build_messages(
            question=question,
            memory=memory_messages,
            context=full_context if full_context else None,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )

        # 8. Génération avec Circuit Breaker et Fallback
        async def call_llm():
            if routing.use_reflection:
                return await provider.generate_with_reflection(messages)
            return await provider.generate(
                messages,
                system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            )

        async def fallback_call():
            self.logger.warning("Primary provider failing, attempting fallback")
            fallback_p = self._generator.get_fallback_provider(provider_type, user_id)
            fallback_messages = self._generator.build_messages(
                question,
                context=full_context if full_context else None,
                system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            )
            return await fallback_p.generate(fallback_messages)

        try:
            llm_response = await self._breaker.execute(
                provider_type, call_llm, fallback=fallback_call
            )
        except Exception as e:
            self.logger.error("LLM Generation failed", error=str(e))
            raise

        # 9. Sauvegarder dans la mémoire de l'agent
        if agent_id:
            try:
                self._memory_repo.add_exchange(agent_id, question, llm_response.content)
            except Exception as e:
                self.logger.warning("Failed to update agent memory", error=str(e))

        # 10. Logger la conversation
        elapsed_ms = int((time.time() - start_time) * 1000)
        conversation_id = await self._log_conversation(
            question=question,
            answer=llm_response.content,
            sources=sources,
            tokens={"input": llm_response.tokens_input, "output": llm_response.tokens_output},
            elapsed_ms=elapsed_ms,
            user_id=user_id,
            thought_process=llm_response.thought_process,
            routing_decision=routing,
        )

        self.logger.info(
            "Query completed",
            elapsed_ms=elapsed_ms,
            sources_count=len(sources),
        )

        return RAGResponse(
            answer=llm_response.content,
            sources=sources,
            conversation_id=conversation_id,
            metadata={
                "elapsed_ms": elapsed_ms,
                "tokens_input": llm_response.tokens_input,
                "tokens_output": llm_response.tokens_output,
                "model_used": llm_response.model_used,
                "routing_intent": routing.intent.value,
            },
            thought_process=llm_response.thought_process,
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
        api_key_id: str | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Traite une requête en mode streaming.

        Émet des événements SSE pour chaque étape.
        """
        start_time = time.time()
        sources: list[ContextSource] = []

        # 1. Routage
        yield {"event": "routing", "data": {"status": "started"}}

        routing = await self._orchestrator.route(
            question,
            force_rag=use_rag is True,
            force_web=use_web is True,
            disable_rag=use_rag is False,
            disable_web=use_web is False,
            force_reflection=enable_reflection or self.config.enable_reflection,
        )

        yield {
            "event": "routing",
            "data": {
                "status": "completed",
                "intent": routing.intent.value,
                "use_rag": routing.should_use_rag,
                "use_web": routing.should_use_web,
            },
        }

        # 2. Recherches
        vector_context = ""
        web_context = ""

        if routing.should_use_rag:
            yield {"event": "search_start", "data": {"type": "rag"}}
            result = await self._retriever.search_vector_store(question, user_id, api_key_id)
            vector_context = result.context
            sources.extend(result.sources)
            yield {"event": "search_complete", "data": {"type": "rag", "results": len(result.sources)}}

        if routing.should_use_web:
            yield {"event": "search_start", "data": {"type": "web"}}
            web_result = await self._retriever.search_web(question)
            if web_result:
                web_context = web_result.content
                sources.append(
                    ContextSource(
                        source_type="perplexity",
                        content_preview=web_context[:500],
                        url=web_result.sources[0] if web_result.sources else None,
                    )
                )
            yield {"event": "search_complete", "data": {"type": "web", "found": bool(web_result)}}

        # 3. Génération en streaming
        yield {"event": "generation_start", "data": {}}

        full_context = self._retriever.build_context(vector_context, web_context)
        provider, provider_type = self._generator.get_provider(
            model_id=model_id,
            user_id=user_id,
            enable_reflection=routing.use_reflection,
            stream=True,
        )

        messages = self._generator.build_messages(
            question,
            context=full_context if full_context else None,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )

        full_response = ""
        thought_content = ""

        try:
            async for chunk in provider.generate_stream(messages):
                if chunk.is_thought:
                    thought_content += chunk.content
                    yield {"event": "thought", "data": {"content": chunk.content}}
                else:
                    full_response += chunk.content
                    yield {"event": "chunk", "data": {"content": chunk.content}}

            await self._breaker._record_success(provider_type)

        except Exception as e:
            await self._breaker._record_failure(provider_type, e)
            self.logger.error("Streaming error", error=str(e))
            yield {"event": "error", "data": {"message": "Service temporairement indisponible."}}

        # 4. Finalisation
        elapsed_ms = int((time.time() - start_time) * 1000)

        if self.config.log_conversations:
            await self._log_conversation(
                question, full_response, sources,
                {"input": 0, "output": 0}, elapsed_ms, user_id,
                thought_process=thought_content if thought_content else None,
            )

        yield {
            "event": "complete",
            "data": {
                "sources": [{"source_type": s.source_type, "content_preview": s.content_preview} for s in sources],
                "metadata": {"elapsed_ms": elapsed_ms},
            },
        }

    def query(
        self,
        question: str,
        system_prompt: str | None = None,
        use_web: bool | None = None,
    ) -> RAGResponse:
        """Version synchrone de query_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.query_async(question, system_prompt, use_web))

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
        """Enregistre la conversation."""
        try:
            routing_info = None
            if routing_decision:
                routing_info = {
                    "intent": routing_decision.intent.value,
                    "confidence": routing_decision.confidence,
                    "use_rag": routing_decision.should_use_rag,
                    "use_web": routing_decision.should_use_web,
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
                    perplexity_used=any(s.source_type == "perplexity" for s in sources),
                    vector_results_count=sum(1 for s in sources if s.source_type == "vector_store"),
                    reflection_enabled=thought_process is not None,
                    routing_info=routing_info,
                    llm_provider=self.config.llm_provider,
                ),
            )

            created = self._conversation_repo.log_conversation(conv)

            if user_id:
                self._trace_service.log_success(
                    user_id=user_id,
                    model_used=self.config.llm_model,
                    prompt_tokens=tokens.get("input", 0),
                    completion_tokens=tokens.get("output", 0),
                    latency_ms=elapsed_ms,
                )

            return str(created.id)

        except Exception as e:
            self.logger.error("Failed to log conversation", error=str(e))
            return None
