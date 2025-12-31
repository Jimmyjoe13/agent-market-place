"""
API Routes - Key Management
============================

Endpoints pour la gestion des clés API:
- CRUD des clés API (liées à un agent)
- Rotation de clé
- Statistiques d'utilisation

Architecture v2:
- Chaque clé API est liée à un agent
- Les limites de budget sont sur l'agent
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_agent_repo, get_api_key_repo
from src.config.logging_config import get_logger
from src.models.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo, ApiKeyListResponse
from src.models.user import UserWithSubscription
from src.repositories.agent_repository import AgentRepository
from src.repositories.api_key_repository import ApiKeyRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/keys", tags=["API Keys"])


# ============================================
# Schemas
# ============================================

class KeyRotateResponse(BaseModel):
    """Réponse après rotation de clé."""
    new_key: str = Field(..., description="Nouvelle clé API (à stocker immédiatement)")
    key_id: str = Field(..., description="ID de la clé (inchangé)")
    rotated_at: datetime = Field(..., description="Date/heure de la rotation")
    warning: str = Field(
        default="Cette clé ne sera plus affichée. Stockez-la dans un endroit sécurisé.",
        description="Message d'avertissement"
    )


class UsageStatsResponse(BaseModel):
    """Statistiques d'utilisation."""
    key_id: str
    agent_id: str
    agent_name: Optional[str]
    total_requests: int
    avg_response_time: Optional[float]
    error_rate: float
    requests_by_day: dict


# ============================================
# CRUD Endpoints
# ============================================

@router.get("", response_model=ApiKeyListResponse)
async def list_keys(
    agent_id: UUID | None = None,
    page: int = 1,
    per_page: int = 20,
    user: UserWithSubscription = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Liste les clés API de l'utilisateur.
    
    Args:
        agent_id: Filtrer par agent (optionnel).
        page: Numéro de page.
        per_page: Résultats par page.
        
    Returns:
        Liste des clés API.
    """
    keys, total = repo.list_keys(
        user_id=str(user.id),
        agent_id=str(agent_id) if agent_id else None,
        page=page,
        per_page=per_page,
    )
    
    return ApiKeyListResponse(
        keys=keys,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    key_data: ApiKeyCreate,
    user: UserWithSubscription = Depends(get_current_user),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repo),
    agent_repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Crée une nouvelle clé API.
    
    Si agent_id n'est pas fourni, utilise l'agent par défaut de l'utilisateur
    (ou en crée un si aucun n'existe).
    
    ⚠️ La clé complète n'est retournée qu'une seule fois.
    
    Args:
        key_data: Configuration de la clé.
        
    Returns:
        Clé API créée avec le secret.
    """
    # Vérifier la limite de clés API
    current_count = api_key_repo.count_user_keys(str(user.id))
    if user.api_keys_limit > 0 and current_count >= user.api_keys_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "api_keys_limit_reached",
                "message": f"Limite de {user.api_keys_limit} clés API atteinte. Passez au plan supérieur.",
                "current": current_count,
                "limit": user.api_keys_limit,
            }
        )
    
    # Déterminer l'agent
    if key_data.agent_id:
        # Vérifier que l'agent existe et appartient à l'utilisateur
        agent = agent_repo.get_by_id(str(key_data.agent_id))
        if not agent or agent.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        agent_id = str(key_data.agent_id)
    else:
        # Utiliser ou créer l'agent par défaut
        agent = agent_repo.get_or_create_default_agent(str(user.id))
        agent_id = str(agent.id)
    
    # Créer la clé
    result = api_key_repo.create({
        "name": key_data.name,
        "agent_id": agent_id,
        "user_id": str(user.id),
        "scopes": [s.value for s in key_data.scopes],
        "rate_limit_per_minute": key_data.rate_limit_per_minute,
        "expires_in_days": key_data.expires_in_days,
    })
    
    logger.info(
        "API key created",
        key_id=result["id"],
        agent_id=agent_id,
        user_id=str(user.id),
    )
    
    return ApiKeyResponse(
        id=result["id"],
        agent_id=agent_id,
        name=result["name"],
        key=result["key"],
        prefix=result["prefix"],
        scopes=result["scopes"],
        rate_limit_per_minute=result["rate_limit_per_minute"],
        expires_at=result.get("expires_at"),
        is_active=result["is_active"],
        created_at=result["created_at"],
    )


