"""
Agent Routes
=============

Endpoints FastAPI pour la gestion des agents IA.

Ce module fournit :
- CRUD des agents (configuration LLM, RAG, limites)
- Listing des agents d'un utilisateur
- Statistiques d'utilisation par agent
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import get_agent_repo, get_api_key_repo, get_current_user
from src.config.logging_config import get_logger
from src.models.agent import (
    AgentCreate,
    AgentInfo,
    AgentListResponse,
    AgentUpdate,
    AgentWithStats,
)
from src.models.user import UserWithSubscription
from src.repositories.agent_repository import AgentRepository
from src.repositories.api_key_repository import ApiKeyRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agents"])


# ===== CRUD Agents =====


@router.get("", response_model=AgentListResponse)
async def list_agents(
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Liste tous les agents de l'utilisateur connecté.

    Returns:
        Liste des agents avec leur configuration.
    """
    agents = repo.get_by_user(str(user.id), active_only=True)

    return AgentListResponse(
        agents=agents,
        total=len(agents),
    )


@router.post("", response_model=AgentInfo, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Crée un nouvel agent.

    Vérifie que l'utilisateur n'a pas atteint sa limite d'agents.

    Args:
        agent_data: Configuration de l'agent.

    Returns:
        Agent créé.
    """
    # Vérifier la limite d'agents
    current_count = repo.count_user_agents(str(user.id))
    if user.agents_limit > 0 and current_count >= user.agents_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "agents_limit_reached",
                "message": f"Limite de {user.agents_limit} agents atteinte. Passez au plan supérieur.",
                "current": current_count,
                "limit": user.agents_limit,
            },
        )

    agent = repo.create_agent(str(user.id), agent_data)

    logger.info(
        "Agent created",
        agent_id=str(agent.id),
        user_id=str(user.id),
        name=agent_data.name,
    )

    return agent


@router.get("/{agent_id}", response_model=AgentWithStats)
async def get_agent(
    agent_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Récupère un agent par son ID avec ses statistiques.

    Args:
        agent_id: UUID de l'agent.

    Returns:
        Agent avec statistiques d'utilisation.
    """
    agent = repo.get_with_stats(str(agent_id))

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Vérifier que l'agent appartient à l'utilisateur
    if agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this agent",
        )

    return agent


@router.patch("/{agent_id}", response_model=AgentInfo)
async def update_agent(
    agent_id: UUID,
    updates: AgentUpdate,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Met à jour un agent.

    Args:
        agent_id: UUID de l'agent.
        updates: Champs à mettre à jour.

    Returns:
        Agent mis à jour.
    """
    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = repo.get_by_id(str(agent_id))

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this agent",
        )

    updated = repo.update(str(agent_id), updates)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent",
        )

    logger.info(
        "Agent updated",
        agent_id=str(agent_id),
        updated_fields=updates.model_dump(exclude_none=True),
        new_model_id=updated.model_id,
    )

    return updated


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Supprime un agent et toutes ses clés API.

    ⚠️ Cette action est irréversible.

    Args:
        agent_id: UUID de l'agent.
    """
    # Vérifier que l'agent existe et appartient à l'utilisateur
    agent = repo.get_by_id(str(agent_id))

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this agent",
        )

    # Supprimer l'agent (les clés API seront supprimées par cascade)
    success = repo.delete(str(agent_id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent",
        )

    logger.info("Agent deleted", agent_id=str(agent_id), user_id=str(user.id))


@router.post("/{agent_id}/deactivate", response_model=AgentInfo)
async def deactivate_agent(
    agent_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Désactive un agent (soft delete).

    L'agent et ses clés ne fonctionneront plus mais restent en base.

    Args:
        agent_id: UUID de l'agent.

    Returns:
        Agent désactivé.
    """
    agent = repo.get_by_id(str(agent_id))

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    repo.deactivate(str(agent_id))

    return repo.get_by_id(str(agent_id))


# ===== Agent Keys =====


@router.get("/{agent_id}/keys")
async def list_agent_keys(
    agent_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    agent_repo: AgentRepository = Depends(get_agent_repo),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repo),
):
    """
    Liste les clés API d'un agent.

    Args:
        agent_id: UUID de l'agent.

    Returns:
        Liste des clés API.
    """
    # Vérifier que l'agent appartient à l'utilisateur
    agent = agent_repo.get_by_id(str(agent_id))

    if not agent or agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    keys = api_key_repo.get_by_agent(str(agent_id))

    return {
        "keys": keys,
        "total": len(keys),
    }


# ===== Agent Memory =====


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: UUID,
    limit: int | None = None,
    user: UserWithSubscription = Depends(get_current_user),
    agent_repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Récupère la mémoire conversationnelle d'un agent.

    Retourne les derniers messages en mémoire (limite configurable par agent).

    Args:
        agent_id: UUID de l'agent.
        limit: Nombre max de messages (optionnel, utilise la limite agent sinon).

    Returns:
        Liste des messages avec statistiques.
    """
    from src.repositories.agent_memory_repository import AgentMemoryRepository

    # Vérifier propriété
    agent = agent_repo.get_by_id(str(agent_id))
    if not agent or agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    memory_repo = AgentMemoryRepository()
    messages = memory_repo.get_messages(str(agent_id), limit)
    stats = memory_repo.get_memory_stats(str(agent_id))

    return {
        "agent_id": str(agent_id),
        "agent_name": agent.name,
        "memory_limit": agent.memory_limit,
        "messages": [msg.to_dict() for msg in messages],
        "stats": stats,
    }


@router.delete("/{agent_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
async def clear_agent_memory(
    agent_id: UUID,
    user: UserWithSubscription = Depends(get_current_user),
    agent_repo: AgentRepository = Depends(get_agent_repo),
):
    """
    Efface la mémoire conversationnelle d'un agent.

    Utile pour "repartir de zéro" sans supprimer l'agent.
    L'agent conserve sa configuration mais oublie tout l'historique.

    Args:
        agent_id: UUID de l'agent.
    """
    from src.repositories.agent_memory_repository import AgentMemoryRepository

    # Vérifier propriété
    agent = agent_repo.get_by_id(str(agent_id))
    if not agent or agent.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    memory_repo = AgentMemoryRepository()
    success = memory_repo.clear_memory(str(agent_id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear agent memory",
        )

    logger.info("Agent memory cleared", agent_id=str(agent_id), user_id=str(user.id))
