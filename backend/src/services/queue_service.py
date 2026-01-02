"""
Queue Service
==============

Service pour gérer les jobs asynchrones via Redis Queue.

Fournit une interface simple pour enqueue des tâches et
suivre leur progression.
"""

from dataclasses import dataclass
from typing import Any

from redis import Redis
from rq import Queue

from src.config.logging_config import LoggerMixin
from src.config.settings import get_settings
from src.workers.tasks import (
    JobProgress,
    JobStatus,
    get_job_status,
    ingest_github_repository_task,
    ingest_pdf_document_task,
)


@dataclass
class EnqueueResult:
    """Résultat d'un enqueue de job."""

    job_id: str
    queue: str
    status: str


class QueueService(LoggerMixin):
    """
    Service pour gérer la queue de jobs.

    Permet d'enqueue des tâches d'ingestion et de suivre
    leur progression.
    """

    def __init__(self) -> None:
        """Initialise le service de queue."""
        settings = get_settings()
        self._redis_url = settings.redis_url
        self._connection: Redis | None = None
        self._queue: Queue | None = None

    @property
    def is_available(self) -> bool:
        """Vérifie si Redis est disponible."""
        return bool(self._redis_url)

    def _get_queue(self, name: str = "ingestion") -> Queue:
        """Récupère ou crée une queue."""
        if not self._redis_url:
            raise RuntimeError("Redis URL not configured. Jobs cannot be queued.")

        if self._connection is None:
            self._connection = Redis.from_url(self._redis_url)

        return Queue(name, connection=self._connection)

    def enqueue_github_ingestion(
        self,
        user_id: str,
        repo_url: str,
        api_key_id: str,
        branch: str = "main",
    ) -> EnqueueResult:
        """
        Enqueue un job d'ingestion GitHub.

        Args:
            user_id: ID de l'utilisateur.
            repo_url: URL du repository GitHub.
            api_key_id: ID de la clé API.
            branch: Branche à ingérer.

        Returns:
            EnqueueResult avec l'ID du job.
        """
        queue = self._get_queue("ingestion")

        job = queue.enqueue(
            ingest_github_repository_task,
            user_id=user_id,
            repo_url=repo_url,
            api_key_id=api_key_id,
            branch=branch,
            job_timeout="30m",  # 30 minutes max
            result_ttl=86400,  # Résultat gardé 24h
            failure_ttl=86400,
            meta={
                "status": JobStatus.PENDING.value,
                "progress": 0,
                "message": "En attente de traitement...",
                "type": "github_ingestion",
                "repo_url": repo_url,
            },
        )

        self.logger.info(
            "GitHub ingestion job queued",
            job_id=job.id,
            repo_url=repo_url,
        )

        return EnqueueResult(
            job_id=job.id,
            queue="ingestion",
            status="queued",
        )

    def enqueue_pdf_ingestion(
        self,
        user_id: str,
        file_path: str,
        api_key_id: str,
        filename: str,
    ) -> EnqueueResult:
        """
        Enqueue un job d'ingestion PDF.

        Args:
            user_id: ID de l'utilisateur.
            file_path: Chemin vers le fichier temporaire.
            api_key_id: ID de la clé API.
            filename: Nom original du fichier.

        Returns:
            EnqueueResult avec l'ID du job.
        """
        queue = self._get_queue("ingestion")

        job = queue.enqueue(
            ingest_pdf_document_task,
            user_id=user_id,
            file_path=file_path,
            api_key_id=api_key_id,
            filename=filename,
            job_timeout="10m",  # 10 minutes max pour un PDF
            result_ttl=86400,
            failure_ttl=86400,
            meta={
                "status": JobStatus.PENDING.value,
                "progress": 0,
                "message": "En attente de traitement...",
                "type": "pdf_ingestion",
                "filename": filename,
            },
        )

        self.logger.info(
            "PDF ingestion job queued",
            job_id=job.id,
            filename=filename,
        )

        return EnqueueResult(
            job_id=job.id,
            queue="ingestion",
            status="queued",
        )

    def get_job_status(self, job_id: str) -> JobProgress | None:
        """
        Récupère le statut d'un job.

        Args:
            job_id: ID du job.

        Returns:
            JobProgress ou None si introuvable.
        """
        return get_job_status(job_id)

    def get_queue_stats(self) -> dict[str, Any]:
        """
        Récupère les statistiques de la queue.

        Returns:
            Stats incluant nombre de jobs en attente, en cours, etc.
        """
        if not self.is_available:
            return {"available": False}

        try:
            queue = self._get_queue("ingestion")
            return {
                "available": True,
                "queue_name": "ingestion",
                "pending_jobs": len(queue),
                "failed_jobs": len(queue.failed_job_registry),
                "finished_jobs": len(queue.finished_job_registry),
            }
        except Exception as e:
            self.logger.error("Failed to get queue stats", error=str(e))
            return {"available": False, "error": str(e)}


# Singleton
_queue_service: QueueService | None = None


def get_queue_service() -> QueueService:
    """Retourne l'instance singleton du service de queue."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
