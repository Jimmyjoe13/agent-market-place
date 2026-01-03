"""
Agent Repository
==================

Repository pour la gestion des agents IA dans Supabase.

Ce module fournit les opérations CRUD pour les agents :
- Création et configuration d'agents
- Liaison avec api_keys
- Mise à jour des paramètres LLM et RAG
"""

from datetime import datetime
from typing import Any

from src.models.agent import AgentCreate, AgentInfo, AgentUpdate, AgentWithStats
from src.repositories.base import BaseRepository


class AgentRepository(BaseRepository[AgentInfo]):
    """
    Repository pour les opérations sur les agents.

    Gère la configuration des agents IA avec leurs paramètres LLM.
    """

    def __init__(self) -> None:
        """Initialise le repository agents."""
        super().__init__("agents")

    def get_by_id(self, id: str) -> AgentInfo | None:
        """
        Récupère un agent par son ID.

        Args:
            id: UUID de l'agent.

        Returns:
            AgentInfo ou None si non trouvé.
        """
        try:
            response = self.table.select("*").eq("id", id).single().execute()
            if response.data:
                return AgentInfo(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching agent", id=id, error=str(e))
            return None

    def get_by_user(self, user_id: str, active_only: bool = True) -> list[AgentInfo]:
        """
        Récupère tous les agents d'un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.
            active_only: Ne retourner que les agents actifs.

        Returns:
            Liste des agents.
        """
        try:
            query = self.table.select("*").eq("user_id", user_id)

            if active_only:
                query = query.eq("is_active", True)

            query = query.order("created_at", desc=True)
            response = query.execute()

            return [AgentInfo(**a) for a in response.data]
        except Exception as e:
            self.logger.error("Error fetching user agents", user_id=user_id, error=str(e))
            return []

    def get_with_stats(self, agent_id: str) -> AgentWithStats | None:
        """
        Récupère un agent avec ses statistiques.

        Args:
            agent_id: UUID de l'agent.

        Returns:
            AgentWithStats ou None.
        """
        try:
            # Utiliser la vue agent_dashboard
            response = (
                self.client.from_("agent_dashboard")
                .select("*")
                .eq("id", agent_id)
                .single()
                .execute()
            )

            if response.data:
                return AgentWithStats(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching agent stats", agent_id=agent_id, error=str(e))
            return self.get_by_id(agent_id)  # Fallback sans stats

    def create(self, data: dict[str, Any]) -> AgentInfo:
        """
        Crée un nouvel agent.

        Args:
            data: Données de l'agent.

        Returns:
            AgentInfo créé.
        """
        response = self.table.insert(data).execute()
        return AgentInfo(**response.data[0])

    def create_agent(self, user_id: str, agent_data: AgentCreate) -> AgentInfo:
        """
        Crée un nouvel agent pour un utilisateur.

        Args:
            user_id: UUID de l'utilisateur propriétaire.
            agent_data: Données de création.

        Returns:
            AgentInfo créé.
        """
        data = {
            "user_id": user_id,
            "name": agent_data.name,
            "description": agent_data.description,
            "model_id": agent_data.model_id,
            "system_prompt": agent_data.system_prompt,
            "temperature": agent_data.temperature,
            "rag_enabled": agent_data.rag_enabled,
            "max_monthly_tokens": agent_data.max_monthly_tokens,
            "max_daily_requests": agent_data.max_daily_requests,
        }

        agent = self.create(data)

        self.logger.info(
            "Agent created",
            agent_id=str(agent.id),
            user_id=user_id,
            name=agent_data.name,
        )

        return agent

    def create_agent_with_key(
        self, 
        user_id: str, 
        agent_data: AgentCreate, 
        api_key_id: str
    ) -> AgentInfo:
        """
        Crée un nouvel agent lié à une clé API.

        Architecture v3: 1 Clé = 1 Agent = 1 RAG.
        L'agent est créé avec api_key_id pré-rempli.

        Args:
            user_id: UUID de l'utilisateur propriétaire.
            agent_data: Données de création de l'agent.
            api_key_id: UUID de la clé API propriétaire.

        Returns:
            AgentInfo créé.
        """
        data = {
            "user_id": user_id,
            "api_key_id": api_key_id,
            "name": agent_data.name,
            "description": agent_data.description,
            "model_id": agent_data.model_id,
            "system_prompt": agent_data.system_prompt,
            "temperature": agent_data.temperature,
            "rag_enabled": agent_data.rag_enabled,
            "max_monthly_tokens": agent_data.max_monthly_tokens,
            "max_daily_requests": agent_data.max_daily_requests,
        }

        agent = self.create(data)

        self.logger.info(
            "Agent created with key",
            agent_id=str(agent.id),
            api_key_id=api_key_id,
            user_id=user_id,
            name=agent_data.name,
        )

        return agent

    def update(self, agent_id: str, updates: AgentUpdate) -> AgentInfo | None:
        """
        Met à jour un agent.

        Args:
            agent_id: UUID de l'agent.
            updates: Données à mettre à jour.

        Returns:
            AgentInfo mis à jour ou None si erreur.
        """
        try:
            # Filtrer les valeurs None
            update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

            if not update_data:
                return self.get_by_id(agent_id)

            response = self.table.update(update_data).eq("id", agent_id).execute()

            if response.data:
                self.logger.info("Agent updated", agent_id=agent_id)
                return AgentInfo(**response.data[0])
            return None
        except Exception as e:
            self.logger.error("Error updating agent", agent_id=agent_id, error=str(e))
            return None

    def delete(self, id: str) -> bool:
        """
        Supprime un agent (et ses clés API par cascade).

        Args:
            id: UUID de l'agent.

        Returns:
            True si supprimé.
        """
        try:
            self.table.delete().eq("id", id).execute()
            self.logger.info("Agent deleted", agent_id=id)
            return True
        except Exception as e:
            self.logger.error("Error deleting agent", agent_id=id, error=str(e))
            return False

    def deactivate(self, agent_id: str) -> bool:
        """
        Désactive un agent (soft delete).

        Args:
            agent_id: UUID de l'agent.

        Returns:
            True si désactivé.
        """
        try:
            self.table.update({"is_active": False}).eq("id", agent_id).execute()
            self.logger.info("Agent deactivated", agent_id=agent_id)
            return True
        except Exception as e:
            self.logger.error("Error deactivating agent", error=str(e))
            return False

    def count_user_agents(self, user_id: str) -> int:
        """
        Compte les agents actifs d'un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            Nombre d'agents.
        """
        try:
            response = (
                self.table.select("id", count="exact")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            return response.count or 0
        except Exception as e:
            self.logger.error("Error counting agents", error=str(e))
            return 0

    def increment_usage(
        self,
        agent_id: str,
        tokens: int = 0,
        requests: int = 1,
    ) -> None:
        """
        Incrémente les compteurs d'usage d'un agent.

        Args:
            agent_id: UUID de l'agent.
            tokens: Nombre de tokens à ajouter.
            requests: Nombre de requêtes à ajouter.
        """
        try:
            current_month = datetime.utcnow().strftime("%Y-%m")
            today = datetime.utcnow().date().isoformat()

            # Récupérer l'agent pour vérifier le reset
            agent = self.get_by_id(agent_id)
            if not agent:
                return

            update_data = {}

            # Reset mensuel si nouveau mois
            if agent.usage_reset_month != current_month:
                update_data["tokens_used_this_month"] = tokens
                update_data["usage_reset_month"] = current_month
            else:
                # Incrémenter via RPC ou calcul
                update_data["tokens_used_this_month"] = agent.tokens_used_this_month + tokens

            # Reset quotidien si nouveau jour
            if str(agent.daily_reset_date) != today:
                update_data["requests_today"] = requests
                update_data["daily_reset_date"] = today
            else:
                update_data["requests_today"] = agent.requests_today + requests

            self.table.update(update_data).eq("id", agent_id).execute()

        except Exception as e:
            self.logger.error("Error incrementing agent usage", error=str(e))

    def check_limits(self, agent_id: str) -> dict[str, Any]:
        """
        Vérifie si l'agent a atteint ses limites.

        Args:
            agent_id: UUID de l'agent.

        Returns:
            Dict avec allowed, reason, usage, limits.
        """
        agent = self.get_by_id(agent_id)
        if not agent or not agent.is_active:
            return {"allowed": False, "reason": "agent_inactive"}

        # Vérifier limite quotidienne
        if agent.max_daily_requests > 0 and agent.requests_today >= agent.max_daily_requests:
            return {
                "allowed": False,
                "reason": "daily_limit_reached",
                "usage": agent.requests_today,
                "limit": agent.max_daily_requests,
            }

        # Vérifier limite mensuelle tokens
        if (
            agent.max_monthly_tokens > 0
            and agent.tokens_used_this_month >= agent.max_monthly_tokens
        ):
            return {
                "allowed": False,
                "reason": "monthly_token_limit_reached",
                "usage": agent.tokens_used_this_month,
                "limit": agent.max_monthly_tokens,
            }

        return {"allowed": True}

    def get_or_create_default_agent(self, user_id: str) -> AgentInfo:
        """
        Récupère ou crée l'agent par défaut d'un utilisateur.

        Utilisé lors de la création d'une clé API sans agent_id spécifié.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            AgentInfo (existant ou nouveau).
        """
        # Chercher un agent existant
        agents = self.get_by_user(user_id, active_only=True)
        if agents:
            return agents[0]

        # Créer un agent par défaut
        return self.create_agent(
            user_id=user_id,
            agent_data=AgentCreate(name="Default Agent"),
        )
