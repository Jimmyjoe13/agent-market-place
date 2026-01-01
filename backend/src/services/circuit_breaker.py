"""
Circuit Breaker Service
========================

Protection contre les pannes en cascade des APIs LLM externes.
Implémente le pattern Circuit Breaker avec trois états:
- CLOSED: Normal, les requêtes passent
- OPEN: Bloqué, les requêtes échouent immédiatement
- HALF_OPEN: Test, une requête passe pour vérifier la récupération
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
from collections import defaultdict

from src.config.logging_config import get_logger
from src.config.redis import get_redis_client

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """États du circuit breaker."""
    CLOSED = "closed"      # Normal - requêtes passent
    OPEN = "open"          # Bloqué - requêtes rejetées
    HALF_OPEN = "half_open"  # Test - une requête pour vérifier


class CircuitOpenError(Exception):
    """Levée quand le circuit est ouvert."""
    def __init__(self, provider: str, retry_after: int):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker for {provider} is OPEN. Retry after {retry_after}s")


@dataclass
class CircuitStats:
    """Statistiques d'un circuit."""
    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    state: CircuitState = CircuitState.CLOSED
    opened_at: float = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration du circuit breaker."""
    failure_threshold: int = 5          # Échecs avant ouverture
    success_threshold: int = 2          # Succès en HALF_OPEN avant fermeture
    recovery_timeout: int = 30          # Secondes avant passage HALF_OPEN
    half_open_max_calls: int = 3        # Requêtes max en HALF_OPEN
    

class CircuitBreaker:
    """
    Circuit breaker pour APIs LLM externes.
    
    Protège contre les pannes en cascade en:
    - Détectant les échecs répétés
    - Bloquant les requêtes pendant la panne
    - Testant périodiquement la récupération
    
    Usage:
        breaker = CircuitBreaker()
        result = await breaker.execute("openai", api_call_coroutine)
    """
    
    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._circuits: dict[str, CircuitStats] = defaultdict(CircuitStats)
        self._half_open_calls: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        
    def get_state(self, provider: str) -> CircuitState:
        """Retourne l'état actuel du circuit pour un provider."""
        stats = self._circuits[provider]
        
        if stats.state == CircuitState.OPEN:
            # Vérifier si on peut passer en HALF_OPEN
            elapsed = time.time() - stats.opened_at
            if elapsed >= self.config.recovery_timeout:
                return CircuitState.HALF_OPEN
                
        return stats.state
    
    def is_open(self, provider: str) -> bool:
        """Vérifie si le circuit est ouvert (bloqué)."""
        return self.get_state(provider) == CircuitState.OPEN
    
    def get_retry_after(self, provider: str) -> int:
        """Retourne le temps restant avant réessai possible."""
        stats = self._circuits[provider]
        if stats.state != CircuitState.OPEN:
            return 0
        
        elapsed = time.time() - stats.opened_at
        remaining = self.config.recovery_timeout - elapsed
        return max(0, int(remaining))
    
    async def execute(
        self, 
        provider: str, 
        operation: Callable[[], Any],
        fallback: Callable[[], Any] | None = None
    ) -> Any:
        """
        Exécute une opération avec protection circuit breaker.
        
        Args:
            provider: Identifiant du provider (openai, mistral, deepseek)
            operation: Coroutine à exécuter
            fallback: Fallback optionnel si circuit ouvert
            
        Returns:
            Résultat de l'opération ou du fallback
            
        Raises:
            CircuitOpenError: Si circuit ouvert et pas de fallback
        """
        state = self.get_state(provider)
        
        # Circuit ouvert
        if state == CircuitState.OPEN:
            retry_after = self.get_retry_after(provider)
            logger.warning(
                "Circuit breaker OPEN",
                provider=provider,
                retry_after=retry_after
            )
            
            if fallback:
                fallback_result = fallback()
                return await fallback_result if asyncio.iscoroutine(fallback_result) else fallback_result
            
            raise CircuitOpenError(provider, retry_after)
        
        # Circuit HALF_OPEN - limiter les appels de test
        if state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls[provider] >= self.config.half_open_max_calls:
                    if fallback:
                        fallback_result = fallback()
                        return await fallback_result if asyncio.iscoroutine(fallback_result) else fallback_result
                    raise CircuitOpenError(provider, self.config.recovery_timeout)
                
                self._half_open_calls[provider] += 1
        
        # Exécuter l'opération
        try:
            result = operation()
            if asyncio.iscoroutine(result):
                result = await result
            await self._record_success(provider)
            return result
            
        except Exception as e:
            await self._record_failure(provider, e)
            raise
    
    async def _record_success(self, provider: str) -> None:
        """Enregistre un succès."""
        async with self._lock:
            stats = self._circuits[provider]
            stats.successes += 1
            stats.last_success_time = time.time()
            
            current_state = self.get_state(provider)
            
            if current_state == CircuitState.HALF_OPEN:
                # Vérifier si on peut fermer le circuit
                if stats.successes >= self.config.success_threshold:
                    stats.state = CircuitState.CLOSED
                    stats.failures = 0
                    stats.successes = 0
                    self._half_open_calls[provider] = 0
                    logger.info(
                        "Circuit breaker CLOSED",
                        provider=provider,
                        reason="recovery_successful"
                    )
            elif current_state == CircuitState.CLOSED:
                # Reset failures counter on success
                stats.failures = 0
    
    async def _record_failure(self, provider: str, error: Exception) -> None:
        """Enregistre un échec."""
        async with self._lock:
            stats = self._circuits[provider]
            stats.failures += 1
            stats.last_failure_time = time.time()
            
            current_state = self.get_state(provider)
            
            logger.warning(
                "Circuit breaker failure recorded",
                provider=provider,
                failures=stats.failures,
                threshold=self.config.failure_threshold,
                error=str(error)
            )
            
            if current_state == CircuitState.HALF_OPEN:
                # Retour à OPEN si échec en HALF_OPEN
                stats.state = CircuitState.OPEN
                stats.opened_at = time.time()
                stats.successes = 0
                self._half_open_calls[provider] = 0
                logger.warning(
                    "Circuit breaker re-OPENED",
                    provider=provider,
                    reason="half_open_failure"
                )
                
            elif current_state == CircuitState.CLOSED:
                # Ouvrir si threshold atteint
                if stats.failures >= self.config.failure_threshold:
                    stats.state = CircuitState.OPEN
                    stats.opened_at = time.time()
                    logger.error(
                        "Circuit breaker OPENED",
                        provider=provider,
                        failures=stats.failures
                    )
    
    def get_all_stats(self) -> dict[str, dict]:
        """Retourne les stats de tous les circuits."""
        return {
            provider: {
                "state": self.get_state(provider).value,
                "failures": stats.failures,
                "successes": stats.successes,
                "retry_after": self.get_retry_after(provider)
            }
            for provider, stats in self._circuits.items()
        }
    
    async def reset(self, provider: str) -> None:
        """Reset manuel d'un circuit (admin)."""
        async with self._lock:
            self._circuits[provider] = CircuitStats()
            self._half_open_calls[provider] = 0
            logger.info("Circuit breaker manually reset", provider=provider)


# ============================================
# Singleton global
# ============================================

_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Retourne l'instance globale du circuit breaker."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker


# ============================================
# Décorateur pour usage simplifié
# ============================================

def with_circuit_breaker(provider: str):
    """
    Décorateur pour protéger une fonction avec le circuit breaker.
    
    Usage:
        @with_circuit_breaker("openai")
        async def call_openai():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker()
            return await breaker.execute(
                provider,
                lambda: func(*args, **kwargs)
            )
        return wrapper
    return decorator
