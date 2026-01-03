"""
API Key Service
================

Service layer pour la gestion des clés API.
Encapsule la logique métier et coordonne repositories.

Ce service est responsable de :
- Validation des quotas utilisateur avant création
- Génération sécurisée des clés
- Application des règles métier (pas de scope admin pour self-service)

Usage:
    >>> from src.services.api_key_service import ApiKeyService
    >>> service = ApiKeyService()
    >>> raw_key, key_info = await service.create_user_key(
    ...     user_id="uuid",
    ...     name="Production",
    ...     scopes=["query", "feedback"]
    ... )
"""

from dataclasses import dataclass
from typing import Any

from src.config.logging_config import get_logger
from src.models.api_key import (
    ApiKeyInfo,
    ApiKeyScope,
    ApiKeyUsageStats,
)
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.subscription_repository import SubscriptionRepository

logger = get_logger(__name__)


@dataclass
class CreateKeyResult:
    """Résultat de création d'une clé API."""

    raw_key: str  # Clé complète, affichée UNE SEULE FOIS
    key_info: ApiKeyInfo


class QuotaExceededError(Exception):
    """Levée quand l'utilisateur a atteint sa limite de clés."""

    def __init__(self, message: str, limits: dict[str, Any]):
        self.message = message
        self.limits = limits
        super().__init__(message)


