"""
Authentication Routes
======================

Endpoints FastAPI pour l'authentification Supabase.

Ce module fournit :
- Sync utilisateur depuis Supabase Auth
- Récupération du profil utilisateur (/me)
- Logout et refresh de session

Version 3.0.0: Migration vers Supabase Auth.
L'authentification OAuth est gérée par Supabase côté frontend.
Le backend valide les JWT et gère les profils.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.config.logging_config import get_logger
from src.config.settings import get_settings
from src.models.user import (
    UserInfo,
    UserWithSubscription,
    UserUpdate,
    SessionInfo,
)
from src.repositories.user_repository import UserRepository
from src.api.deps import get_user_repo, get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ===== Schemas =====

class UserSyncRequest(BaseModel):
    """Requête de synchronisation utilisateur depuis le frontend."""
    
    email: str = Field(..., description="Email de l'utilisateur")
    name: str | None = Field(default=None, description="Nom d'affichage")
    avatar_url: str | None = Field(default=None, description="URL de l'avatar")
    provider: str = Field(default="email", description="Provider OAuth ou 'email'")
    provider_id: str | None = Field(default=None, description="ID du provider")


class UserSyncResponse(BaseModel):
    """Réponse de synchronisation utilisateur."""
    
    success: bool
    user: UserInfo | None = None
    message: str | None = None


# ===== Auth Sync Endpoint =====

@router.post("/sync", response_model=UserSyncResponse)
async def sync_user(
    request: UserSyncRequest,
    repo: UserRepository = Depends(get_user_repo),
) -> UserSyncResponse:
    """
    Synchronise un utilisateur depuis Supabase Auth.
    
    Appelé par le frontend après authentification OAuth ou inscription.
    Le trigger Supabase devrait déjà avoir créé le profile, mais
    cette route permet de s'assurer que le profile existe et est à jour.
    
    Note: Cette route est protégée par le JWT Supabase envoyé dans le header.
    """
    try:
        user = repo.get_or_create_oauth_user(
            email=request.email,
            name=request.name,
            provider=request.provider,
            provider_id=request.provider_id or request.email,
            avatar_url=request.avatar_url,
        )
        
        logger.info(
            "User synced from Supabase",
            user_id=str(user.id),
            email=user.email,
            provider=request.provider,
        )
        
        return UserSyncResponse(
            success=True,
            user=user,
            message="Utilisateur synchronisé avec succès",
        )
        
    except Exception as e:
        logger.error("User sync failed", email=request.email, error=str(e))
        return UserSyncResponse(
            success=False,
            message="Erreur lors de la synchronisation",
        )


# ===== Profile Endpoints =====

@router.get("/me", response_model=UserWithSubscription)
async def me(
    user: UserWithSubscription = Depends(get_current_user),
) -> UserWithSubscription:
    """
    Récupère le profil de l'utilisateur connecté.
    
    Nécessite un JWT Supabase valide dans le header Authorization.
    """
    return user


@router.patch("/me", response_model=UserInfo)
async def update_me(
    update_data: UserUpdate,
    user: UserWithSubscription = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
) -> UserInfo:
    """
    Met à jour le profil de l'utilisateur connecté.
    """
    updated_user = repo.update_profile(
        user_id=str(user.id),
        name=update_data.name,
        avatar_url=update_data.avatar_url,
        provider_keys=update_data.provider_keys,
    )
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du profil")
        
    return updated_user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
) -> dict[str, str]:
    """
    Déconnecte l'utilisateur.
    
    Note: Le frontend gère la déconnexion Supabase.
    Cette route est principalement pour invalider les caches côté serveur si nécessaire.
    """
    logger.info("User logged out")
    return {"message": "Déconnexion réussie"}


@router.get("/session", response_model=SessionInfo | None)
async def get_session(
    request: Request,
) -> SessionInfo | None:
    """
    Vérifie si l'utilisateur a une session active.
    
    Returns:
        SessionInfo si connecté, None sinon.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        from src.api.deps import decode_supabase_jwt
        
        token = auth_header.split(" ")[1]
        payload = decode_supabase_jwt(token)
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        repo = get_user_repo()
        user = repo.get_user_with_subscription(user_id)
        
        if not user:
            return None
        
        return SessionInfo(
            user_id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
            plan_slug=user.plan_slug,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        
    except Exception as e:
        logger.error("Session check failed", error=str(e))
        return None


# ===== Plans Endpoints (publics) =====

@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """
    Liste les plans d'abonnement disponibles.
    
    Endpoint public pour la page pricing.
    """
    from src.repositories.subscription_repository import SubscriptionRepository
    
    repo = SubscriptionRepository()
    plans = repo.list_plans()
    
    return {
        "plans": [p.model_dump() for p in plans],
    }
