"""
OpenAI LLM Provider
====================

Implémentation du provider OpenAI (GPT-4, GPT-4o, GPT-3.5).
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


class OpenAILLMProvider(BaseLLMProvider):
    """
    Provider OpenAI (Décembre 2025).

    Supporte les modèles :

    PREMIUM (abonnement requis):
    - GPT-5.2 Series: gpt-5.2, gpt-5.2-pro (flagship, codage, agentique)
    - GPT-5.1 Series: gpt-5.1, gpt-5.1-codex-max (raisonnement configurable)
    - O-Series: o3-deep-research, o3-pro, o4-mini-deep-research, o1-pro (research)

    STANDARD (gratuit):
    - GPT-5 Series: gpt-5, gpt-5-mini, gpt-5-nano
    - GPT-4.1 Series: gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
    - Legacy: gpt-4o, gpt-4o-mini, gpt-4-turbo
    """

    # Tous les modèles disponibles
    MODELS = [
        # GPT-5.2 Series (Flagship - Premium)
        "gpt-5.2",
        "gpt-5.2-pro",
        # GPT-5.1 Series (Premium)
        "gpt-5.1",
        "gpt-5.1-codex-max",
        # GPT-5 Series (Standard)
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        # GPT-4.1 Series (Standard)
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # O-Series (Research - Premium)
        "o3-deep-research",
        "o3-pro",
        "o4-mini-deep-research",
        "o1-pro",
        # Legacy (Standard)
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
    ]

    # Modèles nécessitant un abonnement premium
    PREMIUM_MODELS = [
        "gpt-5.2",
        "gpt-5.2-pro",
        "gpt-5.1",
        "gpt-5.1-codex-max",
        "o3-deep-research",
        "o3-pro",
        "o4-mini-deep-research",
        "o1-pro",
    ]

    def __init__(self, config: LLMConfig | None = None, api_key: str | None = None) -> None:
        """
        Initialise le provider OpenAI.

        Args:
            config: Configuration optionnelle.
            api_key: Clé API optionnelle (BYOK).
        """
        settings = get_settings()

        default_config = LLMConfig(
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=4096,
        )

        super().__init__(config or default_config)

        # Priorité: Clé passée explicitement > Clé du settings
        effective_key = api_key or getattr(settings, "openai_api_key", None)

        # Import conditionnel pour éviter d'obliger l'installation
        try:
            from openai import AsyncOpenAI

            if not effective_key:
                self.logger.warning("OpenAI API key not configured")
                self._client = None
            else:
                self._client = AsyncOpenAI(api_key=effective_key)
        except ImportError:
            self.logger.warning("OpenAI package not installed")
            self._client = None

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.OPENAI

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    @property
    def is_available(self) -> bool:
        """Vérifie si le provider est disponible."""
        return self._client is not None

    def _validate_config(self) -> None:
        """Valide la configuration OpenAI."""
        if self.config.model not in self.MODELS:
            self.logger.warning(f"Model {self.config.model} not in known models, using anyway")

        if not (0 <= self.config.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")

    def _get_completion_params(self, messages: list[dict[str, str]], stream: bool = False) -> dict:
        """
        Prépare les paramètres de complétion en fonction du modèle.

        Gère les nouveaux modèles (GPT-5, O-Series) qui requièrent
        'max_completion_tokens' au lieu de 'max_tokens'.
        """
        # Modèles de raisonnement (O-Series)
        is_reasoning = self.config.model.startswith(("o1-", "o3-", "o4-"))
        # Nouveaux modèles GPT-5 et GPT-4.1
        is_new_series = self.config.model.startswith(("gpt-5", "gpt-4.1"))

        params = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
        }

        # Paramètre de limite de tokens (nouveau format vs ancien)
        if is_reasoning or is_new_series:
            params["max_completion_tokens"] = self.config.max_tokens
        else:
            params["max_tokens"] = self.config.max_tokens

        # Les modèles O-Series et GPT-5 imposent souvent temperature=1.0
        if is_reasoning or self.config.model.startswith("gpt-5"):
            # Forcé à 1.0 par l'API pour ces modèles
            params["temperature"] = 1.0
        else:
            params["temperature"] = self.config.temperature
            params["top_p"] = self.config.top_p

        return params

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse avec OpenAI.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Returns:
            LLMResponse avec le contenu généré.

        Raises:
            RuntimeError: Si le client n'est pas initialisé ou si la réponse est vide.
        """
        if not self._client:
            raise RuntimeError(
                f"OpenAI client not initialized. Check OPENAI_API_KEY environment variable. "
                f"Model requested: {self.config.model}"
            )

        start_time = time.time()

        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            params = self._get_completion_params(final_messages)
            response = await self._client.chat.completions.create(**params)

            latency_ms = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content or ""

            # Valider que la réponse n'est pas vide
            if not content.strip():
                self.logger.error(
                    "OpenAI returned empty response",
                    model=self.config.model,
                    finish_reason=response.choices[0].finish_reason,
                )
                raise RuntimeError(
                    f"OpenAI returned empty response for model {self.config.model}. "
                    f"Finish reason: {response.choices[0].finish_reason}"
                )

            return LLMResponse(
                content=content,
                tokens_input=response.usage.prompt_tokens if response.usage else 0,
                tokens_output=response.usage.completion_tokens if response.usage else 0,
                model_used=self.config.model,
                finish_reason=response.choices[0].finish_reason or "stop",
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.logger.error("OpenAI generation failed", error=str(e), model=self.config.model)
            raise

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Génère une réponse en streaming avec OpenAI.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.

        Yields:
            StreamChunk progressifs.
        """
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")

        # Préparer les messages
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        try:
            params = self._get_completion_params(final_messages, stream=True)
            stream = await self._client.chat.completions.create(**params)

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
            self.logger.error("OpenAI streaming failed", error=str(e))
            raise