class ApiKeyService:
    """
    Service pour la gestion des clés API.

    Coordonne ApiKeyRepository et SubscriptionRepository
    pour appliquer les règles métier.

    Attributes:
        FORBIDDEN_SCOPES_SELF_SERVICE: Scopes interdits pour les utilisateurs.
    """

    # Scopes interdits pour le self-service (seul admin peut les attribuer)
    FORBIDDEN_SCOPES_SELF_SERVICE = frozenset([ApiKeyScope.ADMIN.value, "admin"])

    def __init__(
        self,
        key_repo: ApiKeyRepository | None = None,
        sub_repo: SubscriptionRepository | None = None,
    ) -> None:
        """
        Initialise le service.

        Args:
            key_repo: Repository API Keys (injection dépendance).
            sub_repo: Repository Subscriptions (injection dépendance).
        """
        self._key_repo = key_repo or ApiKeyRepository()
        self._sub_repo = sub_repo or SubscriptionRepository()

    async def create_user_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
        rate_limit_per_minute: int = 60,
        expires_in_days: int | None = None,
        # Config agent (nouvelle architecture)
        agent_name: str | None = None,
        agent_model_id: str = "mistral-large-latest",
        agent_system_prompt: str | None = None,
        agent_rag_enabled: bool = True,
    ) -> CreateKeyResult:
        """
        Crée une clé API avec son agent dédié.

        Architecture v3 (1 Clé = 1 Agent = 1 RAG):
        - Une clé API possède exactement un agent
        - L'agent est créé automatiquement avec la clé
        - Supprimer la clé supprime l'agent (CASCADE)

        Args:
            user_id: UUID de l'utilisateur propriétaire.
            name: Nom descriptif de la clé.
            scopes: Liste des permissions demandées.
            rate_limit_per_minute: Limite de requêtes par minute.
            expires_in_days: Expiration en jours (None = jamais).
            agent_name: Nom de l'agent (défaut: "Agent pour {name}").
            agent_model_id: ID du modèle LLM.
            agent_system_prompt: Prompt système personnalisé.
            agent_rag_enabled: Activer le RAG.

        Returns:
            CreateKeyResult contenant la clé brute et ses informations.

        Raises:
            QuotaExceededError: Si l'utilisateur a atteint sa limite.
        """
        # 1. Vérifier les quotas utilisateur
        limits = self._sub_repo.check_user_limits(user_id, "api_key")

        if not limits.get("allowed", False):
            reason = limits.get("reason", "quota_exceeded")
            logger.warning(
                "API key creation blocked by quota",
                user_id=user_id,
                reason=reason,
            )
            raise QuotaExceededError(
                f"Limite de clés atteinte: {reason}",
                limits=limits,
            )

        # 2. Filtrer les scopes interdits (sécurité)
        safe_scopes = [s for s in scopes if s not in self.FORBIDDEN_SCOPES_SELF_SERVICE]

        if not safe_scopes:
            safe_scopes = [ApiKeyScope.QUERY.value]
            logger.warning(
                "All requested scopes were forbidden, falling back to query",
                user_id=user_id,
                requested_scopes=scopes,
            )

        # 3. Créer la clé API d'abord (sans agent_id pour l'instant)
        create_data = {
            "user_id": user_id,
            "name": name,
            "scopes": safe_scopes,
            "rate_limit_per_minute": rate_limit_per_minute,
            "expires_in_days": expires_in_days,
        }

        result = self._key_repo.create(create_data)
        key_id = result["id"]

        # 4. Créer l'agent lié à cette clé
        from src.models.agent import AgentCreate
        from src.repositories.agent_repository import AgentRepository

        agent_repo = AgentRepository()
        
        final_agent_name = agent_name or f"Agent pour {name}"
        new_agent = AgentCreate(
            name=final_agent_name,
            description=f"Agent créé avec la clé {name}",
            model_id=agent_model_id,
            system_prompt=agent_system_prompt,
            rag_enabled=agent_rag_enabled,
        )
        
        created_agent = agent_repo.create_agent_with_key(
            user_id=user_id, 
            agent_data=new_agent, 
            api_key_id=key_id
        )

        logger.info(
            "API key and agent created",
            user_id=user_id,
            key_id=key_id,
            agent_id=str(created_agent.id),
            key_name=name,
            agent_name=final_agent_name,
        )

        # 5. Construire la réponse
        key_info = ApiKeyInfo(
            id=result["id"],
            agent_id=created_agent.id,
            name=result["name"],
            prefix=result["prefix"],
            scopes=result["scopes"],
            rate_limit_per_minute=result["rate_limit_per_minute"],
            is_active=result.get("is_active", True),
            expires_at=result.get("expires_at"),
            last_used_at=result.get("last_used_at"),
            created_at=result.get("created_at"),
            agent_name=final_agent_name,
            agent_model_id=agent_model_id,
            rag_enabled=agent_rag_enabled,
        )

        return CreateKeyResult(
            raw_key=result["key"],
            key_info=key_info,
        )

    def list_user_keys(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        include_inactive: bool = False,
    ) -> tuple[list[ApiKeyInfo], int]:
        """
        Liste les clés API d'un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.
            page: Numéro de page (1-indexed).
            per_page: Nombre de résultats par page.
            include_inactive: Inclure les clés révoquées.

        Returns:
            Tuple (liste des clés, total).
        """
        return self._key_repo.list_keys(
            user_id=user_id,
            page=page,
            per_page=per_page,
            include_inactive=include_inactive,
        )

    def revoke_user_key(
        self,
        user_id: str,
        key_id: str,
        delete_agent: bool = True,
    ) -> bool:
        """
        Révoque une clé appartenant à un utilisateur.

        Args:
            user_id: UUID de l'utilisateur propriétaire.
            key_id: UUID de la clé à révoquer.
            delete_agent: Si True, supprime aussi l'agent lié et ses documents.

        Returns:
            True si révoquée, False sinon.

        Raises:
            PermissionError: Si la clé n'appartient pas à l'utilisateur.
        """
        # Vérifier appartenance et récupérer les infos
        key = self._key_repo.get_by_id(key_id)

        if not key:
            logger.warning("Key not found for revocation", key_id=key_id)
            return False

        # Récupérer l'agent_id avant suppression
        agent_id = key.agent_id

        # Révoquer la clé
        success = self._key_repo.revoke(key_id)

        if success:
            logger.info(
                "API key revoked by user",
                user_id=user_id,
                key_id=key_id,
            )

            # Supprimer l'agent lié si demandé
            if delete_agent and agent_id:
                try:
                    from src.repositories.agent_repository import AgentRepository
                    
                    agent_repo = AgentRepository()
                    
                    # Supprimer l'agent (les documents seront gérés par ON DELETE CASCADE/SET NULL)
                    deleted = agent_repo.delete(agent_id)
                    
                    if deleted:
                        logger.info(
                            "Agent deleted with API key",
                            agent_id=agent_id,
                            key_id=key_id,
                            user_id=user_id,
                        )
                    else:
                        logger.warning(
                            "Failed to delete agent with API key",
                            agent_id=agent_id,
                            key_id=key_id,
                        )
                except Exception as e:
                    logger.error(
                        "Error deleting agent with API key",
                        agent_id=agent_id,
                        key_id=key_id,
                        error=str(e),
                    )

        return success

    def get_key_stats(
        self,
        key_id: str,
        days: int = 30,
    ) -> ApiKeyUsageStats | None:
        """
        Récupère les statistiques d'utilisation d'une clé.

        Args:
            key_id: UUID de la clé.
            days: Période en jours.

        Returns:
            ApiKeyUsageStats ou None si non trouvée.
        """
        return self._key_repo.get_usage_stats(key_id, days)

    def validate_key(
        self,
        raw_key: str,
        client_ip: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Valide une clé API.

        Args:
            raw_key: Clé API complète (sk-proj-xxx...).
            client_ip: IP du client pour logging.

        Returns:
            Dict avec les infos de validation ou None si invalide.
        """
        validation = self._key_repo.validate(raw_key, client_ip)

        if validation is None:
            return None

        result = {
            "id": str(validation.id) if validation.id else None,
            "user_id": str(validation.user_id) if validation.user_id else None,
            "scopes": validation.scopes,
            "rate_limit": validation.rate_limit,
            "is_valid": validation.is_valid,
            "rejection_reason": validation.rejection_reason,
            # Config agent (champs directs sur ApiKeyValidation)
            "model_id": validation.model_id,
            "system_prompt": validation.system_prompt,
            "rag_enabled": validation.rag_enabled,
            "agent_name": validation.agent_name,
        }

        return result


# ===== Singleton pour injection =====

_api_key_service: ApiKeyService | None = None


def get_api_key_service() -> ApiKeyService:
    """Retourne l'instance singleton du service."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = ApiKeyService()
    return _api_key_service
