"""
Document Repository
====================

Repository pour la gestion des documents vectorisés dans Supabase.
"""

import hashlib
from typing import Any
from uuid import UUID

from src.models.document import Document, DocumentCreate, DocumentMatch, SourceType
from src.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """
    Repository pour les opérations CRUD sur les documents.
    
    Gère le stockage et la recherche vectorielle des documents.
    """
    
    def __init__(self) -> None:
        """Initialise le repository documents."""
        super().__init__("documents")
    
    def get_by_id(self, id: str) -> Document | None:
        """
        Récupère un document par son ID.
        
        Args:
            id: UUID du document.
            
        Returns:
            Document ou None si non trouvé.
        """
        try:
            response = self.table.select("*").eq("id", id).single().execute()
            if response.data:
                return Document(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching document", id=id, error=str(e))
            return None
    
    def create(self, data: dict[str, Any]) -> Document:
        """
        Crée un nouveau document.
        
        Args:
            data: Données du document incluant l'embedding.
            
        Returns:
            Document créé.
        """
        # Calcul du hash pour déduplication
        if "content" in data and "content_hash" not in data:
            data["content_hash"] = self._compute_hash(data["content"])
        
        response = self.table.insert(data).execute()
        self.logger.info("Document created", id=response.data[0]["id"])
        return Document(**response.data[0])
    
    def delete(self, id: str) -> bool:
        """
        Supprime un document.
        
        Args:
            id: UUID du document.
            
        Returns:
            True si supprimé avec succès.
        """
        try:
            self.table.delete().eq("id", id).execute()
            self.logger.info("Document deleted", id=id)
            return True
        except Exception as e:
            self.logger.error("Error deleting document", id=id, error=str(e))
            return False
    
    def create_from_model(
        self,
        doc: DocumentCreate,
        embedding: list[float],
        user_id: str | None = None,
        api_key_id: str | None = None,
    ) -> Document:
        """
        Crée un document à partir d'un modèle Pydantic.
        
        Args:
            doc: Modèle DocumentCreate.
            embedding: Vecteur d'embedding.
            user_id: ID de l'utilisateur (multi-tenant).
            api_key_id: ID de la clé API/agent propriétaire.
            
        Returns:
            Document créé.
        """
        data = {
            "content": doc.content,
            "embedding": embedding,
            "source_type": doc.source_type.value,
            "source_id": doc.source_id,
            "metadata": doc.metadata.model_dump(),
            "content_hash": self._compute_hash(doc.content),
        }
        
        if user_id:
            data["user_id"] = user_id
        
        if api_key_id:
            data["api_key_id"] = api_key_id
            
        return self.create(data)
    
    def search_similar(
        self,
        query_embedding: list[float],
        threshold: float = 0.7,
        limit: int = 10,
        source_type: SourceType | None = None,
        user_id: str | None = None,
        api_key_id: str | None = None,
    ) -> list[DocumentMatch]:
        """
        Recherche par similarité cosinus.
        
        Args:
            query_embedding: Vecteur de la requête.
            threshold: Seuil de similarité minimum.
            limit: Nombre maximum de résultats.
            source_type: Filtrer par type de source.
            user_id: Filtrer par utilisateur (multi-tenant, déprécié).
            api_key_id: Filtrer par agent/clé API (isolation documents).
            
        Returns:
            Liste des documents correspondants avec score.
        """
        try:
            params = {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            }
            if source_type:
                params["filter_source_type"] = source_type.value
            
            if user_id:
                params["filter_user_id"] = user_id
            
            if api_key_id:
                params["filter_api_key_id"] = api_key_id
            
            response = self.client.rpc("match_documents", params).execute()
            
            return [DocumentMatch(**doc) for doc in response.data]
        except Exception as e:
            self.logger.error("Search error", error=str(e))
            return []
    
    def get_by_source(
        self,
        source_type: SourceType,
        source_id: str | None = None,
    ) -> list[Document]:
        """
        Récupère les documents par source.
        
        Args:
            source_type: Type de source.
            source_id: ID spécifique de la source.
            
        Returns:
            Liste des documents.
        """
        query = self.table.select("*").eq("source_type", source_type.value)
        if source_id:
            query = query.eq("source_id", source_id)
        
        response = query.execute()
        return [Document(**doc) for doc in response.data]
    
    def exists_by_hash(self, content: str) -> bool:
        """
        Vérifie si un document existe déjà.
        
        Args:
            content: Contenu à vérifier.
            
        Returns:
            True si le document existe.
        """
        content_hash = self._compute_hash(content)
        response = (
            self.table.select("id")
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
        )
        return len(response.data) > 0
    
    @staticmethod
    def _compute_hash(content: str) -> str:
        """Calcule le hash SHA-256 du contenu."""
        return hashlib.sha256(content.encode()).hexdigest()
