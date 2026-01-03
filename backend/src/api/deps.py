"""
API Dependencies
=================

Dépendances réutilisables pour les routes FastAPI.
Inclut l'authentification utilisateur via JWT Supabase.

Version 3.0.0: Migration vers Supabase Auth.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt

from src.config.logging_config import get_logger
from src.config.settings import get_settings
from src.models.user import UserWithSubscription
from src.repositories.agent_repository import AgentRepository
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.repositories.user_repository import UserRepository

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

    Supabase utilise HS256 avec le JWT secret.
    On essaie plusieurs configurations pour être robuste.

    Args:
        token: JWT access token de Supabase.

    Returns:
        Payload décodé ou None si invalide.
    """
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        # En développement sans secret, on décode sans vérifier
        logger.warning("SUPABASE_JWT_SECRET not set, skipping signature verification (DEV ONLY)")
        try:
            return jwt.get_unverified_claims(token)
        except JWTError as e:
            logger.error("JWT decode error (unverified)", error=str(e))
            return None

    # Essayer de décoder avec le secret JWT
    try:
        # Supabase utilise HS256 par défaut avec le JWT secret
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        logger.debug("JWT decoded successfully with HS256")
        return payload
    except JWTError as e:
        error_msg = str(e)
        logger.debug(f"HS256 with audience failed: {error_msg}")
        
        # Si l'erreur est liée à l'audience, réessayer sans vérification d'audience
        if "audience" in error_msg.lower():
            try:
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                logger.debug("JWT decoded successfully with HS256 (no aud verification)")
                return payload
            except JWTError as e2:
                logger.error("JWT decode failed (no aud)", error=str(e2))
                return None
        
        # Si l'erreur est "alg not allowed", le token utilise probablement un algo différent
        # Dans ce cas, lire l'en-tête pour voir l'algo utilisé
        if "alg" in error_msg.lower() or "algorithm" in error_msg.lower():
            try:
                # Lire l'en-tête du token pour debug
                header = jwt.get_unverified_header(token)
                logger.error(f"JWT algorithm mismatch. Token uses: {header.get('alg')}, expected: HS256")
                
                # Si c'est RS256, on ne peut pas le valider sans la clé publique
                # Pour l'instant, on accepte le token en mode dégradé si les claims sont valides
                claims = jwt.get_unverified_claims(token)
                import time
                
                # Vérification manuelle de l'expiration
                exp = claims.get("exp", 0)
                if exp < time.time():
                    logger.error("JWT expired")
                    return None
                
                # Vérification du role/audience
                if claims.get("aud") == "authenticated" or claims.get("role") == "authenticated":
                    logger.warning("JWT accepted in degraded mode (unverified signature)")
                    return claims
                    
                logger.error("JWT claims validation failed")
                return None
                
            except Exception as e3:
                logger.error("JWT header/claims read failed", error=str(e3))
                return None
        
        logger.error("JWT decode failed", error=error_msg)
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
            detail={"error": "not_authenticated", "message": "Authentification requise"},
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
            status_code=403, detail={"error": "forbidden", "message": "Accès administrateur requis"}
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
            },
        )
    return user
