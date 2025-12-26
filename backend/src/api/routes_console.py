"""
Console Routes
===============

Endpoints pour la console développeur (Self-Service).
Accessibles aux utilisateurs authentifiés via Session.

Prefix: /api/v1/console
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import CurrentUser
from src.config.logging_config import get_logger
from src.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyListResponse,
)
from src.services.api_key_service import (
    ApiKeyService,
    QuotaExceededError,
    get_api_key_service,
)
from src.repositories.subscription_repository import SubscriptionRepository

logger = get_logger(__name__)

router = APIRouter(
    prefix="/console",
    tags=["Console Developer"],
)

# ===== Dependencies =====

def get_sub_repo() -> SubscriptionRepository:
    return SubscriptionRepository()

# ===== API Keys Endpoints =====

@router.get(
    "/keys",
    response_model=ApiKeyListResponse,
    summary="Mes clés API",
)
async def list_my_keys(
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = False,
    service: ApiKeyService = Depends(get_api_key_service),
) -> ApiKeyListResponse:
    """Liste les clés API de l'utilisateur courant."""
    keys, total = service.list_user_keys(
        user_id=str(user.id),
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

@router.post(
    "/keys",
    response_model=ApiKeyResponse,
    status_code=201,
    summary="Créer une clé API",
)
async def create_my_key(
    request: ApiKeyCreate,
    user: CurrentUser,
    service: ApiKeyService = Depends(get_api_key_service),
) -> ApiKeyResponse:
    """
    Crée une nouvelle clé API pour l'utilisateur courant.
    
    ⚠️ IMPORTANT: La clé complète n'est retournée qu'une seule fois.
    Sauvegardez-la immédiatement, elle ne sera plus jamais affichée.
    """
    try:
        # Convertir les scopes enum en strings si nécessaire
        scopes = [
            s.value if hasattr(s, 'value') else str(s) 
            for s in request.scopes
        ]
        
        result = await service.create_user_key(
            user_id=str(user.id),
            name=request.name,
            scopes=scopes,
            rate_limit_per_minute=request.rate_limit_per_minute,
            monthly_quota=request.monthly_quota,
            expires_in_days=request.expires_in_days,
            metadata=request.metadata,
        )
        
        return ApiKeyResponse(
            id=result.key_info.id,
            name=result.key_info.name,
            key=result.raw_key,  # Clé complète, une seule fois!
            prefix=result.key_info.prefix,
            scopes=result.key_info.scopes,
            rate_limit_per_minute=result.key_info.rate_limit_per_minute,
            monthly_quota=result.key_info.monthly_quota,
            is_active=result.key_info.is_active,
            expires_at=result.key_info.expires_at,
            created_at=result.key_info.created_at,
        )
        
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "quota_exceeded",
                "message": e.message,
                "limits": e.limits,
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "message": str(e),
            }
        )
    except Exception as e:
        logger.error("Failed to create user key", error=str(e), user_id=str(user.id))
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error",
                "message": "Erreur lors de la création de la clé",
            }
        )

@router.delete(
    "/keys/{key_id}",
    status_code=204,
    summary="Révoquer une clé",
)
async def revoke_my_key(
    key_id: UUID,
    user: CurrentUser,
    service: ApiKeyService = Depends(get_api_key_service),
) -> None:
    """Révoque une clé appartenant à l'utilisateur."""
    success = service.revoke_user_key(
        user_id=str(user.id),
        key_id=str(key_id),
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "not_found",
                "message": "Clé introuvable ou déjà révoquée",
            }
        )

@router.get(
    "/keys/{key_id}/stats",
    summary="Statistiques d'une clé",
)
async def get_key_stats(
    key_id: UUID,
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
    service: ApiKeyService = Depends(get_api_key_service),
):
    """Récupère les statistiques d'utilisation d'une clé."""
    stats = service.get_key_stats(str(key_id), days)
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": "Clé introuvable ou pas de statistiques",
            }
        )
    
    return stats

# ===== Usage Endpoint =====

@router.get("/usage", summary="Mon usage")
async def get_my_usage(
    user: CurrentUser,
):
    """Récupère les statistiques d'usage de l'utilisateur."""
    sub_repo = get_sub_repo()
    usage = sub_repo.get_user_usage(str(user.id))
    
    if not usage:
        return {
            "period": "current",
            "requests_count": 0,
            "requests_limit": user.requests_limit,
            "plan": user.plan_slug,
        }
        
    return usage
