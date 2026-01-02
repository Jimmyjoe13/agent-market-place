"""
LLM Provider Factory
=====================

Factory pour créer et gérer les providers LLM.
Implémente le pattern Factory + Strategy pour le switching dynamique.
"""

from src.config.logging_config import get_logger
from src.config.settings import get_settings

from .base_llm import BaseLLMProvider, LLMConfig, LLMProvider

logger = get_logger(__name__)

# Registry des providers disponibles
_PROVIDER_REGISTRY: dict[LLMProvider, type[BaseLLMProvider]] = {}


def register_provider(provider_type: LLMProvider):
    """Décorateur pour enregistrer un provider."""

    def decorator(cls: type[BaseLLMProvider]):
        _PROVIDER_REGISTRY[provider_type] = cls
        return cls

    return decorator


class LLMProviderFactory:
    """
    Factory pour créer des instances de providers LLM.

    Supporte le switching dynamique basé sur:
    - Configuration par défaut
    - Clé API utilisateur (BYOK - Bring Your Own Key)
    - Sélection explicite

    Usage:
        factory = LLMProviderFactory()
        provider = factory.get_provider(LLMProvider.MISTRAL)
        response = await provider.generate(messages)
    """

    def __init__(self) -> None:
        """Initialise la factory."""
        self._cache: dict[str, BaseLLMProvider] = {}
        self._register_all_providers()

    def _register_all_providers(self) -> None:
        """Enregistre tous les providers disponibles."""
        # Import et enregistrement des providers
        from .mistral_provider import MistralLLMProvider

        _PROVIDER_REGISTRY[LLMProvider.MISTRAL] = MistralLLMProvider

        try:
            from .openai_provider import OpenAILLMProvider

            _PROVIDER_REGISTRY[LLMProvider.OPENAI] = OpenAILLMProvider
        except ImportError:
            logger.debug("OpenAI provider not available")

        try:
            from .gemini_provider import GeminiLLMProvider

            _PROVIDER_REGISTRY[LLMProvider.GEMINI] = GeminiLLMProvider
        except ImportError:
            logger.debug("Gemini provider not available")

        try:
            from .deepseek_provider import DeepseekLLMProvider

            _PROVIDER_REGISTRY[LLMProvider.DEEPSEEK] = DeepseekLLMProvider
        except ImportError:
            logger.debug("Deepseek provider not available")

    @property
    def available_providers(self) -> list[LLMProvider]:
        """Liste des providers disponibles."""
        return list(_PROVIDER_REGISTRY.keys())

    def get_provider(
        self,
        provider_type: LLMProvider | str | None = None,
        config: LLMConfig | None = None,
        cache: bool = True,
        api_key: str | None = None,
    ) -> BaseLLMProvider:
        """
        Récupère ou crée un provider.

        Args:
            provider_type: Type de provider (défaut depuis config).
            config: Configuration personnalisée.
            cache: Utiliser le cache d'instances.

        Returns:
            Instance du provider.

        Raises:
            ValueError: Si le provider n'existe pas.
        """
        # Résoudre le type de provider
        if provider_type is None:
            settings = get_settings()
            provider_type = getattr(settings, "default_llm_provider", "mistral")

        if isinstance(provider_type, str):
            try:
                provider_type = LLMProvider(provider_type.lower())
            except ValueError:
                raise ValueError(f"Unknown provider: {provider_type}")

        # Vérifier si disponible
        if provider_type not in _PROVIDER_REGISTRY:
            raise ValueError(
                f"Provider {provider_type} not available. "
                f"Available: {list(_PROVIDER_REGISTRY.keys())}"
            )

        # Cache key
        cache_key = f"{provider_type.value}:{config.model if config else 'default'}:{hash(api_key)}"

        # Retourner du cache si disponible
        if cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Créer nouvelle instance
        provider_class = _PROVIDER_REGISTRY[provider_type]
        provider = provider_class(config, api_key=api_key)

        # Mettre en cache
        if cache:
            self._cache[cache_key] = provider

        logger.info(
            "LLM provider created",
            provider=provider_type.value,
            model=config.model if config else "default",
        )

        return provider

    def get_router_provider(self) -> BaseLLMProvider:
        """
        Récupère un provider rapide pour le routage intelligent.

        Utilise un modèle économique/rapide comme Mistral-tiny ou GPT-3.5.

        Returns:
            Provider configuré pour le routage.
        """
        # Essayer Mistral-tiny d'abord (le plus rapide)
        try:
            config = LLMConfig(
                model="mistral-tiny",
                temperature=0.0,  # Déterministe pour le routage
                max_tokens=100,  # Réponse courte
            )
            return self.get_provider(LLMProvider.MISTRAL, config, cache=True)
        except Exception:
            pass

        # Fallback sur GPT-3.5
        try:
            config = LLMConfig(
                model="gpt-3.5-turbo",
                temperature=0.0,
                max_tokens=100,
            )
            return self.get_provider(LLMProvider.OPENAI, config, cache=True)
        except Exception:
            pass

        # Dernier recours : provider par défaut
        return self.get_provider()

    def clear_cache(self) -> None:
        """Vide le cache des providers."""
        self._cache.clear()


# Singleton de la factory
_factory: LLMProviderFactory | None = None


def get_llm_provider(
    provider_type: LLMProvider | str | None = None,
    config: LLMConfig | None = None,
    api_key: str | None = None,
) -> BaseLLMProvider:
    """
    Fonction utilitaire pour récupérer un provider.

    Args:
        provider_type: Type de provider.
        config: Configuration optionnelle.

    Returns:
        Instance du provider.
    """
    global _factory
    if _factory is None:
        _factory = LLMProviderFactory()

    return _factory.get_provider(provider_type, config, api_key=api_key)


def get_provider_factory() -> LLMProviderFactory:
    """Récupère le singleton de la factory."""
    global _factory
    if _factory is None:
        _factory = LLMProviderFactory()
    return _factory
