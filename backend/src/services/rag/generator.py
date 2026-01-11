"""
RAG Generator
==============

Responsable de la génération de réponses via les providers LLM.
Supporte le multi-provider (Mistral, OpenAI, Gemini, DeepSeek) et le fallback automatique.
"""

from src.config.logging_config import LoggerMixin
from src.providers.llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderFactory,
)
from src.repositories.user_repository import UserRepository
from src.services.rag.config import RAGConfig


class RAGGenerator(LoggerMixin):
    """
    Gestionnaire de génération LLM pour le RAG.

    Responsabilités :
    - Sélection du provider LLM (avec BYOK)
    - Construction des messages avec mémoire
    - Gestion du fallback en cas de panne
    """

    # Modèles de secours par provider
    FALLBACK_MODELS = {
        "openai": "gpt-4o-mini",
        "mistral": "mistral-small-latest",
        "anthropic": "claude-3-haiku-20240307",
        "gemini": "gemini-1.5-flash",
        "deepseek": "deepseek-chat",
    }

    def __init__(self, config: RAGConfig) -> None:
        """
        Initialise le generator.

        Args:
            config: Configuration RAG.
        """
        self.config = config
        self._factory = LLMProviderFactory()
        self._user_repo = UserRepository()

    def detect_provider_from_model(self, model_id: str) -> str:
        """
        Détecte le provider à partir du model_id.

        Args:
            model_id: Identifiant du modèle.

        Returns:
            Nom du provider (mistral, openai, gemini, etc.)
        """
        model_lower = model_id.lower()

        if model_lower.startswith("gpt") or model_lower.startswith("o1"):
            return "openai"
        elif model_lower.startswith("deepseek"):
            return "deepseek"
        elif model_lower.startswith("gemini"):
            return "gemini"
        elif model_lower.startswith("claude"):
            return "anthropic"
        else:
            # Default to Mistral
            return "mistral"

    def get_provider(
        self,
        model_id: str | None = None,
        user_id: str | None = None,
        enable_reflection: bool = False,
        stream: bool = False,
    ) -> tuple[BaseLLMProvider, str]:
        """
        Récupère le provider LLM approprié.

        Args:
            model_id: Modèle à utiliser (override config).
            user_id: ID utilisateur pour BYOK.
            enable_reflection: Activer le mode réflexion.
            stream: Mode streaming.

        Returns:
            Tuple (Provider LLM configuré, type du provider).
        """
        current_model = model_id or self.config.llm_model
        provider_type = self.detect_provider_from_model(current_model)

        self.logger.info(
            "Selecting LLM provider",
            requested_model_id=model_id,
            config_model=self.config.llm_model,
            selected_model=current_model,
            provider_type=provider_type,
        )

        # Récupérer les clés BYOK si disponibles
        user_keys = {}
        if user_id:
            user_keys = self._user_repo.get_decrypted_provider_keys(user_id)

        provider_api_key = user_keys.get(provider_type)

        llm_config = LLMConfig(
            model=current_model,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            enable_reflection=enable_reflection,
            stream=stream,
        )

        provider = self._factory.get_provider(
            provider_type, llm_config, cache=False, api_key=provider_api_key
        )

        return provider, provider_type

    def get_fallback_provider(
        self,
        current_provider_type: str,
        user_id: str | None = None,
    ) -> BaseLLMProvider:
        """
        Récupère un provider de secours en cas de panne.

        Args:
            current_provider_type: Type du provider actuel (en panne).
            user_id: ID utilisateur pour BYOK.

        Returns:
            Provider LLM de secours.
        """
        # Utiliser Mistral comme fallback universel, sauf si déjà sur Mistral
        fallback_type = "openai" if current_provider_type == "mistral" else "mistral"
        fallback_model = self.FALLBACK_MODELS.get(fallback_type, "gpt-4o-mini")

        self.logger.info(
            "Getting fallback provider",
            current=current_provider_type,
            fallback=fallback_type,
        )

        user_keys = {}
        if user_id:
            user_keys = self._user_repo.get_decrypted_provider_keys(user_id)

        api_key = user_keys.get(fallback_type)

        llm_config = LLMConfig(
            model=fallback_model,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
        )

        return self._factory.get_provider(
            fallback_type, llm_config, cache=False, api_key=api_key
        )

    def build_messages(
        self,
        question: str,
        memory: list[dict[str, str]] | None = None,
        context: str | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Construit les messages LLM avec injection de la mémoire conversationnelle.

        Structure des messages:
        1. System prompt
        2. Mémoire (historique des échanges précédents)
        3. Contexte RAG/Web + Question utilisateur

        Args:
            question: Question de l'utilisateur.
            memory: Historique des messages précédents.
            context: Contexte RAG/Web fusionné.
            system_prompt: Prompt système personnalisé.

        Returns:
            Liste de messages formatés pour le LLM.
        """
        messages: list[dict[str, str]] = []

        # 1. System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. Mémoire conversationnelle (historique)
        if memory:
            messages.extend(memory)

        # 3. Contexte RAG/Web + Question utilisateur
        user_content = question
        if context:
            user_content = f"""Contexte disponible:
{context}

Question de l'utilisateur: {question}"""

        messages.append({"role": "user", "content": user_content})

        return messages
