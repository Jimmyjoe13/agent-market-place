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


# Repository singleton
_agent_repo: ApiKeyRepository | None = None


def get_agent_repo() -> ApiKeyRepository:
    """Retourne le repository API keys."""
    global _agent_repo
    if _agent_repo is None:
        _agent_repo = ApiKeyRepository()
    return _agent_repo


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
            # Mistral
            {"id": "mistral-large-latest", "provider": "mistral", "name": "Mistral Large", "recommended": True},
            {"id": "mistral-medium-latest", "provider": "mistral", "name": "Mistral Medium"},
            {"id": "mistral-small-latest", "provider": "mistral", "name": "Mistral Small"},
            # OpenAI
            {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "provider": "openai", "name": "GPT-4 Turbo"},
            # Deepseek
            {"id": "deepseek-chat", "provider": "deepseek", "name": "Deepseek Chat", "recommended": True},
            {"id": "deepseek-coder", "provider": "deepseek", "name": "Deepseek Coder"},
            {"id": "deepseek-reasoner", "provider": "deepseek", "name": "Deepseek Reasoner"},
        ]
    }
