"""
Base Provider
==============

Classe abstraite définissant l'interface pour tous les providers de données.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator

from src.config.logging_config import LoggerMixin
from src.models.document import DocumentCreate, DocumentMetadata, SourceType


@dataclass
class ExtractedContent:
    """
    Contenu extrait par un provider.
    
    Attributes:
        content: Texte extrait.
        source_id: Identifiant unique de la source.
        metadata: Métadonnées associées.
    """
    content: str
    source_id: str
    metadata: dict[str, Any]


class BaseProvider(ABC, LoggerMixin):
    """
    Provider de base pour l'extraction de données.
    
    Tous les providers doivent implémenter cette interface.
    """
    
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Type de source du provider."""
        pass
    
    @abstractmethod
    def extract(self, source: str) -> Iterator[ExtractedContent]:
        """
        Extrait le contenu d'une source.
        
        Args:
            source: Identifiant de la source (URL, chemin, etc.).
            
        Yields:
            ExtractedContent: Contenu extrait avec métadonnées.
        """
        pass
    
    def to_document(self, extracted: ExtractedContent) -> DocumentCreate:
        """
        Convertit un contenu extrait en DocumentCreate.
        
        Args:
            extracted: Contenu extrait par le provider.
            
        Returns:
            DocumentCreate prêt pour vectorisation.
        """
        return DocumentCreate(
            content=extracted.content,
            source_type=self.source_type,
            source_id=extracted.source_id,
            metadata=DocumentMetadata(**extracted.metadata),
        )
    
    def extract_all(self, sources: list[str]) -> Iterator[DocumentCreate]:
        """
        Extrait et convertit plusieurs sources.
        
        Args:
            sources: Liste d'identifiants de sources.
            
        Yields:
            DocumentCreate pour chaque contenu extrait.
        """
        for source in sources:
            try:
                for extracted in self.extract(source):
                    yield self.to_document(extracted)
            except Exception as e:
                self.logger.error(
                    "Extraction failed",
                    source=source,
                    error=str(e),
                )
                continue
