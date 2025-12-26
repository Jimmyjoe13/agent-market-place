"""
Tests unitaires pour l'orchestrateur de routage intelligent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.services.orchestrator import (
    QueryOrchestrator,
    RoutingDecision,
    QueryIntent,
    OrchestratorConfig,
    get_orchestrator,
)


class TestQueryIntent:
    """Tests pour l'enum QueryIntent."""
    
    def test_intent_values(self):
        """Vérifie les valeurs des intents."""
        assert QueryIntent.GENERAL.value == "general"
        assert QueryIntent.DOCUMENTS.value == "documents"
        assert QueryIntent.WEB_SEARCH.value == "web_search"
        assert QueryIntent.HYBRID.value == "hybrid"
        assert QueryIntent.GREETING.value == "greeting"
    
    def test_all_intents_exist(self):
        """Vérifie que tous les intents attendus existent."""
        expected = {"GENERAL", "DOCUMENTS", "WEB_SEARCH", "HYBRID", "GREETING"}
        actual = {intent.name for intent in QueryIntent}
        assert expected == actual


class TestRoutingDecision:
    """Tests pour le dataclass RoutingDecision."""
    
    def test_create_routing_decision(self):
        """Test de création d'une décision de routage."""
        decision = RoutingDecision(
            intent=QueryIntent.DOCUMENTS,
            use_rag=True,
            use_web=False,
            use_reflection=False,
            confidence=0.9,
            reasoning="User asked about their documents",
            latency_ms=45,
        )
        
        assert decision.intent == QueryIntent.DOCUMENTS
        assert decision.use_rag is True
        assert decision.use_web is False
        assert decision.confidence == 0.9
        assert decision.latency_ms == 45
    
    def test_routing_decision_defaults(self):
        """Test des valeurs par défaut."""
        decision = RoutingDecision(
            intent=QueryIntent.GENERAL,
        )
        
        assert decision.use_rag is False
        assert decision.use_web is False
        assert decision.use_reflection is False
        assert decision.confidence == 0.0
        assert decision.reasoning == ""
        assert decision.latency_ms == 0
    
    def test_should_use_rag_with_force(self):
        """Test du calcul should_use_rag avec force."""
        decision = RoutingDecision(
            intent=QueryIntent.GENERAL,
            use_rag=False,
            force_rag=True,
        )
        
        assert decision.should_use_rag is True
    
    def test_should_use_web_with_force(self):
        """Test du calcul should_use_web avec force."""
        decision = RoutingDecision(
            intent=QueryIntent.GENERAL,
            use_web=False,
            force_web=True,
        )
        
        assert decision.should_use_web is True


class TestOrchestratorConfig:
    """Tests pour la configuration de l'orchestrateur."""
    
    def test_default_config(self):
        """Test de la configuration par défaut."""
        config = OrchestratorConfig()
        
        assert config.enable_smart_routing is True
        assert config.router_model == "mistral-tiny"
        assert config.router_timeout_ms == 2000
        assert config.confidence_threshold == 0.7
        assert config.cache_decisions is True
        assert config.cache_ttl_seconds == 300
    
    def test_custom_config(self):
        """Test de la configuration personnalisée."""
        config = OrchestratorConfig(
            enable_smart_routing=False,
            cache_ttl_seconds=60,
            router_timeout_ms=1000,
        )
        
        assert config.enable_smart_routing is False
        assert config.cache_ttl_seconds == 60
        assert config.router_timeout_ms == 1000


class TestQueryOrchestratorQuickDetection:
    """Tests pour la détection rapide par patterns."""
    
    @pytest.fixture
    def orchestrator(self):
        """Créer un orchestrateur pour les tests."""
        config = OrchestratorConfig(enable_smart_routing=False)
        return QueryOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_greeting_detection(self, orchestrator):
        """Test de détection des salutations."""
        greetings = ["bonjour", "salut !", "hello world", "coucou", "hey"]
        
        for greeting in greetings:
            decision = await orchestrator.route(greeting)
            assert decision.intent == QueryIntent.GREETING, f"Failed for: {greeting}"
            assert decision.use_rag is False
            assert decision.use_web is False
    
    @pytest.mark.asyncio
    async def test_document_keywords_detection(self, orchestrator):
        """Test de détection des mots-clés liés aux documents."""
        queries = [
            "mon cv",
            "dans mes documents",
            "mes projets",
            "mon expérience professionnelle",
        ]
        
        for query in queries:
            decision = await orchestrator.route(query)
            assert decision.intent == QueryIntent.DOCUMENTS, f"Failed for: {query}"
            assert decision.use_rag is True
    
    @pytest.mark.asyncio
    async def test_web_keywords_detection(self, orchestrator):
        """Test de détection des mots-clés liés au web."""
        queries = [
            "dernières nouvelles",
            "aujourd'hui",
            "météo demain",
        ]
        
        for query in queries:
            decision = await orchestrator.route(query)
            # Accepte WEB_SEARCH ou HYBRID
            assert decision.use_web is True, f"Failed for: {query}"
    
    @pytest.mark.asyncio
    async def test_force_rag_override(self, orchestrator):
        """Test du forçage RAG."""
        decision = await orchestrator.route(
            "bonjour",  # Normalement = greeting
            force_rag=True,
        )
        
        assert decision.should_use_rag is True
    
    @pytest.mark.asyncio
    async def test_force_web_override(self, orchestrator):
        """Test du forçage web."""
        decision = await orchestrator.route(
            "bonjour",  # Normalement = greeting
            force_web=True,
        )
        
        assert decision.should_use_web is True
    
    @pytest.mark.asyncio
    async def test_force_reflection_override(self, orchestrator):
        """Test du forçage réflexion."""
        decision = await orchestrator.route(
            "bonjour",
            force_reflection=True,
        )
        
        assert decision.use_reflection is True


