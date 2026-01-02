"""
API Routes
===========

Endpoints FastAPI pour le système RAG.

Tous les endpoints sont protégés par authentification API Key.
Utilisez le header `X-API-Key` ou le query param `api_key`.

Scopes requis par endpoint:
- `/query`, `/session/new`: `query`
- `/feedback`, `/analytics`: `feedback`
- `/ingest/*`: `ingest`
- `/training/*`: `admin`
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.auth import require_any_scope, require_scope
from src.api.schemas import (
    AnalyticsResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestGithubRequest,
    IngestResponse,
    IngestTextRequest,
    QueryRequest,
    QueryResponse,
    SourceResponse,
)
from src.config.logging_config import get_logger
from src.models.api_key import ApiKeyValidation
from src.models.document import DocumentCreate, DocumentMetadata, SourceType
from src.providers import GithubProvider, PDFProvider
from src.services import FeedbackService, RAGEngine, VectorizationService
from src.services.rate_limiter import get_rate_limiter

logger = get_logger(__name__)

# Créer le router
router = APIRouter()

# Instances des services (lazy loading)
_rag_engine: RAGEngine | None = None
_feedback_service: FeedbackService | None = None
_vectorization: VectorizationService | None = None


def get_rag_engine() -> RAGEngine:
    """Retourne l'instance du RAG Engine."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine


def get_feedback_service() -> FeedbackService:
    """Retourne l'instance du Feedback Service."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service


def get_vectorization() -> VectorizationService:
    """Retourne l'instance du Vectorization Service."""
    global _vectorization
    if _vectorization is None:
        _vectorization = VectorizationService()
    return _vectorization


# ===== Query Endpoints =====


@router.post(
    "/query",
    response_model=QueryResponse,
    tags=["RAG"],
    summary="Interroger le système RAG",
    description="""
Interroge le système RAG avec une question.

Le système utilise un **routage intelligent** pour optimiser la latence :
1. Analyse l'intention pour déterminer le meilleur chemin
2. Recherche conditionnelle dans le Vector Store
3. Recherche web conditionnelle via Perplexity
4. Génération de réponse contextuelle (multi-provider)

**Options avancées** :
- `enable_reflection`: Active le mode réflexion approfondie (Chain of Thought)
- `use_rag`: Force la recherche dans les documents personnels
- `use_web_search`: Force la recherche web
- `provider`: Sélectionne le provider LLM (mistral, openai, gemini)

**Scope requis**: `query`
    """,
    responses={
        200: {"description": "Réponse générée avec succès"},
        401: {"description": "Clé API requise"},
        403: {"description": "Scope insuffisant"},
    },
)
async def query_rag(
    request: QueryRequest,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
) -> QueryResponse:
    """
    Interroge le système RAG avec routage intelligent.

    Le routeur analyse automatiquement la requête pour déterminer :
    - S'il faut chercher dans les documents personnels (RAG)
    - S'il faut chercher sur le web (actualités)
    - Si une réflexion approfondie est nécessaire
    """
    try:
        # 1. Rate limiting pour le mode réflexion (si activé)
        if request.enable_reflection:
            limiter = get_rate_limiter()
            allowed, count, retry_after = await limiter.check_reflection_limit(
                str(api_key.user_id) if api_key.user_id else str(api_key.key_id)
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "REFLECTION_LIMIT_EXCEEDED",
                        "message": f"Limite de réflexion atteinte. Réessayez dans {retry_after}s.",
                        "retry_after": retry_after,
                    },
                )

        rag = get_rag_engine()

        # Utiliser la session existante si fournie
        if request.session_id:
            rag._session_id = request.session_id

        # Récupérer la config agent depuis ApiKeyValidation (champs directs)
        # Les champs sont: model_id, system_prompt, rag_enabled, agent_name

        # Déterminer le system_prompt (priorité: request > agent_config > default)
        effective_system_prompt = request.system_prompt
        if not effective_system_prompt and api_key.system_prompt:
            effective_system_prompt = api_key.system_prompt

        # Déterminer si RAG est activé (config agent peut le désactiver)
        use_rag = request.use_rag
        if api_key.rag_enabled is False:
            use_rag = False

        response = await rag.query_async(
            question=request.question,
            system_prompt=effective_system_prompt,
            use_web=request.use_web_search,
            use_rag=use_rag,
            enable_reflection=request.enable_reflection,
            user_id=str(api_key.user_id) if api_key.user_id else None,
            api_key_id=str(api_key.key_id) if api_key.key_id else None,  # Pour isolation documents
            model_id=api_key.model_id,  # Modèle LLM configuré sur l'agent
        )

        # Convertir les sources
        sources = [
            SourceResponse(
                source_type=s.source_type,
                content_preview=s.content_preview,
                similarity_score=s.similarity_score,
                url=s.url,
            )
            for s in response.sources
        ]

        # Préparer les infos de routage
        routing_info = None
        if response.routing:
            routing_info = {
                "intent": response.routing.intent.value,
                "use_rag": response.routing.should_use_rag,
                "use_web": response.routing.should_use_web,
                "confidence": response.routing.confidence,
                "reasoning": response.routing.reasoning,
                "latency_ms": response.routing.latency_ms,
            }

        logger.info(
            "Query processed",
            key_id=str(api_key.key_id),
            question_length=len(request.question),
            routing_intent=response.routing.intent.value if response.routing else "unknown",
        )

        return QueryResponse(
            answer=response.answer,
            sources=sources,
            conversation_id=response.conversation_id,
            session_id=rag.session_id,
            metadata=response.metadata,
            thought_process=response.thought_process,
            routing=routing_info,
        )

    except Exception as e:
        logger.error("Query failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/session/new",
    tags=["RAG"],
    summary="Créer une nouvelle session",
    description="Crée une nouvelle session de conversation.",
)
async def new_session(
    api_key: ApiKeyValidation = Depends(require_scope("query")),
) -> dict:
    """Crée une nouvelle session de conversation."""
    rag = get_rag_engine()
    session_id = rag.new_session()
    return {"session_id": session_id}


