"""
API Routes - Document Jobs
===========================

Endpoints pour la gestion des jobs d'ingestion de documents:
- Création de jobs d'ingestion
- Suivi de progression
- Historique des jobs
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.api.auth import ApiKeyValidation, require_scope
from src.config.logging_config import get_logger
from src.services.document_processor import (
    get_document_processor,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["Document Jobs"])


# ============================================
# Simple Repository for document_jobs
# ============================================


class DocumentJobRepository:
    """Repository simple pour les jobs de documents."""

    def __init__(self):
        from supabase import create_client

        from src.config.settings import get_settings

        settings = get_settings()
        self._client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )

    @property
    def client(self):
        return self._client

    @property
    def table(self):
        return self._client.table("document_jobs")


def get_job_repo() -> DocumentJobRepository:
    """Factory pour le repository."""
    return DocumentJobRepository()


# ============================================
# Schemas
# ============================================


class JobCreateRequest(BaseModel):
    """Requête de création de job."""

    content: str = Field(..., min_length=10, description="Contenu à ingérer")
    source_filename: str = Field(..., description="Nom du fichier source")
    source_type: str = Field(default="text", description="Type: text, pdf, github")
    webhook_url: str | None = Field(None, description="URL webhook de notification")


class JobStatusResponse(BaseModel):
    """Statut d'un job."""

    id: str
    status: str
    progress: int
    chunks_total: int
    chunks_processed: int
    source_filename: str
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobCreateResponse(BaseModel):
    """Réponse après création de job."""

    job_id: str
    status: str
    message: str


class JobListResponse(BaseModel):
    """Liste des jobs."""

    jobs: list[JobStatusResponse]
    total: int


# ============================================
# Endpoints
# ============================================


@router.post("/ingest", response_model=JobCreateResponse)
async def create_ingest_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
):
    """
    Crée un job d'ingestion de document asynchrone.

    Le document sera traité en arrière-plan avec:
    - Chunking intelligent avec overlap
    - Génération des embeddings par batch
    - Stockage dans le vector store

    Utilisez GET /jobs/{job_id} pour suivre la progression.
    """
    try:
        processor = get_document_processor()

        # Créer le job
        job_id = await processor.create_job(
            api_key_id=str(api_key.api_key_id),
            user_id=str(api_key.user_id),
            content=request.content,
            source_filename=request.source_filename,
            source_type=request.source_type,
            webhook_url=request.webhook_url,
        )

        # Lancer le traitement en arrière-plan
        background_tasks.add_task(processor.process_job, job_id)

        logger.info(
            "Ingest job created",
            job_id=str(job_id),
            source=request.source_filename,
            api_key_id=str(api_key.api_key_id),
        )

        return JobCreateResponse(
            job_id=str(job_id),
            status="pending",
            message="Job créé. Utilisez GET /jobs/{job_id} pour suivre la progression.",
        )

    except Exception as e:
        logger.error("Create ingest job failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du job: {str(e)}")


@router.post("/ingest/file", response_model=JobCreateResponse)
async def create_ingest_job_from_file(
    file: UploadFile = File(..., description="Fichier à ingérer (PDF, TXT)"),
    webhook_url: str | None = None,
    background_tasks: BackgroundTasks = None,
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
):
    """
    Crée un job d'ingestion depuis un fichier uploadé.

    Formats supportés:
    - PDF (.pdf)
    - Texte (.txt, .md)
    """
    try:
        # Lire le contenu du fichier
        content = await file.read()

        # Déterminer le type
        filename = file.filename or "unknown"
        if filename.lower().endswith(".pdf"):
            source_type = "pdf"
            # Pour les PDF, on a besoin d'extraction
            # TODO: Intégrer avec pdf_provider
            raise HTTPException(
                status_code=400,
                detail="L'upload PDF direct nécessite le provider PDF. Utilisez /ingest/pdf à la place.",
            )
        else:
            source_type = "text"
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Le fichier n'est pas un texte valide (encodage UTF-8 attendu)",
                )

        processor = get_document_processor()

        job_id = await processor.create_job(
            api_key_id=str(api_key.api_key_id),
            user_id=str(api_key.user_id),
            content=text_content,
            source_filename=filename,
            source_type=source_type,
            webhook_url=webhook_url,
        )

        background_tasks.add_task(processor.process_job, job_id)

        return JobCreateResponse(
            job_id=str(job_id),
            status="pending",
            message=f"Job créé pour {filename}. Suivi via GET /jobs/{job_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create file ingest job failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
    repo: DocumentJobRepository = Depends(get_job_repo),
):
    """
    Récupère le statut d'un job d'ingestion.

    Utilisez cette endpoint pour suivre la progression en temps réel.
    Poll régulièrement (ex: toutes les secondes) pendant le traitement.
    """
    try:
        processor = get_document_processor()

        # Essayer d'abord la mémoire locale
        status = await processor.get_job_status(UUID(job_id))

        if status:
            return JobStatusResponse(
                id=status["id"],
                status=status["status"],
                progress=status["progress"],
                chunks_total=status["chunks_total"],
                chunks_processed=status["chunks_processed"],
                source_filename=status["source_filename"],
                error_message=status.get("error_message"),
            )

        # Sinon chercher en DB
        result = (
            repo.table.select("*")
            .eq("id", job_id)
            .eq("api_key_id", str(api_key.api_key_id))
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Job non trouvé")

        data = result.data
        return JobStatusResponse(
            id=data["id"],
            status=data["status"],
            progress=data["progress"],
            chunks_total=data["chunks_total"],
            chunks_processed=data["chunks_processed"],
            source_filename=data["source_filename"],
            error_message=data.get("error_message"),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get job status failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
    repo: DocumentJobRepository = Depends(get_job_repo),
):
    """
    Liste les jobs d'ingestion de l'agent.

    Filtres optionnels:
    - status: pending, processing, completed, failed
    """
    try:
        query = repo.table.select("*", count="exact").eq("api_key_id", str(api_key.api_key_id))

        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        result = query.execute()

        jobs = [
            JobStatusResponse(
                id=job["id"],
                status=job["status"],
                progress=job["progress"],
                chunks_total=job["chunks_total"],
                chunks_processed=job["chunks_processed"],
                source_filename=job["source_filename"],
                error_message=job.get("error_message"),
                created_at=job.get("created_at"),
                started_at=job.get("started_at"),
                completed_at=job.get("completed_at"),
            )
            for job in (result.data or [])
        ]

        return JobListResponse(jobs=jobs, total=result.count or len(jobs))

    except Exception as e:
        logger.error("List jobs failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    api_key: ApiKeyValidation = Depends(require_scope("ingest")),
    repo: DocumentJobRepository = Depends(get_job_repo),
):
    """
    Annule un job en attente ou en cours.

    Note: Les chunks déjà traités ne seront pas supprimés.
    """
    try:
        # Mettre à jour le statut
        result = (
            repo.table.update({"status": "cancelled"})
            .eq("id", job_id)
            .eq("api_key_id", str(api_key.api_key_id))
            .in_("status", ["pending", "processing"])
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Job non trouvé ou déjà terminé")

        return {"message": "Job annulé", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cancel job failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")