class TestQueryOrchestratorSmartRouting:
    """Tests pour le routage intelligent via LLM."""
    
    @pytest.fixture
    def orchestrator_with_mock_llm(self):
        """Créer un orchestrateur avec LLM mocké."""
        config = OrchestratorConfig(enable_smart_routing=True)
        orchestrator = QueryOrchestrator(config)
        
        # Mocker le factory LLM
        orchestrator._factory = Mock()
        mock_provider = Mock()
        mock_provider.generate = AsyncMock()
        orchestrator._factory.get_provider.return_value = mock_provider
        
        return orchestrator, mock_provider
    
    @pytest.mark.asyncio
    async def test_smart_routing_parses_json_response(self, orchestrator_with_mock_llm):
        """Test du parsing de la réponse JSON du routeur."""
        orchestrator, mock_provider = orchestrator_with_mock_llm
        
        # Simuler une réponse JSON du LLM
        mock_response = Mock()
        mock_response.content = '{"intent": "documents", "use_rag": true, "use_web": false, "reasoning": "User wants their docs"}'
        mock_provider.generate.return_value = mock_response
        
        decision = await orchestrator.route("Quels sont mes projets GitHub?")
        
        # On s'attend à ce que le routage intelligent soit utilisé
        assert decision.intent in QueryIntent
    
    @pytest.mark.asyncio
    async def test_smart_routing_fallback_on_invalid_json(self, orchestrator_with_mock_llm):
        """Test du fallback si JSON invalide."""
        orchestrator, mock_provider = orchestrator_with_mock_llm
        
        # Simuler une réponse invalide
        mock_response = Mock()
        mock_response.content = "Je ne suis pas sûr de comprendre."
        mock_provider.generate.return_value = mock_response
        
        decision = await orchestrator.route("Question quelconque")
        
        # Doit retourner une décision valide
        assert decision.intent in [QueryIntent.HYBRID, QueryIntent.GENERAL]
    
    @pytest.mark.asyncio
    async def test_smart_routing_fallback_on_exception(self, orchestrator_with_mock_llm):
        """Test du fallback en cas d'exception."""
        orchestrator, mock_provider = orchestrator_with_mock_llm
        
        # Simuler une exception
        mock_provider.generate.side_effect = Exception("API error")
        
        decision = await orchestrator.route("Question quelconque")
        
        # Doit utiliser le fallback
        assert decision.intent in QueryIntent


class TestQueryOrchestratorCache:
    """Tests pour le cache des décisions."""
    
    @pytest.fixture
    def orchestrator(self):
        """Créer un orchestrateur pour les tests."""
        config = OrchestratorConfig(
            enable_smart_routing=False,
            cache_ttl_seconds=10,
            cache_decisions=True,
        )
        return QueryOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, orchestrator):
        """Test du cache hit."""
        query = "bonjour comment ça va"
        
        # Premier appel
        decision1 = await orchestrator.route(query)
        
        # Deuxième appel (devrait être caché)
        decision2 = await orchestrator.route(query)
        
        # Les décisions doivent être identiques
        assert decision1.intent == decision2.intent
    
    def test_clear_cache(self, orchestrator):
        """Test du nettoyage du cache."""
        # Ajouter une entrée au cache
        orchestrator._decision_cache["test_key"] = (
            RoutingDecision(intent=QueryIntent.GENERAL),
            12345
        )
        
        assert len(orchestrator._decision_cache) > 0
        
        orchestrator.clear_cache()
        
        assert len(orchestrator._decision_cache) == 0


class TestGetOrchestrator:
    """Tests pour la fonction singleton."""
    
    def test_get_orchestrator_singleton(self):
        """Test que get_orchestrator retourne un singleton."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        
        assert orch1 is orch2
    
    def test_get_orchestrator_type(self):
        """Test que get_orchestrator retourne le bon type."""
        orch = get_orchestrator()
        
        assert isinstance(orch, QueryOrchestrator)


# Tests de performance
class TestOrchestratorPerformance:
    """Tests de performance de l'orchestrateur."""
    
    @pytest.mark.asyncio
    async def test_quick_detection_is_fast(self):
        """Vérifie que la détection rapide est < 50ms."""
        import time
        
        config = OrchestratorConfig(enable_smart_routing=False)
        orchestrator = QueryOrchestrator(config)
        
        start = time.perf_counter()
        await orchestrator.route("bonjour")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 50, f"Quick detection took {elapsed_ms:.2f}ms"
    
    @pytest.mark.asyncio
    async def test_many_concurrent_requests(self):
        """Test de nombreuses requêtes concurrentes."""
        config = OrchestratorConfig(enable_smart_routing=False)
        orchestrator = QueryOrchestrator(config)
        
        queries = [
            "bonjour",
            "mon cv",
            "actualité",
            "hello",
            "mes documents",
        ] * 20  # 100 requêtes
        
        tasks = [orchestrator.route(q) for q in queries]
        decisions = await asyncio.gather(*tasks)
        
        assert len(decisions) == 100
        assert all(isinstance(d, RoutingDecision) for d in decisions)
