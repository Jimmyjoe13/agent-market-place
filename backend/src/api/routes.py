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

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from src.api.auth import require_api_key, require_scope, require_any_scope
from src.api.schemas import (
    QueryRequest,
    QueryResponse,
    SourceResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestGithubRequest,
    IngestTextRequest,
    IngestResponse,
    AnalyticsResponse,
)
from src.config.logging_config import get_logger
from src.models.api_key import ApiKeyValidation
from src.models.document import DocumentCreate, DocumentMetadata, SourceType
from src.providers import GithubProvider, PDFProvider
from src.services import RAGEngine, FeedbackService, VectorizationService

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

Le système effectue :
1. Une recherche dans le Vector Store (documents personnels)
2. Une recherche web via Perplexity (si activée)
3. Une génération de réponse contextuelle via Mistral

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
    Interroge le système RAG.
    
    Effectue une recherche dans le Vector Store et optionnellement sur le web,
    puis génère une réponse contextuelle.
    """
    try:
        rag = get_rag_engine()
        
        # Utiliser la session existante si fournie
        if request.session_id:
            rag._session_id = request.session_id
        
        response = await rag.query_async(
            question=request.question,
            system_prompt=request.system_prompt,
            use_web=request.use_web_search,
            user_id=str(api_key.user_id) if api_key.user_id else None,
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
        
        logger.info(
            "Query processed",
            key_id=str(api_key.id),
            question_length=len(request.question),
        )
        
        return QueryResponse(
            answer=response.answer,
            sources=sources,
            conversation_id=response.conversation_id,
            session_id=rag.session_id,
            metadata=response.metadata,
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
            key_id=str(api_key.id),
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
