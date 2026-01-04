"""
Orchestrator Service
=====================

Orchestrateur intelligent pour le routage des requêtes.
Analyse l'intention et décide du chemin optimal :
- Chemin A (Direct) : LLM seul pour questions générales
- Chemin B (RAG) : Recherche vectorielle + LLM pour docs privés
- Chemin C (Web) : Recherche web + LLM pour actualités

Objectif : Réduire la latence de 60-80% pour les requêtes simples.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum

from src.config.logging_config import LoggerMixin
from src.providers.llm import LLMConfig, LLMProvider, LLMProviderFactory


class QueryIntent(str, Enum):
    """Types d'intentions de requête."""

    GENERAL = "general"  # Question générale -> LLM seul
    DOCUMENTS = "documents"  # Recherche dans docs privés -> RAG
    WEB_SEARCH = "web_search"  # Info récente/actualité -> Web
    HYBRID = "hybrid"  # Combinaison RAG + Web
    GREETING = "greeting"  # Salutation simple -> Réponse rapide


@dataclass
class RoutingDecision:
    """Décision de routage du routeur intelligent."""

    intent: QueryIntent
    use_rag: bool = False
    use_web: bool = False
    use_reflection: bool = False
    confidence: float = 0.0
    reasoning: str = ""
    latency_ms: int = 0

    # Force overrides (depuis l'UI) - active même si le routeur dit non
    force_rag: bool = False
    force_web: bool = False
    
    # Disable overrides (depuis l'UI) - désactive même si le routeur dit oui
    disable_rag: bool = False
    disable_web: bool = False

    @property
    def should_use_rag(self) -> bool:
        # Si explicitement désactivé, ne jamais utiliser
        if self.disable_rag:
            return False
        return self.use_rag or self.force_rag

    @property
    def should_use_web(self) -> bool:
        # Si explicitement désactivé, ne jamais utiliser
        if self.disable_web:
            return False
        return self.use_web or self.force_web


@dataclass
class OrchestratorConfig:
    """Configuration de l'orchestrateur."""

    # Routage
    enable_smart_routing: bool = True
    router_model: str = "mistral-tiny"
    router_timeout_ms: int = 2000

    # Seuils de confiance
    confidence_threshold: float = 0.7

    # Fallback si le routeur échoue
    fallback_use_rag: bool = True
    fallback_use_web: bool = False

    # Cache des décisions
    cache_decisions: bool = True
    cache_ttl_seconds: int = 300


