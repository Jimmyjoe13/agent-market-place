"""
Mistral LLM Provider
=====================

Implémentation du provider Mistral avec support streaming et réflexion.
"""

import time
from collections.abc import AsyncIterator

from mistralai import Mistral

from src.config.settings import get_settings

from .base_llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    StreamChunk,
)


class MistralLLMProvider(BaseLLMProvider):
    """
    Provider Mistral AI.

    Supporte les modèles :
    - mistral-large-latest (flagship)
    - mistral-medium-latest
    - mistral-small-latest
    - mistral-tiny (économique, bon pour le routage)
    - open-mistral-7b
    - open-mixtral-8x7b
    """

    MODELS = [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "mistral-tiny",
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "open-mixtral-8x22b",
    ]

    def __init__(self, config: LLMConfig | None = None, api_key: str | None = None) -> None:
        """
        Initialise le provider Mistral.

        Args:
            config: Configuration optionnelle.
            api_key: Clé API optionnelle (BYOK).
        """
        settings = get_settings()

        default_config = LLMConfig(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        super().__init__(config or default_config)

        effective_key = api_key or settings.mistral_api_key
        self._client = Mistral(api_key=effective_key)

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.MISTRAL

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    def _validate_config(self) -> None:
        """Valide la configuration Mistral."""
        if self.config.model not in self.MODELS:
            self.logger.warning(f"Model {self.config.model} not in known models, using anyway")

        if not (0 <= self.config.temperature <= 1.5):
            raise ValueError("Temperature must be between 0 and 1.5")

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse avec Mistral.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Returns:
            LLMResponse avec le contenu généré.
        """
        start_time = time.time()

        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            response = self._client.chat.complete(
                model=self.config.model,
                messages=final_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            duration = time.time() - start_time

            # Enregistrer les métriques Prometheus
            try:
                from src.utils.metrics import record_llm_request

                record_llm_request(
                    provider="mistral",
                    model=self.config.model,
                    status="success",
                    duration=duration,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                )
            except ImportError:
                pass  # Metrics not available

            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_input=response.usage.prompt_tokens,
                tokens_output=response.usage.completion_tokens,
                model_used=self.config.model,
                finish_reason=response.choices[0].finish_reason or "stop",
                latency_ms=latency_ms,
            )

        except Exception as e:
            # Enregistrer l'erreur dans les métriques
            try:
                from src.utils.metrics import record_llm_request

                record_llm_request(
                    provider="mistral",
                    model=self.config.model,
                    status="error",
                    duration=time.time() - start_time,
                )
            except ImportError:
                pass

            self.logger.error("Mistral generation failed", error=str(e))
            raise

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Génère une réponse en streaming avec Mistral.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Yields:
            StreamChunk progressifs.
        """
        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            stream = self._client.chat.stream(
                model=self.config.model,
                messages=final_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            tokens_count = 0
            in_thought_block = False

            for event in stream:
                if event.data.choices and event.data.choices[0].delta.content:
                    chunk_content = event.data.choices[0].delta.content
                    tokens_count += 1  # Approximation

                    # Détecter les blocs de pensée
                    if "<thought>" in chunk_content:
                        in_thought_block = True
                    if "</thought>" in chunk_content:
                        in_thought_block = False

                    is_final = event.data.choices[0].finish_reason is not None

                    yield StreamChunk(
                        content=chunk_content,
                        is_thought=in_thought_block,
                        is_final=is_final,
                        tokens_so_far=tokens_count,
                    )

        except Exception as e:
            self.logger.error("Mistral streaming failed", error=str(e))
            raise
