"""
Agent Configuration Routes
============================

Routes API pour la mise à jour de la configuration agent.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import require_api_key
from src.config.logging_config import get_logger
from src.models.api_key import AgentConfig, AgentConfigUpdate, ApiKeyValidation
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.models.subscription import PlanSlug

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["Agent Configuration"],
)


# Response model pour la config
class AgentConfigResponse(BaseModel):
    """Réponse avec la configuration agent."""
    
    agent_id: str = Field(..., description="ID de la clé API/agent")
    config: AgentConfig = Field(..., description="Configuration actuelle")


# Repositories
_agent_repo: ApiKeyRepository | None = None
_sub_repo: SubscriptionRepository | None = None


def get_agent_repo() -> ApiKeyRepository:
    """Retourne le repository API keys."""
    global _agent_repo
    if _agent_repo is None:
        _agent_repo = ApiKeyRepository()
    return _agent_repo


def get_sub_repo() -> SubscriptionRepository:
    """Retourne le repository subscriptions."""
    global _sub_repo
    if _sub_repo is None:
        _sub_repo = SubscriptionRepository()
    return _sub_repo


# Modèles nécessitant un abonnement PREMIUM
PREMIUM_MODELS = [
    # OpenAI Premium
    "gpt-5.2", "gpt-5.2-pro", "gpt-5.1", "gpt-5.1-codex-max",
    "o3-deep-research", "o3-pro", "o4-mini-deep-research", "o1-pro",
    # Deepseek Premium
    "deepseek-reasoner"
]


@router.get(
    "/config",
    response_model=AgentConfigResponse,
    summary="Récupérer la configuration agent",
)
async def get_agent_config(
    api_key: ApiKeyValidation = Depends(require_api_key),
) -> AgentConfigResponse:
    """
    Retourne la configuration actuelle de l'agent associé à la clé API.
    
    La clé API utilisée pour l'authentification détermine l'agent.
    """
    if not api_key.agent_config:
        # Fallback sur valeurs par défaut
        config = AgentConfig()
    else:
        config = api_key.agent_config
    
    return AgentConfigResponse(
        agent_id=str(api_key.id),
        config=config,
    )


@router.patch(
    "/config",
    response_model=AgentConfigResponse,
    summary="Mettre à jour la configuration agent",
)
async def update_agent_config(
    update: AgentConfigUpdate,
    api_key: ApiKeyValidation = Depends(require_api_key),
    repo: ApiKeyRepository = Depends(get_agent_repo),
) -> AgentConfigResponse:
    """
    Met à jour la configuration de l'agent.
    
    Seuls les champs fournis sont mis à jour (PATCH sémantique).
    
    Champs modifiables:
    - **model_id**: Modèle LLM (mistral-large-latest, gpt-4o, deepseek-chat, etc.)
    - **system_prompt**: Prompt système personnalisé
    - **rag_enabled**: Activer/désactiver la recherche RAG
    - **agent_name**: Nom affiché de l'agent
    """
    if not api_key.id:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_key", "message": "Clé API invalide"},
        )
    
    # Construire les données à mettre à jour
    update_data = {}
    
    if update.model_id is not None:
        # Vérifier si c'est un modèle premium
        if update.model_id in PREMIUM_MODELS:
            # Vérifier l'abonnement du propriétaire de la clé
            sub_repo = get_sub_repo()
            subscription = sub_repo.get_user_subscription(str(api_key.user_id))
            
            is_premium = (
                subscription is not None and 
                subscription.plan.slug != PlanSlug.FREE
            )
            
            if not is_premium:
                logger.warning(
                    "Premium model access denied",
                    user_id=str(api_key.user_id),
                    model_id=update.model_id
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "premium_required",
                        "message": f"Le modèle {update.model_id} nécessite un abonnement PRO."
                    }
                )
        
        update_data["model_id"] = update.model_id
    
    if update.system_prompt is not None:
        update_data["system_prompt"] = update.system_prompt
    
    if update.rag_enabled is not None:
        update_data["rag_enabled"] = update.rag_enabled
    
    if update.agent_name is not None:
        update_data["agent_name"] = update.agent_name
    
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail={"error": "no_changes", "message": "Aucun champ à mettre à jour"},
        )
    
    # Exécuter la mise à jour
    try:
        repo.table.update(update_data).eq("id", str(api_key.id)).execute()
        
        logger.info(
            "Agent config updated",
            agent_id=str(api_key.id),
            updated_fields=list(update_data.keys()),
        )
        
        # Construire la nouvelle config
        current = api_key.agent_config or AgentConfig()
        new_config = AgentConfig(
            model_id=update_data.get("model_id", current.model_id),
            system_prompt=update_data.get("system_prompt", current.system_prompt),
            rag_enabled=update_data.get("rag_enabled", current.rag_enabled),
            agent_name=update_data.get("agent_name", current.agent_name),
        )
        
        return AgentConfigResponse(
            agent_id=str(api_key.id),
            config=new_config,
        )
        
    except Exception as e:
        logger.error("Failed to update agent config", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": "update_failed", "message": "Échec de la mise à jour"},
        )


@router.get(
    "/available-models",
    summary="Liste des modèles LLM disponibles",
)
async def list_available_models() -> dict:
    """
    Retourne la liste des modèles LLM disponibles pour configuration.
    
    Inclut les providers: Mistral, OpenAI, Deepseek.
    """
    return {
        "models": [
            # === MISTRAL ===
            {"id": "mistral-large-latest", "provider": "mistral", "name": "Mistral Large", "description": "Flagship Mistral", "recommended": True, "premium": False},
            {"id": "mistral-medium-latest", "provider": "mistral", "name": "Mistral Medium", "description": "Balanced", "premium": False},
            {"id": "mistral-small-latest", "provider": "mistral", "name": "Mistral Small", "description": "Fast & cheap", "premium": False},
            
            # === OPENAI - GPT-5.2 Series (Premium) ===
            {"id": "gpt-5.2", "provider": "openai", "name": "GPT-5.2", "description": "State-of-the-art agentic & coding", "recommended": True, "premium": True, "new": True},
            {"id": "gpt-5.2-pro", "provider": "openai", "name": "GPT-5.2 Pro", "description": "Maximum intelligence", "premium": True, "new": True},
            
            # === OPENAI - GPT-5.1 Series (Premium) ===
            {"id": "gpt-5.1", "provider": "openai", "name": "GPT-5.1", "description": "Advanced reasoning", "premium": True},
            {"id": "gpt-5.1-codex-max", "provider": "openai", "name": "GPT-5.1 Codex Max", "description": "Best for software engineering", "premium": True},
            
            # === OPENAI - O-Series (Premium) ===
            {"id": "o3-deep-research", "provider": "openai", "name": "o3 Deep Research", "description": "Autonomous research agent", "premium": True, "new": True},
            {"id": "o3-pro", "provider": "openai", "name": "o3-pro", "description": "Reasoning flagship", "premium": True},
            {"id": "o4-mini-deep-research", "provider": "openai", "name": "o4-mini Deep Research", "description": "Fast research", "premium": True, "new": True},
            {"id": "o1-pro", "provider": "openai", "name": "o1-pro", "description": "Legacy reasoning flagship", "premium": True},
            
            # === OPENAI - GPT-5 Series (Standard) ===
            {"id": "gpt-5", "provider": "openai", "name": "GPT-5", "description": "Standard intelligence", "premium": False, "new": True},
            {"id": "gpt-5-mini", "provider": "openai", "name": "GPT-5 Mini", "description": "Balanced & cost-effective", "premium": False, "new": True},
            {"id": "gpt-5-nano", "provider": "openai", "name": "GPT-5 Nano", "description": "Ultra fast & lightweight", "premium": False, "new": True},
            
            # === OPENAI - GPT-4.1 Series (Standard) ===
            # === OPENAI - Legacy (Standard) ===
            {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o", "description": "Legacy multimodal", "premium": False},
            {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini", "description": "Legacy economic", "premium": False},
            {"id": "gpt-4-turbo", "provider": "openai", "name": "GPT-4 Turbo", "description": "128K context", "premium": False},
            
            # === DEEPSEEK ===
            {"id": "deepseek-chat", "provider": "deepseek", "name": "Deepseek Chat", "description": "General chat", "recommended": True, "premium": False},
            {"id": "deepseek-coder", "provider": "deepseek", "name": "Deepseek Coder", "description": "Code generation", "premium": False},
            {"id": "deepseek-reasoner", "provider": "deepseek", "name": "Deepseek Reasoner", "description": "Advanced reasoning", "premium": True},
        ]
    }
