"""
Background Tasks
=================

Tâches lourdes exécutées en background via Redis Queue.

Ces tâches sont enqueued par l'API et exécutées par un worker séparé.
Chaque tâche met à jour son statut pour permettre le polling côté frontend.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from rq import get_current_job

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Statuts possibles d'un job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobProgress:
    """Progression d'un job."""

    status: JobStatus
    progress: int  # 0-100
    message: str
    result: Any = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


def update_job_progress(
    progress: int,
    message: str,
    status: JobStatus = JobStatus.RUNNING,
    result: Any = None,
    error: str | None = None,
) -> None:
    """
    Met à jour la progression du job courant.

    Args:
        progress: Pourcentage de progression (0-100).
        message: Message de statut.
        status: Statut du job.
        result: Résultat partiel ou final.
        error: Message d'erreur si échec.
    """
    job = get_current_job()
    if job:
        job.meta["progress"] = progress
        job.meta["message"] = message
        job.meta["status"] = status.value
        job.meta["updated_at"] = datetime.utcnow().isoformat()

        if result is not None:
            job.meta["result"] = result
        if error:
            job.meta["error"] = error

        job.save_meta()


def get_job_status(job_id: str) -> JobProgress | None:
    """
    Récupère le statut d'un job par son ID.

    Args:
        job_id: ID du job RQ.

    Returns:
        JobProgress ou None si job introuvable.
    """
    from redis import Redis
    from rq.job import Job

    from src.config.settings import get_settings

    settings = get_settings()
    if not settings.redis_url:
        return None

    try:
        redis_conn = Redis.from_url(settings.redis_url)
        job = Job.fetch(job_id, connection=redis_conn)

        status = JobStatus(job.meta.get("status", "pending"))
        if job.is_finished:
            status = JobStatus.COMPLETED
        elif job.is_failed:
            status = JobStatus.FAILED

        return JobProgress(
            status=status,
            progress=job.meta.get("progress", 0),
            message=job.meta.get("message", "En attente..."),
            result=job.meta.get("result"),
            error=job.meta.get("error"),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.ended_at.isoformat() if job.ended_at else None,
        )
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        return None


# ==============================================
# Tâches d'ingestion
# ==============================================


def ingest_github_repository_task(
    user_id: str,
    repo_url: str,
    api_key_id: str,
    branch: str = "main",
) -> dict:
    """
    Ingère un repository GitHub en background.

    Cette tâche :
    1. Clone/accède au repository
    2. Extrait les fichiers de code
    3. Génère les embeddings
    4. Stocke dans le vector store

    Args:
        user_id: ID de l'utilisateur propriétaire.
        repo_url: URL du repository GitHub.
        api_key_id: ID de la clé API (pour isolation des documents).
        branch: Branche à ingérer.

    Returns:
        Résultat avec nombre de documents ingérés.
    """
    from src.providers.github_provider import GitHubProvider
    from src.repositories.document_repository import DocumentRepository
    from src.services.embedding_service import EmbeddingService

    logger.info(
        "Starting GitHub ingestion",
        repo_url=repo_url,
        api_key_id=api_key_id,
    )

    update_job_progress(5, f"Connexion à GitHub: {repo_url}")

    try:
        # Étape 1: Extraire les fichiers
        update_job_progress(10, "Extraction des fichiers...")
        github = GitHubProvider()
        documents = list(github.extract(repo_url))

        if not documents:
            update_job_progress(
                100,
                "Aucun fichier trouvé",
                status=JobStatus.COMPLETED,
                result={"documents_count": 0},
            )
            return {"documents_count": 0}

        total_docs = len(documents)
        logger.info("Files extracted", count=total_docs)

        # Étape 2: Générer les embeddings
        update_job_progress(30, f"Génération des embeddings ({total_docs} fichiers)...")
        embedding_service = EmbeddingService()

        texts = [doc.content for doc in documents]
        embeddings = embedding_service.embed_batch(texts)

        # Étape 3: Stocker dans Supabase
        update_job_progress(70, "Stockage dans la base vectorielle...")
        doc_repo = DocumentRepository()

        stored_count = 0
        for i, (doc, embedding) in enumerate(zip(documents, embeddings, strict=True)):
            progress = 70 + int((i / total_docs) * 25)
            update_job_progress(progress, f"Stockage {i + 1}/{total_docs}...")

            try:
                doc_repo.store_document(
                    content=doc.content,
                    embedding=embedding,
                    source_id=doc.source_id,
                    metadata={
                        **doc.metadata,
                        "api_key_id": api_key_id,
                        "user_id": user_id,
                    },
                )
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store document", source_id=doc.source_id, error=str(e))

        result = {
            "documents_count": stored_count,
            "total_extracted": total_docs,
            "repo_url": repo_url,
        }

        update_job_progress(
            100,
            f"Ingestion terminée: {stored_count} documents",
            status=JobStatus.COMPLETED,
            result=result,
        )

        logger.info("GitHub ingestion completed", **result)
        return result

    except Exception as e:
        error_msg = str(e)
        logger.error("GitHub ingestion failed", error=error_msg)
        update_job_progress(
            0,
            f"Erreur: {error_msg}",
            status=JobStatus.FAILED,
            error=error_msg,
        )
        raise


