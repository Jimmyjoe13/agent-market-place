"""
Gemini LLM Provider
====================

Implémentation du provider Google Gemini.
"""

import time
from typing import AsyncIterator

from src.config.settings import get_settings
from .base_llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    StreamChunk,
)


class GeminiLLMProvider(BaseLLMProvider):
    """
    Provider Google Gemini.
    
    Supporte les modèles :
    - gemini-2.0-flash-exp (dernier, rapide)
    - gemini-1.5-pro (flagship)
    - gemini-1.5-flash (rapide, économique)
    - gemini-1.5-flash-8b (ultra-économique)
    """
    
    MODELS = [
        "gemini-3-pro",
        "gemini-3-flash",
        "gemini-2.5-flash-exp",
        "gemini-2.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.0-pro",
    ]
    
    def __init__(self, config: LLMConfig | None = None, api_key: str | None = None) -> None:
        """
        Initialise le provider Gemini.
        
        Args:
            config: Configuration optionnelle.
            api_key: Clé API optionnelle (BYOK - Bring Your Own Key).
        """
        settings = get_settings()
        
        default_config = LLMConfig(
            model="gemini-1.5-flash",
            temperature=0.7,
            max_tokens=4096,
        )
        
        super().__init__(config or default_config)
        
        # Import conditionnel
        try:
            import google.generativeai as genai
            # Priorité: Clé passée explicitement > Clé du settings
            effective_key = api_key or getattr(settings, 'gemini_api_key', None)
            if not effective_key:
                self.logger.warning("Gemini API key not configured")
                self._client = None
            else:
                genai.configure(api_key=effective_key)
                self._client = genai.GenerativeModel(self.config.model)
                self._genai = genai
        except ImportError:
            self.logger.warning("Google Generative AI package not installed")
            self._client = None
            self._genai = None
    
    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.GEMINI
    
    @property
    def available_models(self) -> list[str]:
        return self.MODELS
    
    @property
    def is_available(self) -> bool:
        """Vérifie si le provider est disponible."""
        return self._client is not None
    
    def _validate_config(self) -> None:
        """Valide la configuration Gemini."""
        if self.config.model not in self.MODELS:
            self.logger.warning(
                f"Model {self.config.model} not in known models, using anyway"
            )
        
        if not (0 <= self.config.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")
    
    def _convert_messages_to_gemini(
        self, 
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> tuple[str, list]:
        """
        Convertit les messages au format Gemini.
        
        Gemini utilise un format différent avec system_instruction séparé.
        
        Returns:
            (system_instruction, history)
        """
        system_instruction = system_prompt or ""
        history = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = f"{system_instruction}\n{content}".strip()
            elif role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})
        
        return system_instruction, history
    
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Génère une réponse avec Gemini.
        
        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.
            
        Returns:
            LLMResponse avec le contenu généré.
        """
        if not self._client:
            raise RuntimeError("Gemini client not initialized")
        
        start_time = time.time()
        
        # Convertir les messages
        system_instruction, history = self._convert_messages_to_gemini(
            messages, system_prompt
        )
        
        try:
            # Créer un modèle avec l'instruction système
            model = self._genai.GenerativeModel(
                self.config.model,
                system_instruction=system_instruction if system_instruction else None,
            )
            
            # Configuration de génération
            generation_config = self._genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )
            
            # Utiliser le dernier message comme prompt
            if history:
                last_message = history[-1]["parts"][0] if history[-1]["role"] == "user" else ""
                chat_history = history[:-1] if len(history) > 1 else []
            else:
                last_message = ""
                chat_history = []
            
            # Créer le chat et envoyer
            chat = model.start_chat(history=chat_history)
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Estimer les tokens (Gemini n'expose pas toujours ça)
            input_tokens = sum(len(m.get("parts", [""])[0]) // 4 for m in history)
            output_tokens = len(response.text) // 4
            
            return LLMResponse(
                content=response.text,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                model_used=self.config.model,
                finish_reason="stop",
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            self.logger.error("Gemini generation failed", error=str(e))
            raise
    
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Génère une réponse en streaming avec Gemini.
        
        Args:
            messages: Liste des messages.
            system_prompt: Prompt système optionnel.
            
        Yields:
            StreamChunk progressifs.
        """
        if not self._client:
            raise RuntimeError("Gemini client not initialized")
        
        # Convertir les messages
        system_instruction, history = self._convert_messages_to_gemini(
            messages, system_prompt
        )
        
        try:
            model = self._genai.GenerativeModel(
                self.config.model,
                system_instruction=system_instruction if system_instruction else None,
            )
            
            generation_config = self._genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )
            
            if history:
                last_message = history[-1]["parts"][0] if history[-1]["role"] == "user" else ""
                chat_history = history[:-1] if len(history) > 1 else []
            else:
                last_message = ""
                chat_history = []
            
            chat = model.start_chat(history=chat_history)
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
                stream=True,
            )
            
            tokens_count = 0
            in_thought_block = False
            
            async for chunk in response:
                if chunk.text:
                    chunk_content = chunk.text
                    tokens_count += len(chunk_content) // 4
                    
                    # Détecter les blocs de pensée
                    if "<thought>" in chunk_content:
                        in_thought_block = True
                    if "</thought>" in chunk_content:
                        in_thought_block = False
                    
                    yield StreamChunk(
                        content=chunk_content,
                        is_thought=in_thought_block,
                        is_final=False,
                        tokens_so_far=tokens_count,
                    )
            
            # Chunk final
            yield StreamChunk(
                content="",
                is_thought=False,
                is_final=True,
                tokens_so_far=tokens_count,
            )
                    
        except Exception as e:
            self.logger.error("Gemini streaming failed", error=str(e))
            raise
