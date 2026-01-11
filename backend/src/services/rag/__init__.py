"""
RAG Services Module
====================

Module modulaire pour le système RAG (Retrieval-Augmented Generation).
Architecture refactorisée pour une meilleure maintenabilité.

Modules:
- config: Dataclasses de configuration et réponse
- retriever: Recherche vectorielle et web
- generator: Génération LLM avec support multi-provider
- engine: Orchestration principale
"""

from src.services.rag.config import RAGConfig, RAGResponse
from src.services.rag.retriever import RAGRetriever, RetrievalResult
from src.services.rag.generator import RAGGenerator
from src.services.rag.engine import RAGEngine

__all__ = [
    "RAGConfig",
    "RAGResponse",
    "RAGRetriever",
    "RetrievalResult",
    "RAGGenerator",
    "RAGEngine",
]
