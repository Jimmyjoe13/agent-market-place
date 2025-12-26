"""
Rate Limiter Service
====================

Gestion du rate limiting utilisant Redis pour le stockage des compteurs.
Prend en charge les limites par clé API et par IP.
"""

import time
from typing import Optional, Tuple
from src.config.redis import get_redis_client
from src.config.settings import get_settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """
    Service de rate limiting basé sur Redis (Fixed Window).
    """
    
    def __init__(self):
        self.settings = get_settings()
        
    async def is_allowed(
        self, 
        key: str, 
        limit: Optional[int] = None,
        window: int = 60
    ) -> Tuple[bool, int, int]:
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
            pipe.expire(redis_key, window + 5) # Un peu plus que la fenêtre
            results = await pipe.execute()
            
            count = results[0]
            allowed = count <= max_requests
            
            # Temps restant avant la fin de la fenêtre
            retry_after = window - (current_time % window) if not allowed else 0
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded", 
                    key=key, 
                    count=count, 
                    limit=max_requests
                )
                
            return allowed, count, retry_after
            
        except Exception as e:
            logger.error("Rate limiter error", error=str(e))
            return True, 0, 0

    async def check_reflection_limit(
        self, 
        user_id: str,
    ) -> Tuple[bool, int, int]:
        """
        Limite spécifique pour le mode réflexion (très coûteux).
        Par défaut: 5 réflexions par minute.
        """
        limit = getattr(self.settings, 'rate_limit_reflection', 5)
        window = 60 # 1 minute
        
        return await self.is_allowed(
            f"reflection:{user_id}", 
            limit=limit, 
            window=window
        )

# Singleton
_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
