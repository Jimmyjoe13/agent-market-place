"""
Base LLM Provider
==================

Classe abstraite définissant l'interface pour tous les providers LLM.
Implémente le Pattern Strategy pour permettre le switching dynamique.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.config.logging_config import LoggerMixin


class LLMProvider(str, Enum):
    """Providers LLM supportés."""

    MISTRAL = "mistral"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration générique pour un provider LLM."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0

    # Mode réflexion
    enable_reflection: bool = False
    reflection_depth: int = 1  # Nombre de passes de réflexion

    # Streaming
    stream: bool = False

    # Extra parameters spécifiques au provider
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Réponse d'un LLM avec métadonnées."""

    content: str
    tokens_input: int = 0
    tokens_output: int = 0
    model_used: str = ""

    # Mode réflexion : pensées internes
    thought_process: str | None = None

    # Métadonnées additionnelles
    finish_reason: str = "stop"
    latency_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass
class StreamChunk:
    """Chunk de streaming pour les réponses en flux."""

    content: str
    is_thought: bool = False  # True si c'est une pensée interne
    is_final: bool = False
    tokens_so_far: int = 0


class BaseLLMProvider(ABC, LoggerMixin):
    """
    Provider LLM de base (Pattern Strategy).

    Tous les providers LLM doivent implémenter cette interface.
    Supporte le mode synchrone, asynchrone et streaming.
    """

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialise le provider avec sa configuration.

        Args:
            config: Configuration du provider.
        """
        self.config = config
        self._validate_config()

    @property
    @abstractmethod
    def provider_name(self) -> LLMProvider:
        """Nom du provider."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """Liste des modèles disponibles pour ce provider."""
        pass

    @abstractmethod
    def _validate_config(self) -> None:
        """Valide la configuration spécifique au provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse complète (non-streaming).

        Args:
            messages: Liste des messages de la conversation.
            system_prompt: Prompt système optionnel.

        Returns:
            LLMResponse avec le contenu et les métadonnées.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Génère une réponse en streaming.

        Args:
            messages: Liste des messages de la conversation.
            system_prompt: Prompt système optionnel.

        Yields:
            StreamChunk avec le contenu progressif.
        """
        pass

    async def generate_with_reflection(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse avec le mode réflexion (Chain of Thought).

        Cette méthode par défaut ajoute un prompt de réflexion.
        Les providers peuvent l'override pour une implémentation native.

        Args:
            messages: Liste des messages.
            system_prompt: Prompt système.

        Returns:
            LLMResponse avec thought_process rempli.
        """
        reflection_prompt = """Tu dois réfléchir étape par étape avant de répondre.

Structure ta réponse ainsi :
<thought>
[Tes réflexions internes, analyse du problème, considérations]
</thought>

<answer>
[Ta réponse finale à l'utilisateur]
</answer>

Commence maintenant."""

        # Combiner les prompts
        combined_system = f"{system_prompt or ''}\n\n{reflection_prompt}".strip()

        # Générer la réponse
        response = await self.generate(messages, combined_system)

        # Parser les sections
        content = response.content
        thought = None
        answer = content

        if "<thought>" in content and "</thought>" in content:
            thought_start = content.find("<thought>") + len("<thought>")
            thought_end = content.find("</thought>")
            thought = content[thought_start:thought_end].strip()

        if "<answer>" in content and "</answer>" in content:
            answer_start = content.find("<answer>") + len("<answer>")
            answer_end = content.find("</answer>")
            answer = content[answer_start:answer_end].strip()
        elif "</thought>" in content:
            # Tout après </thought> est la réponse
            answer = content[content.find("</thought>") + len("</thought>") :].strip()

        return LLMResponse(
            content=answer,
            thought_process=thought,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            model_used=response.model_used,
            finish_reason=response.finish_reason,
            latency_ms=response.latency_ms,
        )

    def build_messages(
        self,
        user_query: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Construit la liste des messages pour l'API.

        Args:
            user_query: Question de l'utilisateur.
            context: Contexte additionnel (RAG, web).
            history: Historique de conversation.
            system_prompt: Prompt système.

        Returns:
            Liste de messages formatés.
        """
        messages = []

        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Historique
        if history:
            messages.extend(history)

        # Contexte (injecté comme message assistant pour guider)
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"Voici le contexte disponible:\n\n{context}",
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": "J'ai bien pris en compte le contexte. Quelle est votre question?",
                }
            )

        # Question utilisateur
        messages.append({"role": "user", "content": user_query})

        return messages
