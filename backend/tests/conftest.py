"""
Configuration pytest.
"""

import secrets

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _generate_test_key(prefix: str = "test") -> str:
    """Génère une clé de test unique pour chaque exécution de test."""
    return f"{prefix}_{secrets.token_hex(16)}"


@pytest.fixture
def mock_settings():
    """Fixture pour les settings mockés avec clés générées dynamiquement."""
    settings = Mock()
    # Clés API générées dynamiquement (jamais de valeurs hardcodées)
    settings.mistral_api_key = _generate_test_key("mistral")
    settings.supabase_url = "https://test.supabase.co"
    settings.supabase_anon_key = _generate_test_key("anon")
    settings.supabase_service_role_key = _generate_test_key("service")
    settings.perplexity_api_key = _generate_test_key("perplexity")
    settings.github_access_token = _generate_test_key("github")
    settings.openai_api_key = _generate_test_key("openai")
    settings.gemini_api_key = _generate_test_key("gemini")
    settings.deepseek_api_key = _generate_test_key("deepseek")
    # Configuration non-sensible
    settings.embedding_model = "mistral-embed"
    settings.embedding_dimension = 1024
    settings.similarity_threshold = 0.7
    settings.max_results = 10
    settings.llm_model = "mistral-large-latest"
    settings.llm_temperature = 0.7
    settings.llm_max_tokens = 4096
    settings.log_level = "INFO"
    settings.app_env = "development"
    settings.is_development = True
    settings.is_production = False
    settings.default_llm_provider = "mistral"
    return settings


@pytest.fixture
def sample_document_content():
    """Fixture pour un contenu de document exemple."""
    return """
# Mon CV

## Compétences
- Python
- FastAPI
- Machine Learning

## Expérience
Développeur Senior chez Example Corp
    """


@pytest.fixture
def sample_embedding():
    """Fixture pour un embedding exemple (1024 dimensions)."""
    return [0.1] * 1024


@pytest.fixture
def mock_llm_response():
    """Fixture pour une réponse LLM mockée."""
    from src.providers.llm import LLMResponse
    
    return LLMResponse(
        content="This is a test response from the LLM.",
        tokens_input=50,
        tokens_output=25,
        thought_process=None,
        model_used="mistral-large-latest",
    )


@pytest.fixture
def mock_llm_response_with_reflection():
    """Fixture pour une réponse LLM avec réflexion."""
    from src.providers.llm import LLMResponse
    
    return LLMResponse(
        content="The answer is 42, after careful analysis.",
        tokens_input=100,
        tokens_output=50,
        thought_process="Let me think step by step:\n1. First, I analyze the question\n2. Then, I formulate a response",
        model_used="mistral-large-latest",
    )


@pytest.fixture
def sample_messages():
    """Fixture pour des messages de conversation exemple."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"},
    ]


@pytest.fixture
def sample_routing_queries():
    """Fixture pour des requêtes de test du routage."""
    return {
        "greetings": ["bonjour", "hello", "salut", "hey"],
        "documents": ["mon CV", "mes documents", "dans mes fichiers"],
        "web": ["actualité", "dernières nouvelles", "météo demain"],
        "general": ["qu'est-ce que Python?", "explique-moi", "comment faire"],
    }

