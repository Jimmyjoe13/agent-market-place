"""
Rate Limiter Service
====================

Gestion du rate limiting utilisant Redis pour le stockage des compteurs.
Prend en charge les limites par clé API et par IP.
"""

import time

from src.config.logging_config import get_logger
from src.config.redis import get_redis_client
from src.config.settings import get_settings

logger = get_logger(__name__)


class RateLimiter:
    """
    Service de rate limiting basé sur Redis (Fixed Window).
    """

    def __init__(self):
        self.settings = get_settings()

    async def is_allowed(
        self, key: str, limit: int | None = None, window: int = 60
    ) -> tuple[bool, int, int]:
        """
        Vérifie si une requête est autorisée pour une clé donnée.

        Args:
            key: Identifiant unique (ex: prefixe_cle ou IP).
            limit: Nombre max de requêtes dans la fenêtre (défaut depuis settings).
            window: Taille de la fenêtre en secondes (défaut 60s).

        Returns:
            (allowed, current_count, retry_after)
        """
        if not self.settings.rate_limit_enabled:
            return True, 0, 0

        redis = await get_redis_client()
        if not redis:
            # Fallback si Redis est indisponible
            logger.warning("Redis unavailable for rate limiting, allowing request")
            return True, 0, 0

        # Résolution de la limite
        max_requests = limit if limit is not None else self.settings.rate_limit_requests
        if max_requests <= 0:
            return True, 0, 0

        # Clé Redis : rl:{key}:{timestamp_fenetre}
        current_time = int(time.time())
        window_id = current_time // window
        redis_key = f"rl:{key}:{window_id}"

        try:
            # Incrémenter et récupérer le compteur
            # On utilise pipeline pour s'assurer de l'expiration
            pipe = redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window + 5)  # Un peu plus que la fenêtre
            results = await pipe.execute()

            count = results[0]
            allowed = count <= max_requests

            # Temps restant avant la fin de la fenêtre
            retry_after = window - (current_time % window) if not allowed else 0

            if not allowed:
                logger.warning("Rate limit exceeded", key=key, count=count, limit=max_requests)

            return allowed, count, retry_after

        except Exception as e:
            logger.error("Rate limiter error", error=str(e))
            return True, 0, 0

    async def check_reflection_limit(
        self,
        user_id: str,
    ) -> tuple[bool, int, int]:
        """
        Limite spécifique pour le mode réflexion (très coûteux).
        Par défaut: 5 réflexions par minute.
        """
        limit = getattr(self.settings, "rate_limit_reflection", 5)
        window = 60  # 1 minute

        return await self.is_allowed(f"reflection:{user_id}", limit=limit, window=window)

    async def is_allowed_by_api_key(
        self,
        api_key_id: str,
        operation_type: str = "query",
        limit: int | None = None,
        window: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Rate limiting granulaire par api_key_id et type d'opération.

        Cette méthode permet un contrôle fin des limites par agent et par
        type d'opération (query, ingest, reflection).

        Args:
            api_key_id: ID de la clé API (agent).
            operation_type: Type d'opération (query, ingest, reflection).
            limit: Limite personnalisée (sinon défaut settings).
            window: Fenêtre en secondes.

        Returns:
            (allowed, current_count, retry_after)
        """
        # Limites par défaut selon le type d'opération
        default_limits = {
            "query": getattr(self.settings, "rate_limit_requests", 60),
            "ingest": getattr(self.settings, "rate_limit_ingest", 20),
            "reflection": getattr(self.settings, "rate_limit_reflection", 5),
        }

        effective_limit = (
            limit
            if limit is not None
            else default_limits.get(operation_type, self.settings.rate_limit_requests)
        )

        # Clé unique: rl:api:{api_key_id}:{operation}:{window}
        key = f"api:{api_key_id}:{operation_type}"

        return await self.is_allowed(key, effective_limit, window)

    async def check_budget_limit(
        self,
        api_key_id: str,
        tokens_to_use: int,
    ) -> tuple[bool, dict]:
        """
        Vérifie si l'utilisation de tokens est dans le budget.

        Combine rate limiting Redis et vérification budget DB.

        Args:
            api_key_id: ID de la clé API.
            tokens_to_use: Nombre de tokens à utiliser.

        Returns:
            (allowed, budget_info)
        """
        # Rate limit par api_key d'abord
        allowed, count, retry_after = await self.is_allowed_by_api_key(
            api_key_id, operation_type="query"
        )

        if not allowed:
            return False, {
                "reason": "rate_limit_exceeded",
                "current_count": count,
                "retry_after": retry_after,
            }

        # La vérification du budget tokens se fait en DB via la fonction SQL
        # check_token_budget() - à appeler séparément dans le middleware
        return True, {"reason": "allowed"}

    async def get_usage_stats(
        self,
        api_key_id: str,
    ) -> dict:
        """
        Récupère les statistiques d'utilisation d'une clé API.

        Args:
            api_key_id: ID de la clé API.

        Returns:
            Statistiques d'utilisation par type d'opération.
        """
        redis = await get_redis_client()
        if not redis:
            return {}

        current_time = int(time.time())
        window_id = current_time // 60  # Fenêtre de 1 minute

        stats = {}
        for op_type in ["query", "ingest", "reflection"]:
            redis_key = f"rl:api:{api_key_id}:{op_type}:{window_id}"
            try:
                count = await redis.get(redis_key)
                stats[op_type] = int(count) if count else 0
            except Exception:
                stats[op_type] = 0

        return stats


# Singleton
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
