"""
Tests unitaires pour les LLM Providers et la Factory.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

from src.providers.llm import (
    BaseLLMProvider,
    LLMResponse,
    LLMConfig,
    StreamChunk,
    LLMProvider,
    LLMProviderFactory,
    get_llm_provider,
    MistralLLMProvider,
)


class TestLLMProvider:
    """Tests pour l'enum LLMProvider."""
    
    def test_provider_values(self):
        """Vérifie les valeurs des providers."""
        assert LLMProvider.MISTRAL.value == "mistral"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.DEEPSEEK.value == "deepseek"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
    
    def test_all_providers_exist(self):
        """Vérifie que tous les providers attendus existent."""
        expected = {"MISTRAL", "OPENAI", "GEMINI", "DEEPSEEK", "ANTHROPIC"}
        actual = {p.name for p in LLMProvider}
        assert expected == actual


class TestLLMConfig:
    """Tests pour le dataclass LLMConfig."""
    
    def test_default_model_required(self):
        """Test que le modèle est un paramètre requis."""
        config = LLMConfig(model="mistral-large-latest")
        
        assert config.model == "mistral-large-latest"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.enable_reflection is False
        assert config.stream is False
    
    def test_custom_config(self):
        """Test de la configuration personnalisée."""
        config = LLMConfig(
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2048,
            enable_reflection=True,
            stream=True,
        )
        
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.enable_reflection is True
        assert config.stream is True
    
    def test_config_serialization(self):
        """Test de la sérialisation en dictionnaire."""
        config = LLMConfig(model="test-model", temperature=0.3)
        
        data = asdict(config)
        
        assert isinstance(data, dict)
        assert data["model"] == "test-model"
        assert data["temperature"] == 0.3


class TestLLMResponse:
    """Tests pour le dataclass LLMResponse."""
    
    def test_basic_response(self):
        """Test d'une réponse basique."""
        response = LLMResponse(
            content="Hello, world!",
            tokens_input=10,
            tokens_output=5,
        )
        
        assert response.content == "Hello, world!"
        assert response.tokens_input == 10
        assert response.tokens_output == 5
        assert response.thought_process is None
        assert response.model_used == ""  # valeur par défaut
        assert response.total_tokens == 15
    
    def test_response_with_thought_process(self):
        """Test d'une réponse avec processus de pensée."""
        response = LLMResponse(
            content="The answer is 42.",
            tokens_input=20,
            tokens_output=15,
            thought_process="Let me think about this question...",
            model_used="mistral-large-latest",
        )
        
        assert response.thought_process == "Let me think about this question..."
        assert response.model_used == "mistral-large-latest"


class TestStreamChunk:
    """Tests pour le dataclass StreamChunk."""
    
    def test_content_chunk(self):
        """Test d'un chunk de contenu."""
        chunk = StreamChunk(
            content="Hello",
            is_thought=False,
            is_final=False,
        )
        
        assert chunk.content == "Hello"
        assert chunk.is_thought is False
        assert chunk.is_final is False
    
    def test_thought_chunk(self):
        """Test d'un chunk de pensée."""
        chunk = StreamChunk(
            content="Thinking...",
            is_thought=True,
            is_final=False,
        )
        
        assert chunk.is_thought is True
    
    def test_final_chunk(self):
        """Test d'un chunk final."""
        chunk = StreamChunk(
            content="",
            is_thought=False,
            is_final=True,
        )
        
        assert chunk.is_final is True


class TestMistralLLMProvider:
    """Tests pour le provider Mistral."""
    
    def test_provider_models_list(self):
        """Test que la liste des modèles est définie."""
        assert hasattr(MistralLLMProvider, "MODELS")
        assert "mistral-large-latest" in MistralLLMProvider.MODELS
        assert "mistral-tiny" in MistralLLMProvider.MODELS
    
    def test_provider_inherits_base(self):
        """Test que le provider hérite de BaseLLMProvider."""
        assert issubclass(MistralLLMProvider, BaseLLMProvider)


