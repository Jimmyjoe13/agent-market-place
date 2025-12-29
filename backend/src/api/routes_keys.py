"""
API Routes - Key Management
============================

Endpoints pour la gestion avancée des clés API:
- Rotation de clé (régénération sans perte de données)
- Configuration des limites de budget
- Statistiques d'utilisation
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import require_scope, ApiKeyValidation
from src.config.logging_config import get_logger
from src.repositories.api_key_repository import ApiKeyRepository
from src.services.rate_limiter import get_rate_limiter

logger = get_logger(__name__)
router = APIRouter(prefix="/keys", tags=["Key Management"])


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


class BudgetLimitsUpdate(BaseModel):
    """Mise à jour des limites de budget."""
    max_monthly_tokens: Optional[int] = Field(
        None, 
        ge=0, 
        description="Limite tokens/mois (0 = illimité)"
    )
    max_daily_requests: Optional[int] = Field(
        None, 
        ge=0, 
        description="Limite requêtes/jour (0 = illimité)"
    )
    system_prompt_max_length: Optional[int] = Field(
        None, 
        ge=100, 
        le=32000,
        description="Taille max du prompt système (100-32000)"
    )


class BudgetLimitsResponse(BaseModel):
    """Réponse avec les limites de budget."""
    max_monthly_tokens: int
    max_daily_requests: int
    tokens_used_this_month: int
    requests_today: int
    system_prompt_max_length: int
    usage_percent: float = Field(..., description="Pourcentage d'utilisation tokens")


class UsageStatsResponse(BaseModel):
    """Statistiques d'utilisation."""
    key_id: str
    agent_name: Optional[str]
    tokens_used_this_month: int
    max_monthly_tokens: int
    requests_today: int
    max_daily_requests: int
    rate_limit_stats: dict
    usage_reset_month: Optional[str]
    daily_reset_date: Optional[str]


# ============================================
# Dependencies
# ============================================

def get_key_repo() -> ApiKeyRepository:
    """Retourne une instance du repository."""
    return ApiKeyRepository()


# ============================================
# Helper Functions
# ============================================

def generate_api_key() -> str:
    """Génère une nouvelle clé API sécurisée."""
    # Format: rag_<32 caractères hex>
    random_bytes = secrets.token_bytes(16)
    return f"rag_{random_bytes.hex()}"