def ingest_pdf_document_task(
    user_id: str,
    file_path: str,
    api_key_id: str,
    filename: str,
) -> dict:
    """
    Ingère un document PDF en background.

    Args:
        user_id: ID de l'utilisateur.
        file_path: Chemin vers le fichier PDF temporaire.
        api_key_id: ID de la clé API.
        filename: Nom original du fichier.

    Returns:
        Résultat avec nombre de pages ingérées.
    """
    from src.providers.pdf_provider import PDFProvider
    from src.repositories.document_repository import DocumentRepository
    from src.services.embedding_service import EmbeddingService

    logger.info(
        "Starting PDF ingestion",
        filename=filename,
        api_key_id=api_key_id,
    )

    update_job_progress(5, f"Lecture du PDF: {filename}")

    try:
        # Étape 1: Extraire le texte
        update_job_progress(10, "Extraction du texte...")
        pdf_provider = PDFProvider(chunk_by_page=True)
        documents = list(pdf_provider.extract(file_path))

        if not documents:
            update_job_progress(
                100,
                "PDF vide ou illisible",
                status=JobStatus.COMPLETED,
                result={"pages_count": 0},
            )
            return {"pages_count": 0}

        total_pages = len(documents)
        logger.info("PDF extracted", pages=total_pages)

        # Étape 2: Générer les embeddings
        update_job_progress(30, f"Génération des embeddings ({total_pages} pages)...")
        embedding_service = EmbeddingService()

        texts = [doc.content for doc in documents]
        embeddings = embedding_service.embed_batch(texts)

        # Étape 3: Stocker
        update_job_progress(70, "Stockage dans la base vectorielle...")
        doc_repo = DocumentRepository()

        stored_count = 0
        for i, (doc, embedding) in enumerate(zip(documents, embeddings, strict=True)):
            progress = 70 + int((i / total_pages) * 25)
            update_job_progress(progress, f"Stockage page {i + 1}/{total_pages}...")

            try:
                doc_repo.store_document(
                    content=doc.content,
                    embedding=embedding,
                    source_id=doc.source_id,
                    metadata={
                        **doc.metadata,
                        "api_key_id": api_key_id,
                        "user_id": user_id,
                        "original_filename": filename,
                    },
                )
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store page", page=i + 1, error=str(e))

        result = {
            "pages_count": stored_count,
            "total_pages": total_pages,
            "filename": filename,
        }

        update_job_progress(
            100,
            f"Ingestion terminée: {stored_count} pages",
            status=JobStatus.COMPLETED,
            result=result,
        )

        logger.info("PDF ingestion completed", **result)
        return result

    except Exception as e:
        error_msg = str(e)
        logger.error("PDF ingestion failed", error=error_msg)
        update_job_progress(
            0,
            f"Erreur: {error_msg}",
            status=JobStatus.FAILED,
            error=error_msg,
        )
        raise
