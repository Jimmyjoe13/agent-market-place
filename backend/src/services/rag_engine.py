"""
RAG Engine (Legacy Facade)
===========================

Ce fichier est conservé pour la rétro-compatibilité.

Pour les nouveaux développements, utilisez directement :
    from src.services.rag import RAGEngine, RAGConfig, RAGResponse

Architecture refactorisée (janvier 2026) :
- src/services/rag/config.py    : Dataclasses de configuration
- src/services/rag/retriever.py : Recherche vectorielle et web
- src/services/rag/generator.py : Génération LLM multi-provider
- src/services/rag/engine.py    : Orchestration principale

Ce fichier re-exporte les classes principales pour maintenir la compatibilité
avec les imports existants :
    from src.services.rag_engine import RAGEngine, RAGConfig, RAGResponse
"""

# Re-export depuis le nouveau module modulaire
from src.services.rag import RAGConfig, RAGEngine, RAGResponse

# Conserver l'export pour la rétro-compatibilité
__all__ = ["RAGConfig", "RAGEngine", "RAGResponse"]
