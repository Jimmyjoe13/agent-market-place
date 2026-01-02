"""
Document Processor Service
===========================

Traitement asynchrone des documents avec pipeline résilient.
Utilise le pattern Producer/Consumer pour l'ingestion en arrière-plan.

Features:
- Chunking stratégique avec overlap
- Retry automatique avec backoff exponentiel
- Tracking de progression en temps réel
- Support webhooks de notification
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from src.config.logging_config import get_logger
from src.config.settings import get_settings
from src.repositories.document_repository import DocumentRepository
from src.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Statuts possibles d'un job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChunkingConfig:
    """Configuration du chunking de documents."""

    chunk_size: int = 1000  # Taille cible des chunks
    chunk_overlap: int = 200  # Overlap entre chunks
    min_chunk_size: int = 100  # Taille minimum d'un chunk
    separator: str = "\n\n"  # Séparateur principal
    fallback_separators: list[str] = field(default_factory=lambda: ["\n", ". ", " "])


@dataclass
class ProcessingJob:
    """Représentation d'un job de traitement."""

    id: UUID
    api_key_id: UUID
    user_id: UUID
    source_filename: str
    source_type: str
    content: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    chunks_total: int = 0
    chunks_processed: int = 0
    error_message: str | None = None
    webhook_url: str | None = None
    created_at: float = field(default_factory=time.time)


class RecursiveTextSplitter:
    """
    Splitter de texte récursif avec overlap.

    Divise le texte en utilisant une hiérarchie de séparateurs,
    en essayant de garder les chunks cohérents sémantiquement.
    """

    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    def split(self, text: str) -> list[str]:
        """
        Divise le texte en chunks avec overlap.

        Args:
            text: Texte à diviser

        Returns:
            Liste de chunks
        """
        if not text or len(text) <= self.config.chunk_size:
            return [text] if text else []

        # Essayer chaque séparateur dans l'ordre
        all_separators = [self.config.separator] + self.config.fallback_separators

        return self._recursive_split(text, all_separators)

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Split récursif avec fallback sur les séparateurs."""
        if not separators:
            # Plus de séparateurs, découper brut
            return self._split_by_size(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep not in text:
            return self._recursive_split(text, remaining_seps)

        parts = text.split(sep)
        chunks = []
        current_chunk = ""

        for part in parts:
            test_chunk = current_chunk + sep + part if current_chunk else part

            if len(test_chunk) <= self.config.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # Part trop grande, split récursif
                if len(part) > self.config.chunk_size:
                    sub_chunks = self._recursive_split(part, remaining_seps)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        # Appliquer l'overlap
        return self._apply_overlap(chunks)

    def _split_by_size(self, text: str) -> list[str]:
        """Découpage brut par taille."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.config.chunk_size
            chunks.append(text[start:end])
            start = end - self.config.chunk_overlap

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Ajoute l'overlap entre les chunks."""
        if len(chunks) <= 1 or self.config.chunk_overlap <= 0:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Prendre la fin du chunk précédent
            overlap_text = prev_chunk[-self.config.chunk_overlap :]

            # Préfixer le chunk actuel avec l'overlap
            overlapped.append(overlap_text + " ... " + current_chunk)

        return overlapped


