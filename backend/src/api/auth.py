"""
API Authentication Module
==========================

Middleware et dépendances FastAPI pour l'authentification par clé API.

Ce module fournit :
- Extraction de la clé depuis header ou query param
- Validation de la clé avec vérification des scopes
- Gestion des erreurs d'authentification

Usage:
    >>> from fastapi import Depends
    >>> from src.api.auth import require_api_key, require_scope
    >>>
    >>> @router.post("/query")
    >>> async def query(api_key = Depends(require_api_key)):
    ...     # api_key contient les informations de la clé validée
    ...     pass
    >>>
    >>> @router.post("/admin/keys")
    >>> async def create_key(api_key = Depends(require_scope("admin"))):
    ...     # Nécessite le scope "admin"
    ...     pass
"""

import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from src.config.logging_config import get_logger
from src.config.settings import get_settings
from src.models.api_key import ApiKeyScope, ApiKeyValidation
from src.repositories.api_key_repository import ApiKeyRepository
from src.services.rate_limiter import get_rate_limiter

logger = get_logger(__name__)

# ===== Security Schemes pour OpenAPI/Swagger =====

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key Header",
    description="Clé API dans le header X-API-Key",
    auto_error=False,
)

api_key_query = APIKeyQuery(
    name="api_key",
    scheme_name="API Key Query",
    description="Clé API en query parameter (?api_key=xxx)",
    auto_error=False,
)

# ===== Repository (lazy loading) =====

_api_key_repo: ApiKeyRepository | None = None


def get_api_key_repo() -> ApiKeyRepository:
    """Retourne l'instance du repository API keys."""
    global _api_key_repo
    if _api_key_repo is None:
        _api_key_repo = ApiKeyRepository()
    return _api_key_repo


# ===== Dépendances d'authentification =====


async def get_api_key(
    request: Request,
    header_key: str | None = Security(api_key_header),
    query_key: str | None = Security(api_key_query),
) -> ApiKeyValidation | None:
    """
    Extrait et valide la clé API depuis la requête.

    Cherche la clé dans l'ordre :
    1. Header `X-API-Key`
    2. Query parameter `api_key`

    Args:
        request: Requête FastAPI.
        header_key: Clé depuis le header.
        query_key: Clé depuis le query param.

    Returns:
        ApiKeyValidation si valide, None si pas de clé fournie.

    Raises:
        HTTPException 401: Si la clé est invalide.
        HTTPException 403: Si la clé est expirée/révoquée/quota dépassé.
    """
    settings = get_settings()

    # Mode développement sans auth
    if not settings.api_key_required and settings.is_development:
        return None

    # Extraire la clé
    key = header_key or query_key

    if not key:
        # Vérifier si l'auth est requise
        if settings.api_key_required:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "api_key_required",
                    "message": "Clé API requise. Utilisez le header X-API-Key ou le paramètre api_key.",
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return None

    # Valider la clé
    repo = get_api_key_repo()
    client_ip = _get_client_ip(request)

    validation = repo.validate(key, client_ip)

    if validation is None:
        logger.warning("API key validation failed", client_ip=client_ip)
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_api_key",
                "message": "Clé API invalide.",
            },
        )

    if not validation.is_valid:
        logger.warning(
            "API key rejected",
            key_id=str(validation.key_id),
            reason=validation.rejection_reason,
        )

        status_code = 403
        error_messages = {
            "key_revoked": "Cette clé API a été révoquée.",
            "key_expired": "Cette clé API a expiré.",
            "quota_exceeded": "Quota mensuel dépassé pour cette clé.",
        }

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": validation.rejection_reason,
                "message": error_messages.get(
                    validation.rejection_reason,
                    "Clé API non autorisée.",
                ),
            },
        )

    # ===== 3. Rate Limiting =====
    rate_limiter = get_rate_limiter()

    # On limite par ID de clé si présent, sinon par IP (fallback/public)
    limit_id = f"key:{validation.key_id}" if validation else f"ip:{client_ip}"
    limit_value = validation.rate_limit if validation else settings.rate_limit_requests

    allowed, count, retry_after = await rate_limiter.is_allowed(key=limit_id, limit=limit_value)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Limite de requêtes dépassée. Réessayez dans {retry_after} secondes.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Stocker les infos dans request.state pour logging et middleware
    request.state.api_key = validation
    request.state.request_start_time = time.time()
    request.state.rate_limit_count = count
    request.state.rate_limit_max = limit_value
    request.state.rate_limit_retry_after = retry_after

    if validation:
        logger.debug(
            "API key validated",
            key_id=str(validation.key_id),
            scopes=validation.scopes,
            rate_count=count,
            model_id=validation.model_id,
        )

    return validation


