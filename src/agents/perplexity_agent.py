"""
Perplexity Agent
=================

Agent de recherche web en temps réel utilisant l'API Perplexity.
Fournit un contexte actualisé pour enrichir les réponses du RAG.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import get_settings
from src.config.logging_config import LoggerMixin


@dataclass
class WebSearchResult:
    """
    Résultat d'une recherche web.
    
    Attributes:
        content: Contenu de la réponse.
        sources: Liste des URLs sources.
        model: Modèle utilisé.
        tokens_used: Nombre de tokens consommés.
    """
    content: str
    sources: list[str]
    model: str
    tokens_used: int


class PerplexityAgent(LoggerMixin):
    """
    Agent de recherche web via Perplexity API.
    
    Permet d'obtenir des informations actualisées du web
    pour enrichir le contexte du RAG.
    
    Attributes:
        api_key: Clé API Perplexity.
        model: Modèle à utiliser (sonar, sonar-pro, etc.).
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Modèles disponibles (mis à jour décembre 2024)
    # Documentation: https://docs.perplexity.ai/getting-started/models
    MODELS = {
        "small": "sonar",                    # Recherche légère et économique
        "large": "sonar-pro",                # Recherche avancée
        "reasoning": "sonar-reasoning-pro",  # Raisonnement avec Chain of Thought
        "research": "sonar-deep-research",   # Recherche approfondie
    }
    
    def __init__(
        self,
        model_size: str = "small",
        timeout: int = 30,
    ) -> None:
        """
        Initialise l'agent Perplexity.
        
        Args:
            model_size: Taille du modèle (small, large, huge).
            timeout: Timeout des requêtes en secondes.
        """
        settings = get_settings()
        self.api_key = settings.perplexity_api_key
        self.model = self.MODELS.get(model_size, self.MODELS["small"])
        self.timeout = timeout
        self._enabled = bool(self.api_key)
        
        if not self._enabled:
            self.logger.warning(
                "Perplexity API key not configured, web search disabled"
            )
    
    @property
    def is_enabled(self) -> bool:
        """Vérifie si l'agent est activé."""
        return self._enabled
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def search(
        self,
        query: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> WebSearchResult | None:
        """
        Effectue une recherche web.
        
        Args:
            query: Question ou requête de recherche.
            system_prompt: Prompt système personnalisé.
            max_tokens: Nombre maximum de tokens en réponse.
            
        Returns:
            WebSearchResult ou None si désactivé/erreur.
        """
        if not self._enabled:
            return None
        
        default_system = """Tu es un assistant de recherche. Donne des réponses courtes et factuelles.

Règles :
- Va droit au but, pas de blabla
- Cite tes sources naturellement dans le texte
- Donne l'info la plus récente et fiable
- Réponds dans la langue de la question"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or default_system},
                {"role": "user", "content": query},
            ],
            "max_tokens": max_tokens,
            "return_citations": True,
            "return_related_questions": False,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            
            # Extraire le contenu
            content = data["choices"][0]["message"]["content"]
            
            # Extraire les sources (citations)
            sources = []
            if "citations" in data:
                sources = data["citations"]
            
            # Tokens utilisés
            tokens = data.get("usage", {}).get("total_tokens", 0)
            
            self.logger.info(
                "Web search completed",
                query_length=len(query),
                sources_count=len(sources),
                tokens=tokens,
            )
            
            return WebSearchResult(
                content=content,
                sources=sources,
                model=self.model,
                tokens_used=tokens,
            )
            
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Perplexity API error",
                status=e.response.status_code,
                detail=e.response.text,
            )
            return None
        except Exception as e:
            self.logger.error("Web search failed", error=str(e))
            return None
    
    def search_sync(
        self,
        query: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> WebSearchResult | None:
        """
        Version synchrone de search.
        
        Args:
            query: Question ou requête.
            system_prompt: Prompt système.
            max_tokens: Tokens maximum.
            
        Returns:
            WebSearchResult ou None.
        """
        if not self._enabled:
            return None
        
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.search(query, system_prompt, max_tokens)
        )
    
    async def search_with_context(
        self,
        query: str,
        context: str,
        max_tokens: int = 1024,
    ) -> WebSearchResult | None:
        """
        Recherche avec contexte additionnel.
        
        Args:
            query: Question principale.
            context: Contexte à prendre en compte.
            max_tokens: Tokens maximum.
            
        Returns:
            WebSearchResult enrichi.
        """
        enriched_query = f"""
Contexte: {context}

Question: {query}

Fournis des informations actualisées et pertinentes en tenant compte du contexte.
"""
        return await self.search(enriched_query, max_tokens=max_tokens)