def hash_api_key(key: str) -> str:
    """Hash une clé API avec SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


# ============================================
# Endpoints
# ============================================

@router.post("/{key_id}/rotate", response_model=KeyRotateResponse)
async def rotate_api_key(
    key_id: str,
    api_key: ApiKeyValidation = Depends(require_scope("admin")),
    repo: ApiKeyRepository = Depends(get_key_repo),
):
    """
    Régénère une clé API sans perdre la configuration ni les documents.
    
    Cette opération:
    - Génère une nouvelle clé avec un nouveau hash
    - Invalide immédiatement l'ancienne clé
    - Préserve tous les documents et configurations de l'agent
    
    ⚠️ La nouvelle clé ne sera affichée qu'une seule fois.
    """
    try:
        # Vérifier que la clé appartient à l'utilisateur
        key_data = repo.get_by_id(key_id)
        
        if not key_data or str(key_data.get("user_id")) != str(api_key.user_id):
            raise HTTPException(
                status_code=404,
                detail="Clé API non trouvée ou accès non autorisé"
            )
        
        # Générer nouvelle clé
        new_key = generate_api_key()
        new_hash = hash_api_key(new_key)
        
        # Mettre à jour le hash (garde le même ID!)
        repo.client.table("api_keys").update({
            "key_hash": new_hash,
            "last_rotated_at": datetime.utcnow().isoformat(),
        }).eq("id", key_id).execute()
        
        logger.info(
            "API key rotated",
            key_id=key_id,
            user_id=str(api_key.user_id)
        )
        
        return KeyRotateResponse(
            new_key=new_key,
            key_id=key_id,
            rotated_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Key rotation failed", error=str(e), key_id=key_id)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la rotation de la clé"
        )


@router.get("/{key_id}/budget", response_model=BudgetLimitsResponse)
async def get_budget_limits(
    key_id: str,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
    repo: ApiKeyRepository = Depends(get_key_repo),
):
    """
    Récupère les limites de budget et l'utilisation actuelle.
    """
    try:
        result = repo.client.table("api_keys").select(
            "max_monthly_tokens",
            "max_daily_requests",
            "tokens_used_this_month",
            "requests_today",
            "system_prompt_max_length",
            "user_id"
        ).eq("id", key_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Clé non trouvée")
        
        data = result.data
        
        # Vérifier la propriété
        if str(data.get("user_id")) != str(api_key.user_id):
            raise HTTPException(status_code=404, detail="Clé non trouvée")
        
        # Calcul du pourcentage d'utilisation
        max_tokens = data.get("max_monthly_tokens") or 0
        used_tokens = data.get("tokens_used_this_month") or 0
        usage_percent = (used_tokens / max_tokens * 100) if max_tokens > 0 else 0
        
        return BudgetLimitsResponse(
            max_monthly_tokens=max_tokens,
            max_daily_requests=data.get("max_daily_requests") or 0,
            tokens_used_this_month=used_tokens,
            requests_today=data.get("requests_today") or 0,
            system_prompt_max_length=data.get("system_prompt_max_length") or 4000,
            usage_percent=round(usage_percent, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get budget limits failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.patch("/{key_id}/budget", response_model=BudgetLimitsResponse)
async def update_budget_limits(
    key_id: str,
    limits: BudgetLimitsUpdate,
    api_key: ApiKeyValidation = Depends(require_scope("admin")),
    repo: ApiKeyRepository = Depends(get_key_repo),
):
    """
    Met à jour les limites de budget d'une clé API.
    
    Seuls les champs fournis sont mis à jour.
    """
    try:
        # Vérifier propriété
        key_data = repo.get_by_id(key_id)
        if not key_data or str(key_data.get("user_id")) != str(api_key.user_id):
            raise HTTPException(status_code=404, detail="Clé non trouvée")
        
        # Construire les champs à mettre à jour
        update_data = {}
        if limits.max_monthly_tokens is not None:
            update_data["max_monthly_tokens"] = limits.max_monthly_tokens
        if limits.max_daily_requests is not None:
            update_data["max_daily_requests"] = limits.max_daily_requests
        if limits.system_prompt_max_length is not None:
            update_data["system_prompt_max_length"] = limits.system_prompt_max_length
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Aucun champ à mettre à jour"
            )
        
        # Mettre à jour
        repo.client.table("api_keys").update(update_data).eq("id", key_id).execute()
        
        # Retourner les nouvelles valeurs
        return await get_budget_limits(key_id, api_key, repo)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update budget limits failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{key_id}/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    key_id: str,
    api_key: ApiKeyValidation = Depends(require_scope("query")),
    repo: ApiKeyRepository = Depends(get_key_repo),
):
    """
    Récupère les statistiques d'utilisation détaillées.
    
    Inclut:
    - Tokens utilisés ce mois
    - Requêtes aujourd'hui
    - Stats rate limiting en temps réel
    """
    try:
        rate_limiter = get_rate_limiter()
        
        # Données DB
        result = repo.client.table("api_keys").select(
            "id",
            "agent_name",
            "tokens_used_this_month",
            "max_monthly_tokens",
            "requests_today",
            "max_daily_requests",
            "usage_reset_month",
            "daily_reset_date",
            "user_id"
        ).eq("id", key_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Clé non trouvée")
        
        data = result.data
        
        # Vérifier propriété
        if str(data.get("user_id")) != str(api_key.user_id):
            raise HTTPException(status_code=404, detail="Clé non trouvée")
        
        # Stats rate limiting temps réel
        rate_stats = await rate_limiter.get_usage_stats(key_id)
        
        return UsageStatsResponse(
            key_id=key_id,
            agent_name=data.get("agent_name"),
            tokens_used_this_month=data.get("tokens_used_this_month") or 0,
            max_monthly_tokens=data.get("max_monthly_tokens") or 0,
            requests_today=data.get("requests_today") or 0,
            max_daily_requests=data.get("max_daily_requests") or 0,
            rate_limit_stats=rate_stats,
            usage_reset_month=data.get("usage_reset_month"),
            daily_reset_date=str(data.get("daily_reset_date")) if data.get("daily_reset_date") else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get usage stats failed", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur")
