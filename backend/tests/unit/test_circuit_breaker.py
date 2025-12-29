"""
Tests for Circuit Breaker Service
==================================
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
    get_circuit_breaker,
)


class TestCircuitBreaker:
    """Tests unitaires pour le Circuit Breaker."""
    
    @pytest.fixture
    def breaker(self):
        """Fixture pour un circuit breaker avec configuration de test."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=1,  # 1 seconde pour les tests
        )
        return CircuitBreaker(config)
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, breaker):
        """Le circuit doit démarrer en état CLOSED."""
        assert breaker.get_state("openai") == CircuitState.CLOSED
        assert not breaker.is_open("openai")
    
    @pytest.mark.asyncio
    async def test_success_keeps_circuit_closed(self, breaker):
        """Les succès gardent le circuit fermé."""
        async def success_operation():
            return "success"
        
        result = await breaker.execute("openai", success_operation)
        
        assert result == "success"
        assert breaker.get_state("openai") == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_failures_open_circuit(self, breaker):
        """Les échecs répétés ouvrent le circuit."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Provoquer 3 échecs (threshold)
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Le circuit doit être ouvert
        assert breaker.get_state("openai") == CircuitState.OPEN
        assert breaker.is_open("openai")
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_immediately(self, breaker):
        """Un circuit ouvert rejette les requêtes immédiatement."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Les prochaines requêtes doivent être rejetées
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.execute("openai", lambda: "should not run")
        
        assert exc_info.value.provider == "openai"
    
    @pytest.mark.asyncio
    async def test_open_circuit_uses_fallback(self, breaker):
        """Un circuit ouvert utilise le fallback si fourni."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Le fallback doit être utilisé
        result = await breaker.execute(
            "openai",
            lambda: "should not run",
            fallback=lambda: "fallback_result"
        )
        
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, breaker):
        """Le circuit passe en HALF_OPEN après le timeout."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        assert breaker.get_state("openai") == CircuitState.OPEN
        
        # Attendre le recovery timeout
        await asyncio.sleep(1.1)
        
        # Le circuit doit être en HALF_OPEN
        assert breaker.get_state("openai") == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, breaker):
        """Des succès en HALF_OPEN ferment le circuit."""
        async def failing_operation():
            raise Exception("API Error")
        
        async def success_operation():
            return "success"
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Attendre le recovery timeout
        await asyncio.sleep(1.1)
        
        # Exécuter des succès en HALF_OPEN
        for _ in range(2):  # success_threshold = 2
            await breaker.execute("openai", success_operation)
        
        # Le circuit doit être fermé
        assert breaker.get_state("openai") == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, breaker):
        """Un échec en HALF_OPEN réouvre le circuit."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Attendre le recovery timeout
        await asyncio.sleep(1.1)
        
        # Un échec en HALF_OPEN
        with pytest.raises(Exception):
            await breaker.execute("openai", failing_operation)
        
        # Le circuit doit être à nouveau ouvert
        assert breaker.get_state("openai") == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_different_providers_independent(self, breaker):
        """Chaque provider a son propre circuit."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit pour openai
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        # Le circuit mistral doit être toujours fermé
        assert breaker.get_state("openai") == CircuitState.OPEN
        assert breaker.get_state("mistral") == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self, breaker):
        """get_all_stats retourne les stats de tous les circuits."""
        async def success_operation():
            return "success"
        
        await breaker.execute("openai", success_operation)
        await breaker.execute("mistral", success_operation)
        
        stats = breaker.get_all_stats()
        
        assert "openai" in stats
        assert "mistral" in stats
        assert stats["openai"]["state"] == "closed"
    
    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker):
        """reset() réinitialise un circuit."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        assert breaker.get_state("openai") == CircuitState.OPEN
        
        # Reset manuel
        await breaker.reset("openai")
        
        assert breaker.get_state("openai") == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_retry_after_calculation(self, breaker):
        """get_retry_after retourne le temps restant."""
        async def failing_operation():
            raise Exception("API Error")
        
        # Ouvrir le circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute("openai", failing_operation)
        
        retry_after = breaker.get_retry_after("openai")
        
        # Doit être environ 1 seconde (recovery_timeout)
        assert 0 < retry_after <= 1


class TestCircuitBreakerSingleton:
    """Tests pour le singleton du circuit breaker."""
    
    def test_get_circuit_breaker_returns_same_instance(self):
        """get_circuit_breaker retourne toujours la même instance."""
        breaker1 = get_circuit_breaker()
        breaker2 = get_circuit_breaker()
        
        assert breaker1 is breaker2
