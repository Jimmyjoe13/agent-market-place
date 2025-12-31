"""
Agent Config Routes (Legacy)
=============================

Routes de configuration agent pour le playground.
Compatibilité avec l'ancienne API `/agent/config`.

Ces routes permettent de :
- Récupérer/modifier la config du premier agent de l'utilisateur
- Lister les modèles LLM disponibles
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_agent_repo
from src.config.logging_config import get_logger
from src.models.user import UserWithSubscription
from src.models.agent import AgentUpdate
from src.repositories.agent_repository import AgentRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent Config"])


# ===== Models =====

class AgentConfigResponse(BaseModel):
    """Réponse config agent pour le playground."""
    agent_id: str
    config: dict


class ModelInfo(BaseModel):
    """Info d'un modèle LLM disponible."""
    id: str
    provider: str
    name: str
    description: str | None = None
    recommended: bool = False
    premium: bool = False
    new: bool = False
    coming_soon: bool = False  # True si pas encore intégré


class AvailableModelsResponse(BaseModel):
    """Liste des modèles disponibles."""
    models: list[ModelInfo]


# ===== Available Models (December 2025) =====
# Providers disponibles: Mistral, OpenAI, DeepSeek
# Coming soon: Google, Anthropic

AVAILABLE_MODELS = [
    # ===== Mistral (DISPONIBLE) =====
    ModelInfo(
        id="mistral-large-latest",
        provider="Mistral",
        name="Mistral Large",
        description="Le modèle le plus puissant de Mistral",
        recommended=True,
    ),
    ModelInfo(
        id="mistral-small-latest",
        provider="Mistral",
        name="Mistral Small",
        description="Rapide et économique",
    ),
    ModelInfo(
        id="codestral-latest",
        provider="Mistral",
        name="Codestral",
        description="Optimisé pour le code",
        new=True,
    ),
    ModelInfo(
        id="pixtral-large-latest",
        provider="Mistral",
        name="Pixtral Large",
        description="Multimodal vision + texte",
        new=True,
    ),
    
    # ===== OpenAI (DISPONIBLE) =====
    # GPT-4o series (actuellement supportés)
    ModelInfo(
        id="gpt-4o",
        provider="OpenAI",
        name="GPT-4o",
        description="Modèle multimodal rapide",
        recommended=True,
    ),
    ModelInfo(
        id="gpt-4o-mini",
        provider="OpenAI",
        name="GPT-4o Mini",
        description="Version compacte de GPT-4o",
    ),
    ModelInfo(
        id="gpt-4-turbo",
        provider="OpenAI",
        name="GPT-4 Turbo",
        description="Rapide avec contexte étendu",
        premium=True,
    ),
    ModelInfo(
        id="gpt-3.5-turbo",
        provider="OpenAI",
        name="GPT-3.5 Turbo",
        description="Économique et rapide",
    ),
    # o-series reasoning (si disponible dans votre clé API)
    ModelInfo(
        id="o1-preview",
        provider="OpenAI",
        name="o1 Preview",
        description="Reasoning avancé",
        premium=True,
        new=True,
    ),
    ModelInfo(
        id="o1-mini",
        provider="OpenAI",
        name="o1 Mini",
        description="Reasoning rapide et économique",
        new=True,
    ),
    
    # ===== DeepSeek (DISPONIBLE) =====
    ModelInfo(
        id="deepseek-chat",
        provider="DeepSeek",
        name="DeepSeek Chat",
        description="Modèle chinois performant",
    ),
    ModelInfo(
        id="deepseek-coder",
        provider="DeepSeek",
        name="DeepSeek Coder",
        description="Spécialisé génération de code",
        new=True,
    ),
    
    # ===== Google Gemini (COMING SOON) =====
    ModelInfo(
        id="gemini-2.0-flash",
        provider="Google",
        name="Gemini 2.0 Flash",
        description="2x plus rapide que 1.5 Pro",
        coming_soon=True,
    ),
    ModelInfo(
        id="gemini-1.5-pro",
        provider="Google",
        name="Gemini 1.5 Pro",
        description="Modèle avancé de Google",
        premium=True,
        coming_soon=True,
    ),
    ModelInfo(
        id="gemini-1.5-flash",
        provider="Google",
        name="Gemini 1.5 Flash",
        description="Rapide et optimisé",
        coming_soon=True,
    ),
    
    # ===== Anthropic Claude (COMING SOON) =====
    ModelInfo(
        id="claude-3.5-sonnet",
        provider="Anthropic",
        name="Claude 3.5 Sonnet",
        description="Modèle équilibré d'Anthropic",
        premium=True,
        coming_soon=True,
    ),
    ModelInfo(
        id="claude-3.5-haiku",
        provider="Anthropic",
        name="Claude 3.5 Haiku",
        description="Rapide et économique",
        coming_soon=True,
    ),
]


# ===== Routes =====

@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models(
    user: UserWithSubscription = Depends(get_current_user),
):
    """
    Liste les modèles LLM disponibles.
    
    Note: Les modèles premium nécessitent un plan Pro.
    """
    return AvailableModelsResponse(models=AVAILABLE_MODELS)


@router.get("/config", response_model=AgentConfigResponse)
async def get_agent_config(
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Récupère la configuration de l'agent par défaut de l'utilisateur.
    
    Si l'utilisateur n'a pas d'agent, en crée un automatiquement.
    """
    # Récupérer le premier agent actif de l'utilisateur
    agents = repo.get_by_user(str(user.id), active_only=True)
    
    if agents:
        agent = agents[0]
    else:
        # Créer un agent par défaut
        from src.models.agent import AgentCreate
        
        new_agent = AgentCreate(
            name="Mon premier agent",
            description="Agent créé automatiquement",
            model_id="mistral-large-latest",
            rag_enabled=True,
        )
        agent = repo.create_agent(str(user.id), new_agent)
        logger.info("Default agent created", user_id=str(user.id), agent_id=str(agent.id))
    
    return AgentConfigResponse(
        agent_id=str(agent.id),
        config={
            "model_id": agent.model_id,
            "system_prompt": agent.system_prompt,
            "rag_enabled": agent.rag_enabled,
            "agent_name": agent.name,
        }
    )


@router.patch("/config", response_model=AgentConfigResponse)
async def update_agent_config(
    updates: AgentUpdate,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Met à jour la configuration de l'agent par défaut.
    """
    # Récupérer le premier agent actif
    agents = repo.get_by_user(str(user.id), active_only=True)
    
    if not agents:
        raise HTTPException(
            status_code=404,
            detail="Aucun agent trouvé. Créez d'abord un agent."
        )
    
    agent = agents[0]
    
    # Mettre à jour
    updated = repo.update(str(agent.id), updates)
    
    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la mise à jour"
        )
    
    logger.info("Agent config updated", agent_id=str(agent.id), user_id=str(user.id))
    
    return AgentConfigResponse(
        agent_id=str(updated.id),
        config={
            "model_id": updated.model_id,
            "system_prompt": updated.system_prompt,
            "rag_enabled": updated.rag_enabled,
            "agent_name": updated.name,
        }
    )
