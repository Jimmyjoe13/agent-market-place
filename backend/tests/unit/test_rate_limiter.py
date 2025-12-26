"""
Tests unitaires pour le Rate Limiter.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.rate_limiter import RateLimiter

class TestRateLimiter:
    """Tests pour le service RateLimiter."""
    
    @pytest.fixture
    def limiter(self):
        """Créer un RateLimiter avec settings mockés."""
        with patch("src.services.rate_limiter.get_settings") as mock_settings:
            settings = Mock()
            settings.rate_limit_enabled = True
            settings.rate_limit_requests = 100
            settings.rate_limit_reflection = 2
            mock_settings.return_value = settings
            
            limiter = RateLimiter()
            limiter.settings = settings
            return limiter

    @pytest.mark.asyncio
    async def test_reflection_limit_works(self, limiter):
        """Vérifie que la limite de réflexion est respectée."""
        with patch("src.services.rate_limiter.get_redis_client") as mock_redis_func:
            mock_redis = AsyncMock()
            mock_redis_func.return_value = mock_redis
            
            # Simuler Redis pipeline
            mock_pipe = AsyncMock()
            mock_redis.pipeline.return_value = mock_pipe
            
            # Premier appel (autorisé)
            mock_pipe.execute.return_value = [1, True]
            allowed, count, _ = await limiter.check_reflection_limit("user1")
            assert allowed is True
            assert count == 1
            
            # Deuxième appel (autorisé)
            mock_pipe.execute.return_value = [2, True]
            allowed, count, _ = await limiter.check_reflection_limit("user1")
            assert allowed is True
            assert count == 2
            
            # Troisième appel (bloqué, limite à 2 définie dans fixture)
            mock_pipe.execute.return_value = [3, True]
            allowed, count, retry = await limiter.check_reflection_limit("user1")
            assert allowed is False
            assert count == 3
            assert retry > 0

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(self, limiter):
        """Vérifie que le limiter ne bloque rien si désactivé."""
        limiter.settings.rate_limit_enabled = False
        
        allowed, _, _ = await limiter.is_allowed("test")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_redis_unavailable_fallback(self, limiter):
        """Vérifie le fallback si Redis est HS."""
        with patch("src.services.rate_limiter.get_redis_client", return_value=None):
            allowed, _, _ = await limiter.is_allowed("test")
            assert allowed is True
