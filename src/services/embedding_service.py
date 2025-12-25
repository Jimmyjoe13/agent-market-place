"""
Embedding Service
==================

Service pour la génération d'embeddings via Mistral AI.
"""

import hashlib
from typing import Any

from mistralai import Mistral
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import get_settings
from src.config.logging_config import LoggerMixin


class EmbeddingService(LoggerMixin):
    """
    Service pour générer des embeddings avec Mistral AI.
    
    Utilise le modèle mistral-embed pour créer des vecteurs
    de 1024 dimensions à partir de texte.
    
    Attributes:
        model: Nom du modèle d'embedding Mistral.
        dimension: Dimension des vecteurs générés.
    """
    
    def __init__(self) -> None:
        """Initialise le service d'embedding."""
        settings = get_settings()
        self._client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def embed_text(self, text: str) -> list[float]:
        """
        Génère un embedding pour un texte.
        
        Args:
            text: Texte à vectoriser.
            
        Returns:
            Vecteur d'embedding (1024 dimensions).
            
        Raises:
            ValueError: Si le texte est vide.
            MistralException: En cas d'erreur API.
        """
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        
        # Tronquer si nécessaire (limite de tokens)
        truncated = self._truncate_text(text, max_tokens=8000)
        
        response = self._client.embeddings.create(
            model=self.model,
            inputs=[truncated],
        )
        
        embedding = response.data[0].embedding
        self.logger.debug(
            "Text embedded",
            text_length=len(text),
            model=self.model,
        )
        
        return embedding
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 25,
    ) -> list[list[float]]:
        """
        Génère des embeddings pour plusieurs textes.
        
        Args:
            texts: Liste de textes à vectoriser.
            batch_size: Taille des batches (max 25).
            
        Returns:
            Liste de vecteurs d'embeddings.
        """
        if not texts:
            return []
        
        all_embeddings: list[list[float]] = []
        
        # Traiter par batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tronquer chaque texte
            truncated = [self._truncate_text(t, 8000) for t in batch]
            
            response = self._client.embeddings.create(
                model=self.model,
                inputs=truncated,
            )
            
            batch_embeddings = [d.embedding for d in response.data]
            all_embeddings.extend(batch_embeddings)
            
            self.logger.debug(
                "Batch embedded",
                batch_num=i // batch_size + 1,
                batch_size=len(batch),
            )
        
        return all_embeddings
    
    def embed_query(self, query: str) -> list[float]:
        """
        Génère un embedding pour une requête de recherche.
        
        Optimisé pour les requêtes courtes.
        
        Args:
            query: Requête de recherche.
            
        Returns:
            Vecteur d'embedding.
        """
        return self.embed_text(query)
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """
        Tronque le texte si nécessaire.
        
        Estimation simple: 1 token ≈ 4 caractères.
        """
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            self.logger.debug(
                "Text truncated",
                original=len(text),
                truncated=max_chars,
            )
            return text[:max_chars]
        return text
    
    @staticmethod
    def compute_similarity(
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings.
        
        Args:
            embedding1: Premier vecteur.
            embedding2: Deuxième vecteur.
            
        Returns:
            Score de similarité entre 0 et 1.
        """
        import math
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
