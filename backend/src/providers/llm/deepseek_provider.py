"""
Deepseek LLM Provider
======================

Implémentation du provider Deepseek via l'API compatible OpenAI.
Deepseek expose une API 100% compatible avec le SDK OpenAI.

Documentation: https://platform.deepseek.com/api-docs
"""

import time
from collections.abc import AsyncIterator

from src.config.settings import get_settings

from .base_llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    StreamChunk,
)


class DeepseekLLMProvider(BaseLLMProvider):
    """
    Provider Deepseek via API compatible OpenAI.

    Supporte les modèles :
    - deepseek-chat (généraliste, recommandé)
    - deepseek-coder (optimisé code)
    - deepseek-reasoner (raisonnement avancé)

    Note: Utilise le SDK OpenAI avec base_url modifié.
    Aucune dépendance additionnelle requise.
    """

    BASE_URL = "https://api.deepseek.com"

    MODELS = [
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-reasoner",
    ]

    def __init__(self, config: LLMConfig | None = None, api_key: str | None = None) -> None:
        """
        Initialise le provider Deepseek.

        Args:
            config: Configuration optionnelle.
            api_key: Clé API optionnelle (BYOK - Bring Your Own Key).
        """
        settings = get_settings()

        default_config = LLMConfig(
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=4096,
        )

        super().__init__(config or default_config)

        # Import conditionnel pour éviter d'obliger l'installation
        try:
            from openai import AsyncOpenAI

            # Priorité: Clé passée explicitement > Clé du settings
            effective_key = api_key or getattr(settings, "deepseek_api_key", None)
            if not effective_key:
                self.logger.warning("Deepseek API key not configured")
                self._client = None
            else:
                # Utiliser le SDK OpenAI avec base_url Deepseek
                self._client = AsyncOpenAI(
                    api_key=effective_key,
                    base_url=self.BASE_URL,
                )
                self.logger.info("Deepseek provider initialized", base_url=self.BASE_URL)
        except ImportError:
            self.logger.warning("OpenAI package not installed (required for Deepseek)")
            self._client = None

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.DEEPSEEK

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    @property
    def is_available(self) -> bool:
        """Vérifie si le provider est disponible."""
        return self._client is not None

    def _validate_config(self) -> None:
        """Valide la configuration Deepseek."""
        if self.config.model not in self.MODELS:
            self.logger.warning(f"Model {self.config.model} not in known models, using anyway")

        if not (0 <= self.config.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse avec Deepseek.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Returns:
            LLMResponse avec le contenu généré.
        """
        if not self._client:
            raise RuntimeError("Deepseek client not initialized. Check DEEPSEEK_API_KEY.")

        start_time = time.time()

        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=final_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=response.choices[0].message.content or "",
                tokens_input=response.usage.prompt_tokens if response.usage else 0,
                tokens_output=response.usage.completion_tokens if response.usage else 0,
                model_used=self.config.model,
                finish_reason=response.choices[0].finish_reason or "stop",
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.logger.error("Deepseek generation failed", error=str(e), model=self.config.model)
            raise

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Génère une réponse en streaming avec Deepseek.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Yields:
            StreamChunk progressifs.
        """
        if not self._client:
            raise RuntimeError("Deepseek client not initialized. Check DEEPSEEK_API_KEY.")

        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model,
                messages=final_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                stream=True,
            )

            tokens_count = 0
            in_thought_block = False

            async for event in stream:
                if event.choices and event.choices[0].delta.content:
                    chunk_content = event.choices[0].delta.content
                    tokens_count += 1

                    # Détecter les blocs de pensée
                    if "<thought>" in chunk_content:
                        in_thought_block = True
                    if "</thought>" in chunk_content:
                        in_thought_block = False

                    is_final = event.choices[0].finish_reason is not None

                    yield StreamChunk(
                        content=chunk_content,
                        is_thought=in_thought_block,
                        is_final=is_final,
                        tokens_so_far=tokens_count,
                    )

        except Exception as e:
            self.logger.error("Deepseek streaming failed", error=str(e))
            raise