class DocumentProcessor:
    """
    Service de traitement asynchrone des documents.

    Gère le pipeline complet:
    1. Chunking du contenu
    2. Génération des embeddings par batch
    3. Stockage dans le vector store
    4. Mise à jour du statut de progression
    """

    def __init__(
        self,
        chunking_config: ChunkingConfig | None = None,
        batch_size: int = 10,
        max_retries: int = 3,
    ):
        self.settings = get_settings()
        self.splitter = RecursiveTextSplitter(chunking_config)
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._embedding_service: EmbeddingService | None = None
        self._doc_repo: DocumentRepository | None = None

        # Queue de jobs en mémoire (pour MVP, à remplacer par Redis/TaskIQ)
        self._jobs: dict[UUID, ProcessingJob] = {}
        self._processing_lock = asyncio.Lock()

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy loading du service d'embedding."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def doc_repo(self) -> DocumentRepository:
        """Lazy loading du repository."""
        if self._doc_repo is None:
            self._doc_repo = DocumentRepository()
        return self._doc_repo

    async def create_job(
        self,
        api_key_id: str | UUID,
        user_id: str | UUID,
        content: str,
        source_filename: str,
        source_type: str = "text",
        webhook_url: str | None = None,
    ) -> UUID:
        """
        Crée un nouveau job de traitement.

        Args:
            api_key_id: ID de la clé API (agent)
            user_id: ID de l'utilisateur
            content: Contenu à traiter
            source_filename: Nom du fichier source
            source_type: Type de source (text, pdf, github)
            webhook_url: URL de notification (optionnel)

        Returns:
            ID du job créé
        """
        job_id = uuid4()

        job = ProcessingJob(
            id=job_id,
            api_key_id=UUID(str(api_key_id)),
            user_id=UUID(str(user_id)),
            source_filename=source_filename,
            source_type=source_type,
            content=content,
            webhook_url=webhook_url,
        )

        self._jobs[job_id] = job

        logger.info(
            "Document job created",
            job_id=str(job_id),
            source=source_filename,
            content_length=len(content),
        )

        return job_id

    async def get_job_status(self, job_id: UUID) -> dict[str, Any] | None:
        """Récupère le statut d'un job."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        return {
            "id": str(job.id),
            "status": job.status.value,
            "progress": job.progress,
            "chunks_total": job.chunks_total,
            "chunks_processed": job.chunks_processed,
            "error_message": job.error_message,
            "source_filename": job.source_filename,
        }

    async def process_job(self, job_id: UUID) -> bool:
        """
        Traite un job de manière asynchrone.

        Args:
            job_id: ID du job à traiter

        Returns:
            True si succès, False sinon
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.error("Job not found", job_id=str(job_id))
            return False

        async with self._processing_lock:
            try:
                job.status = JobStatus.PROCESSING

                # 1. Chunking
                logger.info("Starting chunking", job_id=str(job_id))
                chunks = self.splitter.split(job.content)
                job.chunks_total = len(chunks)

                if not chunks:
                    raise ValueError("No chunks generated from content")

                # 2. Traitement par batch
                documents_created = []

                for i in range(0, len(chunks), self.batch_size):
                    batch = chunks[i : i + self.batch_size]

                    # Générer les embeddings du batch
                    for j, chunk in enumerate(batch):
                        chunk_index = i + j

                        # Retry avec backoff
                        for attempt in range(self.max_retries):
                            try:
                                # Générer embedding
                                embedding = await self.embedding_service.embed_text(chunk)

                                # Créer le document
                                doc_id = await self.doc_repo.create_document(
                                    content=chunk,
                                    embedding=embedding,
                                    source_type=job.source_type,
                                    source_id=f"{job.source_filename}#chunk_{chunk_index}",
                                    metadata={
                                        "chunk_index": chunk_index,
                                        "total_chunks": job.chunks_total,
                                        "source_filename": job.source_filename,
                                    },
                                    user_id=str(job.user_id),
                                    api_key_id=str(job.api_key_id),
                                )

                                documents_created.append(doc_id)
                                break

                            except Exception:
                                if attempt == self.max_retries - 1:
                                    raise
                                await asyncio.sleep(2**attempt)  # Backoff exponentiel

                        job.chunks_processed = chunk_index + 1
                        job.progress = int((job.chunks_processed / job.chunks_total) * 100)

                # 3. Succès
                job.status = JobStatus.COMPLETED
                job.progress = 100

                logger.info(
                    "Document processing completed",
                    job_id=str(job_id),
                    documents_created=len(documents_created),
                )

                # 4. Webhook notification
                if job.webhook_url:
                    await self._send_webhook(job, success=True)

                return True

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = str(e)

                logger.error("Document processing failed", job_id=str(job_id), error=str(e))

                if job.webhook_url:
                    await self._send_webhook(job, success=False)

                return False

    async def _send_webhook(self, job: ProcessingJob, success: bool) -> None:
        """Envoie une notification webhook."""
        if not job.webhook_url:
            return

        try:
            import httpx

            payload = {
                "job_id": str(job.id),
                "status": job.status.value,
                "success": success,
                "source_filename": job.source_filename,
                "chunks_processed": job.chunks_processed,
                "error_message": job.error_message,
            }

            async with httpx.AsyncClient() as client:
                await client.post(job.webhook_url, json=payload, timeout=10.0)

        except Exception as e:
            logger.warning("Webhook notification failed", error=str(e))

    async def process_job_background(self, job_id: UUID) -> None:
        """Lance le traitement en arrière-plan."""
        asyncio.create_task(self.process_job(job_id))


# ============================================
# Singleton
# ============================================

_document_processor: DocumentProcessor | None = None


def get_document_processor() -> DocumentProcessor:
    """Retourne l'instance globale du processor."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
