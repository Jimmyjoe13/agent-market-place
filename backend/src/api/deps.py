"""
API Dependencies
=================

Dépendances réutilisables pour les routes FastAPI.
Inclut l'authentification utilisateur via JWT Supabase.

Version 3.0.0: Migration vers Supabase Auth.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError

from src.config.settings import get_settings
from src.config.logging_config import get_logger
from src.repositories.user_repository import UserRepository
from src.repositories.agent_repository import AgentRepository
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.models.user import UserWithSubscription

logger = get_logger(__name__)

# Repository singletons
_user_repo: UserRepository | None = None
_agent_repo: AgentRepository | None = None
_api_key_repo: ApiKeyRepository | None = None
_subscription_repo: SubscriptionRepository | None = None


def get_user_repo() -> UserRepository:
    """Retourne le singleton UserRepository."""
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo


def get_agent_repo() -> AgentRepository:
    """Retourne le singleton AgentRepository."""
    global _agent_repo
    if _agent_repo is None:
        _agent_repo = AgentRepository()
    return _agent_repo


def get_api_key_repo() -> ApiKeyRepository:
    """Retourne le singleton ApiKeyRepository."""
    global _api_key_repo
    if _api_key_repo is None:
        _api_key_repo = ApiKeyRepository()
    return _api_key_repo


def get_subscription_repo() -> SubscriptionRepository:
    """Retourne le singleton SubscriptionRepository."""
    global _subscription_repo
    if _subscription_repo is None:
        _subscription_repo = SubscriptionRepository()
    return _subscription_repo


def decode_supabase_jwt(token: str) -> dict | None:
    """
    Décode et valide un JWT Supabase.
    
    Args:
        token: JWT access token de Supabase.
        
    Returns:
        Payload décodé ou None si invalide.
    """
    settings = get_settings()
    
    try:
        # En production, on valide la signature avec le secret JWT
        if settings.supabase_jwt_secret:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            # En développement sans secret, on décode sans vérifier
            logger.warning("SUPABASE_JWT_SECRET not set, skipping signature verification")
            payload = jwt.get_unverified_claims(token)
        
        return payload
    
    except JWTError as e:
        logger.error("JWT decode error", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected JWT error", error=str(e))
        return None


async def get_current_user(
    request: Request,
) -> UserWithSubscription:
    """
    Récupère l'utilisateur authentifié via le token JWT Supabase.
    
    Le token est extrait du header Authorization: Bearer <token>.
    L'utilisateur est identifié par son 'sub' (= user ID Supabase = profile ID).
    """
    repo = get_user_repo()
    
    # 1. Extraire le token du header Authorization
    auth_header = request.headers.get("Authorization")
    user_id: str | None = None
    user_email: str | None = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_supabase_jwt(token)
        
        if payload:
            # 'sub' contient l'UUID de l'utilisateur Supabase
            user_id = payload.get("sub")
            user_email = payload.get("email")
            
            if not user_id:
                logger.warning("JWT valid but no 'sub' claim found")
    
    # 2. Fallback: header X-User-ID (pour tests ou admin bypass)
    if not user_id:
        user_id = request.headers.get("X-User-ID")
    
    # 3. Récupérer l'utilisateur
    user = None
    
    if user_id:
        user = repo.get_user_with_subscription(user_id)
    elif user_email:
        # Fallback par email si pas de user_id
        user_info = repo.get_by_email(user_email)
        if user_info:
            user = repo.get_user_with_subscription(str(user_info.id))
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "not_authenticated", "message": "Authentification requise"}
        )
    
    return user


# Alias pour injecter l'utilisateur
CurrentUser = Annotated[UserWithSubscription, Depends(get_current_user)]


async def require_admin_user(
    user: CurrentUser,
) -> UserWithSubscription:
    """Vérifie que l'utilisateur a le rôle admin."""
    if user.role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "Accès administrateur requis"}
        )
    return user


async def require_pro_plan(
    user: CurrentUser,
) -> UserWithSubscription:
    """Vérifie que l'utilisateur a un plan Pro ou supérieur."""
    if user.plan_slug not in ["pro", "enterprise"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "plan_required",
                "message": "Cette fonctionnalité nécessite un plan Pro ou Enterprise",
                "current_plan": user.plan_slug,
            }
        )
    return user
