"""
Redis Configuration
===================

Gestion de la connexion Redis pour le rate limiting et le cache.
"""

import redis.asyncio as redis

from src.config.logging_config import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

# Client Redis asynchrone (lazy loading)
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis | None:
    """
    Retourne l'instance du client Redis.
    Initialise la connexion si nécessaire.
    """
    global _redis_client

    settings = get_settings()
    if not settings.redis_url:
        return None

    if _redis_client is None:
        try:
            logger.info("Connecting to Redis", url=settings.redis_url)
            _redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
            )
            # Vérifier la connexion
            await _redis_client.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            _redis_client = None

    return _redis_client


async def close_redis():
    """Ferme la connexion Redis."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