class QueryOrchestrator(LoggerMixin):
    """
    Orchestrateur intelligent de requêtes.

    Analyse l'intention de l'utilisateur pour optimiser
    le chemin de traitement et réduire la latence.
    """

    ROUTER_PROMPT = """Tu es un classificateur de requêtes. Analyse la question et détermine :
1. S'il faut chercher dans des documents privés (CV, projets, notes personnelles)
2. S'il faut chercher sur le web (actualités, infos récentes, données publiques)
3. S'il faut une réflexion approfondie (question complexe nécessitant analyse)

Réponds UNIQUEMENT en JSON valide, sans explication :
{
  "intent": "general|documents|web_search|hybrid|greeting",
  "use_rag": true/false,
  "use_web": true/false,
  "use_reflection": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "courte explication"
}

Question : """

    # Patterns pour détection rapide (sans appel LLM)
    GREETING_PATTERNS = [
        "bonjour",
        "salut",
        "hello",
        "hi",
        "hey",
        "coucou",
        "bonsoir",
        "yo",
        "good morning",
        "good evening",
    ]

    DOCUMENT_KEYWORDS = [
        "mon cv",
        "mon profil",
        "mes projets",
        "mon expérience",
        "mes compétences",
        "mon parcours",
        "dans mes documents",
        "j'ai uploadé",
        "selon mes notes",
        "dans mon fichier",
    ]

    WEB_KEYWORDS = [
        "aujourd'hui",
        "récemment",
        "actualité",
        "dernières nouvelles",
        "en 2024",
        "en 2025",
        "cette année",
        "cette semaine",
        "prix actuel",
        "météo",
        "cours de",
        "latest",
        "recent",
    ]

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        """
        Initialise l'orchestrateur.

        Args:
            config: Configuration optionnelle.
        """
        self.config = config or OrchestratorConfig()
        self._factory = LLMProviderFactory()
        self._decision_cache: dict[str, tuple[RoutingDecision, float]] = {}

    async def route(
        self,
        query: str,
        force_rag: bool = False,
        force_web: bool = False,
        force_reflection: bool = False,
        disable_rag: bool = False,
        disable_web: bool = False,
    ) -> RoutingDecision:
        """
        Détermine le meilleur chemin pour traiter une requête.

        Args:
            query: Question de l'utilisateur.
            force_rag: Forcer l'utilisation du RAG.
            force_web: Forcer la recherche web.
            force_reflection: Forcer le mode réflexion.
            disable_rag: Désactiver explicitement le RAG.
            disable_web: Désactiver explicitement la recherche web.

        Returns:
            RoutingDecision avec le chemin optimal.
        """
        start_time = time.time()
        query_lower = query.lower().strip()

        # 1. Vérifier le cache
        if self.config.cache_decisions:
            cached = self._get_cached_decision(query_lower)
            if cached:
                cached.force_rag = force_rag
                cached.force_web = force_web
                cached.disable_rag = disable_rag
                cached.disable_web = disable_web
                cached.use_reflection = cached.use_reflection or force_reflection
                return cached

        # 2. Détection rapide par patterns (évite l'appel LLM)
        quick_decision = self._quick_detect(query_lower)
        if quick_decision and quick_decision.confidence >= 0.9:
            quick_decision.force_rag = force_rag
            quick_decision.force_web = force_web
            quick_decision.disable_rag = disable_rag
            quick_decision.disable_web = disable_web
            quick_decision.use_reflection = quick_decision.use_reflection or force_reflection
            quick_decision.latency_ms = int((time.time() - start_time) * 1000)
            self._cache_decision(query_lower, quick_decision)
            return quick_decision

        # 3. Routage intelligent via LLM (si activé)
        if self.config.enable_smart_routing:
            try:
                decision = await self._smart_route(query)
                decision.force_rag = force_rag
                decision.force_web = force_web
                decision.disable_rag = disable_rag
                decision.disable_web = disable_web
                decision.use_reflection = decision.use_reflection or force_reflection
                decision.latency_ms = int((time.time() - start_time) * 1000)
                self._cache_decision(query_lower, decision)
                return decision
            except Exception as e:
                self.logger.warning("Smart routing failed, using fallback", error=str(e))

        # 4. Fallback
        return RoutingDecision(
            intent=QueryIntent.HYBRID,
            use_rag=self.config.fallback_use_rag or force_rag,
            use_web=self.config.fallback_use_web or force_web,
            use_reflection=force_reflection,
            confidence=0.5,
            reasoning="Fallback decision",
            latency_ms=int((time.time() - start_time) * 1000),
            force_rag=force_rag,
            force_web=force_web,
            disable_rag=disable_rag,
            disable_web=disable_web,
        )

    def _quick_detect(self, query: str) -> RoutingDecision | None:
        """
        Détection rapide sans appel LLM.

        Args:
            query: Question en minuscules.

        Returns:
            RoutingDecision si détection sûre, None sinon.
        """
        # Salutations
        if any(query.startswith(g) for g in self.GREETING_PATTERNS):
            return RoutingDecision(
                intent=QueryIntent.GREETING,
                use_rag=False,
                use_web=False,
                use_reflection=False,
                confidence=0.95,
                reasoning="Greeting detected",
            )

        # Mots-clés documents personnels
        if any(kw in query for kw in self.DOCUMENT_KEYWORDS):
            return RoutingDecision(
                intent=QueryIntent.DOCUMENTS,
                use_rag=True,
                use_web=False,
                use_reflection=False,
                confidence=0.9,
                reasoning="Personal document keywords detected",
            )

        # Mots-clés recherche web
        if any(kw in query for kw in self.WEB_KEYWORDS):
            return RoutingDecision(
                intent=QueryIntent.WEB_SEARCH,
                use_rag=False,
                use_web=True,
                use_reflection=False,
                confidence=0.85,
                reasoning="Web search keywords detected",
            )

        # Pas de détection sûre
        return None

    async def _smart_route(self, query: str) -> RoutingDecision:
        """
        Routage intelligent via LLM.

        Args:
            query: Question de l'utilisateur.

        Returns:
            RoutingDecision basée sur l'analyse LLM.
        """
        # Utiliser un modèle rapide pour le routage
        router_config = LLMConfig(
            model=self.config.router_model,
            temperature=0.0,  # Déterministe
            max_tokens=150,
        )

        try:
            provider = self._factory.get_provider(
                LLMProvider.MISTRAL,
                router_config,
            )
        except Exception:
            # Fallback sur le provider par défaut
            provider = self._factory.get_provider()

        # Générer la classification
        messages = [{"role": "user", "content": f"{self.ROUTER_PROMPT}{query}"}]

        try:
            # Timeout pour le routage
            response = await asyncio.wait_for(
                provider.generate(messages),
                timeout=self.config.router_timeout_ms / 1000,
            )

            # Parser le JSON
            result = self._parse_router_response(response.content)
            return result

        except asyncio.TimeoutError:
            self.logger.warning("Router timeout, using quick detect or fallback")
            return self._quick_detect(query.lower()) or RoutingDecision(
                intent=QueryIntent.GENERAL,
                use_rag=False,
                use_web=False,
                confidence=0.5,
                reasoning="Router timeout",
            )

    def _parse_router_response(self, content: str) -> RoutingDecision:
        """
        Parse la réponse JSON du routeur.

        Args:
            content: Réponse du LLM.

        Returns:
            RoutingDecision parsée.
        """
        try:
            # Extraire le JSON de la réponse
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)

            intent_str = data.get("intent", "general")
            try:
                intent = QueryIntent(intent_str)
            except ValueError:
                intent = QueryIntent.GENERAL

            return RoutingDecision(
                intent=intent,
                use_rag=data.get("use_rag", False),
                use_web=data.get("use_web", False),
                use_reflection=data.get("use_reflection", False),
                confidence=float(data.get("confidence", 0.7)),
                reasoning=data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning("Failed to parse router response", error=str(e))
            return RoutingDecision(
                intent=QueryIntent.GENERAL,
                use_rag=False,
                use_web=False,
                confidence=0.5,
                reasoning="Parse error",
            )

    def _get_cached_decision(self, query: str) -> RoutingDecision | None:
        """Récupère une décision du cache si valide."""
        if query in self._decision_cache:
            decision, timestamp = self._decision_cache[query]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                self.logger.debug("Cache hit for routing decision")
                return decision
            else:
                del self._decision_cache[query]
        return None

    def _cache_decision(self, query: str, decision: RoutingDecision) -> None:
        """Met en cache une décision."""
        self._decision_cache[query] = (decision, time.time())

        # Nettoyer le cache si trop grand
        if len(self._decision_cache) > 1000:
            # Supprimer les plus anciens
            sorted_items = sorted(
                self._decision_cache.items(),
                key=lambda x: x[1][1],
            )
            self._decision_cache = dict(sorted_items[-500:])

    def clear_cache(self) -> None:
        """Vide le cache des décisions."""
        self._decision_cache.clear()


# Singleton
_orchestrator: QueryOrchestrator | None = None


def get_orchestrator() -> QueryOrchestrator:
    """Récupère le singleton de l'orchestrateur."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = QueryOrchestrator()
    return _orchestrator