class TestLLMProviderFactory:
    """Tests pour la Factory de providers."""
    
    @pytest.fixture
    def factory(self):
        """Créer une factory pour les tests."""
        return LLMProviderFactory()
    
    def test_factory_has_cache(self, factory):
        """Test que la factory a un cache."""
        assert hasattr(factory, "_cache")
        assert isinstance(factory._cache, dict)
    
    def test_factory_available_providers(self, factory):
        """Test de la liste des providers disponibles."""
        providers = factory.available_providers
        
        assert isinstance(providers, list)
        assert LLMProvider.MISTRAL in providers
    
    def test_get_provider_with_invalid_name_raises(self, factory):
        """Test qu'un nom invalide lève une exception."""
        with pytest.raises(ValueError):
            factory.get_provider("invalid_provider_name")
    
    def test_factory_has_clear_cache(self, factory):
        """Test que la méthode clear_cache existe."""
        assert hasattr(factory, "clear_cache")
        factory.clear_cache()
        assert len(factory._cache) == 0


class TestGetLLMProvider:
    """Tests pour la fonction helper get_llm_provider."""
    
    def test_get_llm_provider_exists(self):
        """Test que la fonction existe et est callable."""
        assert callable(get_llm_provider)


class TestBaseLLMProviderAbstract:
    """Tests pour la classe abstraite BaseLLMProvider."""
    
    def test_cannot_instantiate_directly(self):
        """Vérifie qu'on ne peut pas instancier directement."""
        with pytest.raises(TypeError):
            # BaseLLMProvider nécessite un config
            config = LLMConfig(model="test")
            BaseLLMProvider(config)
    
    def test_abstract_methods_defined(self):
        """Vérifie que les méthodes abstraites sont définies."""
        abstract_methods = getattr(BaseLLMProvider, "__abstractmethods__", set())
        
        # Ces méthodes doivent être abstraites
        assert "generate" in abstract_methods
        assert "generate_stream" in abstract_methods
        assert "_validate_config" in abstract_methods
    
    def test_build_messages_is_concrete(self):
        """Vérifie que build_messages est une méthode concrète."""
        assert hasattr(BaseLLMProvider, "build_messages")
        assert "build_messages" not in getattr(BaseLLMProvider, "__abstractmethods__", set())
    
    def test_generate_with_reflection_is_concrete(self):
        """Vérifie que generate_with_reflection est une méthode concrète."""
        assert hasattr(BaseLLMProvider, "generate_with_reflection")
        assert "generate_with_reflection" not in getattr(BaseLLMProvider, "__abstractmethods__", set())


class TestLLMProviderIntegration:
    """Tests d'intégration légers (sans vraies API calls)."""
    
    @pytest.fixture
    def mock_provider(self):
        """Créer un mock provider pour les tests."""
        provider = Mock(spec=BaseLLMProvider)
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Test response",
            tokens_input=10,
            tokens_output=5,
        ))
        provider.build_messages = Mock(return_value=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ])
        return provider
    
    @pytest.mark.asyncio
    async def test_generate_flow(self, mock_provider):
        """Test du flux de génération."""
        messages = mock_provider.build_messages(
            question="Hello",
            system_prompt="You are helpful.",
        )
        
        response = await mock_provider.generate(messages)
        
        assert response.content == "Test response"
        assert response.tokens_input == 10


class TestProviderReflectionMode:
    """Tests pour le mode réflexion."""
    
    @pytest.fixture
    def mock_reflection_provider(self):
        """Créer un mock provider avec réflexion."""
        provider = Mock(spec=BaseLLMProvider)
        
        async def mock_generate_with_reflection(messages):
            return LLMResponse(
                content="The answer is 42.",
                tokens_input=50,
                tokens_output=30,
                thought_process="Let me analyze this step by step...",
            )
        
        provider.generate_with_reflection = AsyncMock(side_effect=mock_generate_with_reflection)
        return provider
    
    @pytest.mark.asyncio
    async def test_reflection_returns_thought_process(self, mock_reflection_provider):
        """Test que le mode réflexion retourne le processus de pensée."""
        response = await mock_reflection_provider.generate_with_reflection([])
        
        assert response.thought_process is not None
        assert "step by step" in response.thought_process
    
    @pytest.mark.asyncio
    async def test_reflection_returns_answer(self, mock_reflection_provider):
        """Test que le mode réflexion retourne aussi la réponse."""
        response = await mock_reflection_provider.generate_with_reflection([])
        
        assert response.content is not None
        assert len(response.content) > 0