@router.get("/{key_id}", response_model=ApiKeyInfo)
async def get_key(
    key_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Récupère les détails d'une clé API.
    
    Args:
        key_id: UUID de la clé.
        
    Returns:
        Informations de la clé (sans le secret).
    """
    key = repo.get_by_id(str(key_id))
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found",
        )
    
    # Vérifier la propriété via user_id sur la clé ou l'agent
    # Note: le user_id est maintenant sur la clé directement
    keys, _ = repo.list_keys(user_id=str(user.id))
    if not any(k.id == key.id for k in keys):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found",
        )
    
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Révoque une clé API (désactivation, pas suppression).
    
    Args:
        key_id: UUID de la clé.
    """
    # Vérifier la propriété
    keys, _ = repo.list_keys(user_id=str(user.id), include_inactive=True)
    if not any(str(k.id) == str(key_id) for k in keys):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found",
        )
    
    success = repo.revoke(str(key_id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke key",
        )
    
    logger.info("API key revoked", key_id=str(key_id), user_id=str(user.id))


# ============================================
# Advanced Operations
# ============================================

@router.post("/{key_id}/rotate", response_model=KeyRotateResponse)
async def rotate_key(
    key_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Régénère une clé API sans perdre la configuration.
    
    Cette opération:
    - Génère une nouvelle clé avec un nouveau hash
    - Invalide immédiatement l'ancienne clé
    - Préserve tous les paramètres et l'agent associé
    
    ⚠️ La nouvelle clé ne sera affichée qu'une seule fois.
    """
    # Vérifier la propriété
    keys, _ = repo.list_keys(user_id=str(user.id))
    key = next((k for k in keys if str(k.id) == str(key_id)), None)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found",
        )
    
    try:
        # Générer nouvelle clé
        random_part = secrets.token_hex(16)
        new_key = f"sk-proj-{random_part}"
        new_hash = hashlib.sha256(new_key.encode()).hexdigest()
        new_prefix = new_key[:12]
        
        # Mettre à jour le hash
        repo.table.update({
            "key_hash": new_hash,
            "key_prefix": new_prefix,
        }).eq("id", str(key_id)).execute()
        
        logger.info("API key rotated", key_id=str(key_id), user_id=str(user.id))
        
        return KeyRotateResponse(
            new_key=new_key,
            key_id=str(key_id),
            rotated_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error("Key rotation failed", error=str(e), key_id=str(key_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate key",
        )


@router.get("/{key_id}/usage", response_model=UsageStatsResponse)
async def get_key_usage(
    key_id: UUID,
    days: int = 30,
    user: UserWithSubscription = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Récupère les statistiques d'utilisation d'une clé.
    
    Args:
        key_id: UUID de la clé.
        days: Période en jours (défaut: 30).
        
    Returns:
        Statistiques d'utilisation.
    """
    # Vérifier la propriété
    keys, _ = repo.list_keys(user_id=str(user.id))
    key = next((k for k in keys if str(k.id) == str(key_id)), None)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found",
        )
    
    stats = repo.get_usage_stats(str(key_id), days=days)
    
    return UsageStatsResponse(
        key_id=str(key_id),
        agent_id=str(key.agent_id),
        agent_name=key.agent_name,
        total_requests=stats.total_requests if stats else 0,
        avg_response_time=stats.avg_response_time if stats else None,
        error_rate=stats.error_rate if stats else 0,
        requests_by_day=stats.requests_by_day if stats else {},
    )
