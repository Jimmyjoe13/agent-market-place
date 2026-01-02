"""
Admin Routes
=============

Endpoints d'administration pour la gestion des clés API.

Ces endpoints nécessitent le scope "admin" ou la master key.

Endpoints:
    POST   /api/v1/keys          - Créer une clé API
    GET    /api/v1/keys          - Lister les clés
    GET    /api/v1/keys/{id}     - Détails d'une clé
    DELETE /api/v1/keys/{id}     - Révoquer une clé
    GET    /api/v1/keys/{id}/stats - Statistiques d'usage
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_master_key
from src.config.logging_config import get_logger
from src.models.api_key import (
    ApiKeyCreate,
    ApiKeyInfo,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyUsageStats,
)
from src.repositories.api_key_repository import ApiKeyRepository

logger = get_logger(__name__)

# Router pour les endpoints admin
admin_router = APIRouter(
    prefix="/keys",
    tags=["API Keys Management"],
    responses={
        401: {"description": "Authentification requise"},
        403: {"description": "Permissions insuffisantes"},
    },
)

# Repository (lazy loading)
_repo: ApiKeyRepository | None = None


def get_repo() -> ApiKeyRepository:
    """Retourne l'instance du repository."""
    global _repo
    if _repo is None:
        _repo = ApiKeyRepository()
    return _repo


# ===== Endpoints =====


@admin_router.post(
    "",
    response_model=ApiKeyResponse,
    status_code=201,
    summary="Créer une clé API",
    description="""
Crée une nouvelle clé API avec les permissions spécifiées.

⚠️ **IMPORTANT**: La clé complète n'est retournée qu'une seule fois lors de la création.
Assurez-vous de la sauvegarder immédiatement.

**Scopes disponibles**:
- `query`: Permet d'interroger le système RAG
- `ingest`: Permet d'ingérer des documents
- `feedback`: Permet de soumettre des feedbacks
- `admin`: Accès complet (gestion des clés)
    """,
    responses={
        201: {
            "description": "Clé créée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Production App",
                        "key": "rag_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                        "prefix": "rag_a1b2c3d4",
                        "scopes": ["query", "feedback"],
                        "rate_limit_per_minute": 100,
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        }
    },
)
async def create_api_key(
    request: ApiKeyCreate,
    _: bool = Depends(require_master_key),
) -> ApiKeyResponse:
    """
    Crée une nouvelle clé API.

    Nécessite la master key dans le header X-API-Key.
    """
    repo = get_repo()

    try:
        result = repo.create(
            {
                "name": request.name,
                "scopes": [s.value for s in request.scopes],
                "rate_limit_per_minute": request.rate_limit_per_minute,
                "monthly_quota": request.monthly_quota,
                "expires_in_days": request.expires_in_days,
                "metadata": request.metadata,
            }
        )

        logger.info(
            "API key created",
            name=request.name,
            scopes=request.scopes,
        )

        return ApiKeyResponse(
            id=result["id"],
            name=result["name"],
            key=result["key"],  # Retourné une seule fois!
            prefix=result["prefix"],
            scopes=result["scopes"],
            rate_limit_per_minute=result["rate_limit_per_minute"],
            monthly_quota=result.get("monthly_quota", 0),
            expires_at=result.get("expires_at"),
            is_active=True,
            created_at=result["created_at"],
        )

    except Exception as e:
        logger.error("Failed to create API key", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get(
    "",
    response_model=ApiKeyListResponse,
    summary="Lister les clés API",
    description="Retourne la liste paginée des clés API.",
)
async def list_api_keys(
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    per_page: int = Query(default=20, ge=1, le=100, description="Résultats par page"),
    include_inactive: bool = Query(default=False, description="Inclure les clés révoquées"),
    _: bool = Depends(require_master_key),
) -> ApiKeyListResponse:
    """
    Liste toutes les clés API avec pagination.

    Nécessite la master key ou le scope admin.
    """
    repo = get_repo()

    keys, total = repo.list_keys(
        page=page,
        per_page=per_page,
        include_inactive=include_inactive,
    )

    return ApiKeyListResponse(
        keys=keys,
        total=total,
        page=page,
        per_page=per_page,
    )


@admin_router.get(
    "/{key_id}",
    response_model=ApiKeyInfo,
    summary="Détails d'une clé",
    description="Retourne les informations détaillées d'une clé API.",
    responses={404: {"description": "Clé non trouvée"}},
)
async def get_api_key(
    key_id: UUID,
    _: bool = Depends(require_master_key),
) -> ApiKeyInfo:
    """
    Récupère les détails d'une clé API spécifique.
    """
    repo = get_repo()

    key = repo.get_by_id(str(key_id))

    if not key:
        raise HTTPException(
            status_code=404,
            detail={"error": "key_not_found", "message": "Clé API non trouvée."},
        )

    return key


@admin_router.delete(
    "/{key_id}",
    status_code=204,
    summary="Révoquer une clé",
    description="""
Révoque une clé API. La clé reste dans la base de données
mais devient inutilisable.

Cette action est irréversible depuis l'API.
    """,
    responses={
        204: {"description": "Clé révoquée avec succès"},
        404: {"description": "Clé non trouvée"},
    },
)
async def revoke_api_key(
    key_id: UUID,
    _: bool = Depends(require_master_key),
) -> None:
    """
    Révoque (désactive) une clé API.
    """
    repo = get_repo()

    # Vérifier que la clé existe
    key = repo.get_by_id(str(key_id))
    if not key:
        raise HTTPException(
            status_code=404,
            detail={"error": "key_not_found", "message": "Clé API non trouvée."},
        )

    success = repo.revoke(str(key_id))

    if not success:
        raise HTTPException(
            status_code=500,
            detail={"error": "revoke_failed", "message": "Échec de la révocation."},
        )

    logger.info("API key revoked", key_id=str(key_id), name=key.name)


@admin_router.get(
    "/{key_id}/stats",
    response_model=ApiKeyUsageStats,
    summary="Statistiques d'usage",
    description="Retourne les statistiques d'utilisation d'une clé API.",
    responses={404: {"description": "Clé non trouvée"}},
)
async def get_api_key_stats(
    key_id: UUID,
    days: int = Query(default=30, ge=1, le=365, description="Période en jours"),
    _: bool = Depends(require_master_key),
) -> ApiKeyUsageStats:
    """
    Récupère les statistiques d'utilisation d'une clé.
    """
    repo = get_repo()

    # Vérifier que la clé existe
    key = repo.get_by_id(str(key_id))
    if not key:
        raise HTTPException(
            status_code=404,
            detail={"error": "key_not_found", "message": "Clé API non trouvée."},
        )

    stats = repo.get_usage_stats(str(key_id), days)

    if stats is None:
        return ApiKeyUsageStats()

    return stats