async def require_api_key(
    api_key: ApiKeyValidation | None = Depends(get_api_key),
) -> ApiKeyValidation:
    """
    Dépendance qui EXIGE une clé API valide.

    À utiliser sur les endpoints protégés.

    Args:
        api_key: Résultat de get_api_key.

    Returns:
        ApiKeyValidation avec les informations de la clé.

    Raises:
        HTTPException 401: Si pas de clé valide.

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(
        ...     api_key: ApiKeyValidation = Depends(require_api_key)
        ... ):
        ...     return {"key_name": api_key.name}
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "Authentification requise pour cet endpoint.",
            },
        )
    return api_key


def require_scope(scope: str | ApiKeyScope) -> Callable:
    """
    Factory pour créer une dépendance qui vérifie un scope spécifique.

    Args:
        scope: Scope requis (ex: "admin", "ingest").

    Returns:
        Dépendance FastAPI à utiliser avec Depends().

    Example:
        >>> @router.delete("/keys/{key_id}")
        >>> async def delete_key(
        ...     key_id: str,
        ...     api_key = Depends(require_scope("admin"))
        ... ):
        ...     # Seules les clés avec scope "admin" peuvent accéder
        ...     pass
    """
    scope_value = scope.value if isinstance(scope, ApiKeyScope) else scope

    async def scope_checker(
        api_key: ApiKeyValidation = Depends(require_api_key),
    ) -> ApiKeyValidation:
        """Vérifie que la clé a le scope requis."""
        if scope_value not in api_key.scopes and "admin" not in api_key.scopes:
            logger.warning(
                "Scope denied",
                key_id=str(api_key.key_id),
                required=scope_value,
                has=api_key.scopes,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_scope",
                    "message": f"Cette clé ne possède pas le scope '{scope_value}'.",
                    "required_scope": scope_value,
                    "your_scopes": api_key.scopes,
                },
            )
        return api_key

    return scope_checker


def require_any_scope(*scopes: str | ApiKeyScope) -> Callable:
    """
    Factory pour vérifier qu'au moins un des scopes est présent.

    Args:
        *scopes: Scopes acceptés.

    Returns:
        Dépendance FastAPI.

    Example:
        >>> @router.post("/data")
        >>> async def upload_data(
        ...     api_key = Depends(require_any_scope("ingest", "admin"))
        ... ):
        ...     pass
    """
    scope_values = [s.value if isinstance(s, ApiKeyScope) else s for s in scopes]

    async def scope_checker(
        api_key: ApiKeyValidation = Depends(require_api_key),
    ) -> ApiKeyValidation:
        """Vérifie qu'au moins un scope est présent."""
        if not any(s in api_key.scopes for s in scope_values) and "admin" not in api_key.scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_scope",
                    "message": f"Un des scopes suivants est requis: {scope_values}",
                    "required_scopes": scope_values,
                    "your_scopes": api_key.scopes,
                },
            )
        return api_key

    return scope_checker


# ===== Helpers =====


def _get_client_ip(request: Request) -> str:
    """
    Extrait l'adresse IP du client.

    Gère les proxies via X-Forwarded-For.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


# ===== Master Key Validation =====


async def require_master_key(
    request: Request,
    header_key: str | None = Security(api_key_header),
) -> bool:
    """
    Vérifie la master key pour les opérations initiales.

    La master key est définie dans .env et permet de créer
    les premières clés API.

    Raises:
        HTTPException 401: Si la master key est invalide.
    """
    settings = get_settings()

    if not settings.api_master_key:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "master_key_not_configured",
                "message": "API_MASTER_KEY non configurée dans .env",
            },
        )

    if header_key != settings.api_master_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_master_key",
                "message": "Master key invalide.",
            },
        )

    return True
