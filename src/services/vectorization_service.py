"""
Vectorization Service
======================

Service d'ingestion pour transformer les données en embeddings
et les stocker dans Supabase.
"""

from dataclasses import dataclass
from typing import Iterator

from src.config.logging_config import LoggerMixin
from src.models.document import DocumentCreate, Document
from src.providers.base import BaseProvider
from src.repositories.document_repository import DocumentRepository
from src.services.embedding_service import EmbeddingService


@dataclass
class IngestionStats:
    """Statistiques d'ingestion."""
    total_processed: int = 0
    total_created: int = 0
    total_skipped: int = 0
    total_errors: int = 0


class VectorizationService(LoggerMixin):
    """
    Service pour vectoriser et stocker les documents.
    
    Orchestre l'extraction, l'embedding et le stockage
    des documents dans le Vector Store.
    """
    
    def __init__(self) -> None:
        """Initialise le service de vectorisation."""
        self._embedding_service = EmbeddingService()
        self._document_repo = DocumentRepository()
    
    def ingest_from_provider(
        self,
        provider: BaseProvider,
        sources: list[str],
        skip_duplicates: bool = True,
    ) -> IngestionStats:
        """
        Ingère des documents depuis un provider.
        
        Args:
            provider: Provider de données à utiliser.
            sources: Liste des sources à extraire.
            skip_duplicates: Ignorer les documents déjà présents.
            
        Returns:
            Statistiques d'ingestion.
        """
        stats = IngestionStats()
        
        self.logger.info(
            "Starting ingestion",
            provider=provider.__class__.__name__,
            sources_count=len(sources),
        )
        
        for doc in provider.extract_all(sources):
            stats.total_processed += 1
            
            try:
                # Vérifier les doublons
                if skip_duplicates and self._document_repo.exists_by_hash(doc.content):
                    self.logger.debug("Duplicate skipped", source_id=doc.source_id)
                    stats.total_skipped += 1
                    continue
                
                # Générer l'embedding
                embedding = self._embedding_service.embed_text(doc.content)
                
                # Stocker dans Supabase
                self._document_repo.create_from_model(doc, embedding)
                stats.total_created += 1
                
            except Exception as e:
                self.logger.error(
                    "Ingestion error",
                    source_id=doc.source_id,
                    error=str(e),
                )
                stats.total_errors += 1
        
        self.logger.info(
            "Ingestion completed",
            **stats.__dict__,
        )
        
        return stats
    
    def ingest_documents(
        self,
        documents: list[DocumentCreate],
        skip_duplicates: bool = True,
    ) -> IngestionStats:
        """
        Ingère une liste de documents.
        
        Args:
            documents: Documents à ingérer.
            skip_duplicates: Ignorer les doublons.
            
        Returns:
            Statistiques d'ingestion.
        """
        stats = IngestionStats()
        
        for doc in documents:
            stats.total_processed += 1
            
            try:
                if skip_duplicates and self._document_repo.exists_by_hash(doc.content):
                    stats.total_skipped += 1
                    continue
                
                embedding = self._embedding_service.embed_text(doc.content)
                self._document_repo.create_from_model(doc, embedding)
                stats.total_created += 1
                
            except Exception as e:
                self.logger.error("Error", source_id=doc.source_id, error=str(e))
                stats.total_errors += 1
        
        return stats
    
    def ingest_single(
        self,
        content: str,
        source_type: str,
        source_id: str,
        metadata: dict | None = None,
    ) -> Document | None:
        """
        Ingère un document unique.
        
        Args:
            content: Contenu textuel.
            source_type: Type de source.
            source_id: Identifiant de la source.
            metadata: Métadonnées optionnelles.
            
        Returns:
            Document créé ou None si erreur.
        """
        try:
            # Vérifier les doublons
            if self._document_repo.exists_by_hash(content):
                self.logger.info("Document already exists", source_id=source_id)
                return None
            
            # Générer l'embedding
            embedding = self._embedding_service.embed_text(content)
            
            # Créer le document
            data = {
                "content": content,
                "embedding": embedding,
                "source_type": source_type,
                "source_id": source_id,
                "metadata": metadata or {},
            }
            
            return self._document_repo.create(data)
            
        except Exception as e:
            self.logger.error("Failed to ingest", error=str(e))
            return None