@router.post(
    "/query/stream",
    tags=["RAG"],
    summary="Interroger le système RAG en streaming",
    description="""
Interroge le système RAG avec streaming SSE (Server-Sent Events).

Retourne un flux d'événements permettant un feedback temps réel :
- `routing`: Décision de routage (intent, use_rag, use_web)
- `search_start`: Début d'une recherche (type: rag ou web)
- `search_complete`: Fin d'une recherche avec résultats
- `generation_start`: Début de la génération
- `chunk`: Morceau de réponse (contenu progressif)
- `thought`: Pensée interne (si mode réflexion activé)
- `complete`: Réponse terminée avec sources et métadonnées

**Scope requis**: `query`
    """,
)
async def query_rag_stream(
    request: QueryRequest,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
):
    """
    Interroge le système RAG avec streaming SSE.

    Émet des événements pour chaque étape du traitement,
    permettant un feedback visuel temps réel dans l'UI.
    """
    import json

    from fastapi.responses import StreamingResponse

    async def generate_events():
        try:
            # 1. Rate limiting pour le mode réflexion (si activé)
            if request.enable_reflection:
                limiter = get_rate_limiter()
                allowed, count, retry_after = await limiter.check_reflection_limit(
                    str(api_key.user_id) if api_key.user_id else str(api_key.key_id)
                )
                if not allowed:
                    error_data = json.dumps(
                        {
                            "error": "REFLECTION_LIMIT_EXCEEDED",
                            "message": f"Limite de réflexion atteinte. Réessayez dans {retry_after}s.",
                            "retry_after": retry_after,
                        }
                    )
                    yield f"event: error\ndata: {error_data}\n\n"
                    return

            rag = get_rag_engine()

            if request.session_id:
                rag._session_id = request.session_id

            async for event in rag.query_stream(
                question=request.question,
                system_prompt=request.system_prompt,
                use_web=request.use_web_search,
                use_rag=request.use_rag,
                enable_reflection=request.enable_reflection,
                user_id=str(api_key.user_id) if api_key.user_id else None,
            ):
                # Format SSE
                event_type = event.get("event", "message")
                data = json.dumps(event.get("data", {}))
                yield f"event: {event_type}\ndata: {data}\n\n"

        except Exception as e:
            logger.error("Streaming query failed", error=str(e))
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ===== Feedback Endpoints =====


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"],
    summary="Soumettre un feedback",
    description="""
Soumet un feedback pour une conversation.

Permet de noter la qualité de la réponse (1-5) et optionnellement
de la marquer pour ré-injection dans le Vector Store.

**Scope requis**: `feedback`
    """,
)
async def submit_feedback(
    request: FeedbackRequest,
    api_key: ApiKeyValidation = Depends(require_scope("feedback")),
) -> FeedbackResponse:
    """
    Soumet un feedback pour une conversation.
    """
    try:
        feedback = get_feedback_service()

        # Ajouter le feedback
        success = feedback.add_feedback(
            request.conversation_id,
            request.score,
            request.comment,
        )

        # Flaguer si demandé
        if success and request.flag_for_training:
            feedback.flag_for_training(request.conversation_id)

        return FeedbackResponse(
            success=success,
            message="Feedback enregistré" if success else "Échec de l'enregistrement",
        )

    except Exception as e:
        logger.error("Feedback failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    tags=["Feedback"],
    summary="Statistiques de feedback",
    description="Récupère les statistiques de feedback sur une période.",
)
async def get_analytics(
    days: int = 30,
    api_key: ApiKeyValidation = Depends(require_any_scope("feedback", "admin")),
) -> AnalyticsResponse:
    """Récupère les statistiques de feedback."""
    try:
        feedback = get_feedback_service()
        stats = feedback.get_analytics(days)
        return AnalyticsResponse(**stats)
    except Exception as e:
        logger.error("Analytics failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Ingestion Endpoints =====


@router.post(
    "/ingest/github",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingérer des repositories GitHub",
    description="""
Ingère le contenu de repositories GitHub.

Extrait les README, fichiers de code et documentation.

**Scope requis**: `ingest`
    """,
)
async def ingest_github(
    request: IngestGithubRequest,
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
) -> IngestResponse:
    """Ingère des repositories GitHub."""
    try:
        provider = GithubProvider()
        vectorization = get_vectorization()

        stats = vectorization.ingest_from_provider(
            provider,
            request.repositories,
            skip_duplicates=request.skip_duplicates,
            user_id=str(api_key.user_id) if api_key.user_id else None,
        )

        logger.info(
            "GitHub ingestion completed",
            key_id=str(api_key.key_id),
            repos=len(request.repositories),
            created=stats.total_created,
        )
        return IngestResponse(
            success=True,
            documents_created=stats.total_created,
            documents_skipped=stats.total_skipped,
            errors=stats.total_errors,
            message=f"{stats.total_created} documents créés",
        )

    except Exception as e:
        logger.error("GitHub ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/ingest/text",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingérer du texte",
    description="Ingère un texte manuellement dans le Vector Store.",
)
async def ingest_text(
    request: IngestTextRequest,
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
) -> IngestResponse:
    """Ingère un texte manuellement."""
    try:
        vectorization = get_vectorization()

        doc = DocumentCreate(
            content=request.content,
            source_type=SourceType.MANUAL,
            source_id=request.source_id,
            metadata=DocumentMetadata(
                title=request.title,
                tags=request.tags,
            ),
        )

        stats = vectorization.ingest_documents(
            [doc],
            user_id=str(api_key.user_id) if api_key.user_id else None,
        )

        return IngestResponse(
            success=stats.total_created > 0,
            documents_created=stats.total_created,
            documents_skipped=stats.total_skipped,
            errors=stats.total_errors,
            message="Document ingéré" if stats.total_created else "Document ignoré",
        )

    except Exception as e:
        logger.error("Text ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/ingest/pdf",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingérer un PDF",
    description="Upload et ingère un fichier PDF.",
)
async def ingest_pdf(
    file: UploadFile = File(..., description="Fichier PDF à ingérer"),
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
) -> IngestResponse:
    """Ingère un fichier PDF uploadé."""
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

        provider = PDFProvider()
        content = await file.read()

        documents = list(provider.extract_from_bytes(content, file.filename))

        if not documents:
            return IngestResponse(
                success=False,
                documents_created=0,
                documents_skipped=0,
                errors=0,
                message="Aucun contenu extrait du PDF",
            )

        vectorization = get_vectorization()
        doc_creates = [provider.to_document(d) for d in documents]
        stats = vectorization.ingest_documents(
            doc_creates,
            user_id=str(api_key.user_id) if api_key.user_id else None,
        )

        return IngestResponse(
            success=stats.total_created > 0,
            documents_created=stats.total_created,
            documents_skipped=stats.total_skipped,
            errors=stats.total_errors,
            message=f"PDF traité: {stats.total_created} documents créés",
        )

    except Exception as e:
        logger.error("PDF ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/training/process",
    tags=["Training"],
    summary="Traiter la queue de training",
    description="""
Traite les conversations flaggées pour ré-injection dans le Vector Store.

**Scope requis**: `admin`
    """,
)
async def process_training_queue(
    limit: int = 50,
    api_key: ApiKeyValidation = Depends(require_scope("admin")),
) -> dict:
    """Traite la queue de ré-injection."""
    try:
        feedback = get_feedback_service()
        created = feedback.process_training_queue(limit)
        return {
            "success": True,
            "documents_created": created,
            "message": f"{created} documents réinjectés",
        }
    except Exception as e:
        logger.error("Training process failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
