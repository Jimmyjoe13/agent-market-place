"""
Document Models
================

Modèles Pydantic pour les documents vectorisés du système RAG.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """Types de sources de documents supportés."""
    
    GITHUB = "github"
    PDF = "pdf"
    LINKEDIN = "linkedin"
    MANUAL = "manual"
    CONVERSATION = "conversation"


class DocumentMetadata(BaseModel):
    """
    Métadonnées flexibles pour un document.
    
    Attributes:
        title: Titre du document (optionnel).
        author: Auteur du document (optionnel).
        url: URL source du document (optionnel).
        file_path: Chemin du fichier original (optionnel).
        language: Langue du contenu (optionnel).
        tags: Tags pour catégorisation (optionnel).
        extra: Données additionnelles (optionnel).
    """
    
    title: str | None = Field(default=None, description="Titre du document")
    author: str | None = Field(default=None, description="Auteur du document")
    url: str | None = Field(default=None, description="URL source")
    file_path: str | None = Field(default=None, description="Chemin du fichier")
    language: str = Field(default="fr", description="Langue du contenu")
    tags: list[str] = Field(default_factory=list, description="Tags de catégorisation")
    extra: dict[str, Any] = Field(default_factory=dict, description="Données additionnelles")
    
    model_config = {"extra": "allow"}


class DocumentCreate(BaseModel):
    """
    Schéma pour la création d'un nouveau document.
    
    Attributes:
        content: Contenu textuel du document.
        source_type: Type de source (github, pdf, etc.).
        source_id: Identifiant unique de la source.
        metadata: Métadonnées du document.
    """
    
    content: str = Field(
        ...,
        description="Contenu textuel du document",
        min_length=1,
        max_length=100000,
    )
    source_type: SourceType = Field(
        ...,
        description="Type de source du document",
    )
    source_id: str | None = Field(
        default=None,
        description="Identifiant unique de la source",
        max_length=500,
    )
    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
        description="Métadonnées du document",
    )
    
    @field_validator("content")
    @classmethod
    def clean_content(cls, v: str) -> str:
        """Nettoie le contenu en supprimant les espaces superflus."""
        return " ".join(v.split())


class Document(DocumentCreate):
    """
    Modèle complet d'un document avec embedding.
    
    Étend DocumentCreate avec les champs générés par le système.
    
    Attributes:
        id: Identifiant unique UUID du document.
        embedding: Vecteur d'embedding (optionnel lors de la lecture).
        content_hash: Hash SHA-256 du contenu pour déduplication.
        created_at: Date de création.
        updated_at: Date de dernière modification.
    """
    
    id: UUID = Field(..., description="Identifiant unique du document")
    embedding: list[float] | None = Field(
        default=None,
        description="Vecteur d'embedding (1024 dimensions)",
    )
    content_hash: str | None = Field(
        default=None,
        description="Hash SHA-256 du contenu",
        max_length=64,
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date de création",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date de dernière modification",
    )
    
    model_config = {"from_attributes": True}


class DocumentMatch(BaseModel):
    """
    Résultat d'une recherche par similarité.
    
    Attributes:
        id: Identifiant du document.
        content: Contenu du document.
        metadata: Métadonnées du document.
        source_type: Type de source.
        source_id: Identifiant de la source.
        similarity: Score de similarité (0-1).
        created_at: Date de création.
    """
    
    id: UUID = Field(..., description="Identifiant du document")
    content: str = Field(..., description="Contenu du document")
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: SourceType = Field(..., description="Type de source")
    source_id: str | None = Field(default=None)
    similarity: float = Field(
        ...,
        description="Score de similarité cosinus",
        ge=0.0,
        le=1.0,
    )
    created_at: datetime = Field(..., description="Date de création")
    
    model_config = {"from_attributes": True}


class DocumentStats(BaseModel):
    """
    Statistiques sur les documents.
    
    Attributes:
        total_documents: Nombre total de documents.
        documents_by_source: Répartition par type de source.
        avg_content_length: Longueur moyenne du contenu.
        last_updated: Date de dernière mise à jour.
    """
    
    total_documents: int = Field(..., ge=0)
    documents_by_source: dict[str, int] = Field(default_factory=dict)
    avg_content_length: float = Field(..., ge=0)
    last_updated: datetime | None = Field(default=None)
