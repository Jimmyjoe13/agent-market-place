"""
API Key Repository
===================

Repository pour la gestion des clés API dans Supabase.

Ce module fournit les opérations CRUD pour les clés API :
- Création avec génération sécurisée
- Validation avec mise à jour d'usage
- Révocation et listing

Architecture v2:
- Chaque clé API est liée à un agent via api_keys.agent_id
- Un agent peut avoir plusieurs clés API
- La configuration LLM est sur l'agent, pas sur la clé
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from src.models.api_key import ApiKeyInfo, ApiKeyUsageStats, ApiKeyValidation
from src.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKeyInfo]):
    """
    Repository pour les opérations sur les clés API.

    Gère la création, validation et révocation des clés.
    Les clés sont stockées sous forme de hash SHA-256.
    Chaque clé est liée à un agent via agent_id.

    Attributes:
        KEY_PREFIX: Préfixe des clés générées ("sk-proj-").
        KEY_LENGTH: Longueur de la partie aléatoire (32 caractères).
    """

    KEY_PREFIX = "sk-proj-"
    KEY_LENGTH = 32

    def __init__(self) -> None:
        """Initialise le repository api_keys."""
        super().__init__("api_keys")

    def get_by_id(self, id: str) -> ApiKeyInfo | None:
        """
        Récupère une clé API par son ID avec son agent associé.

        Args:
            id: UUID de la clé.

        Returns:
            ApiKeyInfo ou None si non trouvée.
        """
        try:
            # Récupérer la clé avec JOIN sur agents via api_keys.agent_id
            response = (
                self.table.select("*, agents(id, name, model_id, rag_enabled)")
                .eq("id", id)
                .maybe_single()
                .execute()
            )
            
            if not response.data:
                return None
            
            return ApiKeyInfo(**self._format_key_data(response.data))
        except Exception as e:
            self.logger.error("Error fetching API key", id=id, error=str(e))
            return None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Crée une nouvelle clé API liée à un agent.

        Args:
            data: Dictionnaire avec:
                - name: Nom de la clé
                - agent_id: UUID de l'agent (requis)
                - user_id: UUID de l'utilisateur (requis)
                - scopes: Liste des permissions
                - rate_limit_per_minute: Limite par minute
                - expires_in_days: Jours avant expiration

        Returns:
            Dictionnaire avec la clé complète (⚠️ affichée une seule fois).
        """
        # Validation
        if not data.get("agent_id"):
            raise ValueError("agent_id is required")
        if not data.get("user_id"):
            raise ValueError("user_id is required")

        # Générer la clé aléatoire
        random_part = secrets.token_hex(self.KEY_LENGTH // 2)
        full_key = f"{self.KEY_PREFIX}{random_part}"

        # Calculer le hash et le préfixe
        key_hash = self._hash_key(full_key)
        key_prefix = full_key[:12]

        # Calculer la date d'expiration
        expires_at = None
        if data.get("expires_in_days"):
            expires_at = datetime.utcnow() + timedelta(days=data["expires_in_days"])

        # Préparer les données pour insertion
        insert_data = {
            "name": data["name"],
            "agent_id": str(data["agent_id"]),
            "user_id": str(data["user_id"]),
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "scopes": data.get("scopes", ["query"]),
            "rate_limit_per_minute": data.get("rate_limit_per_minute", 60),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

        response = self.table.insert(insert_data).execute()
        created = response.data[0]

        self.logger.info(
            "API key created",
            id=created["id"],
            name=data["name"],
            agent_id=str(data["agent_id"]),
            prefix=key_prefix,
        )

        # Retourner avec la clé complète (une seule fois!)
        return {
            **self._format_key_data(created),
            "key": full_key,
        }

    def delete(self, id: str) -> bool:
        """
        Supprime une clé API (hard delete).

        Args:
            id: UUID de la clé.

        Returns:
            True si supprimée avec succès.
        """
        try:
            self.table.delete().eq("id", id).execute()
            self.logger.info("API key deleted", id=id)
            return True
        except Exception as e:
            self.logger.error("Error deleting API key", error=str(e))
            return False

    def revoke(self, id: str) -> bool:
        """
        Révoque une clé API (soft delete).

        Args:
            id: UUID de la clé.

        Returns:
            True si révoquée avec succès.
        """
        try:
            self.table.update({"is_active": False}).eq("id", id).execute()
            self.logger.info("API key revoked", id=id)
            return True
        except Exception as e:
            self.logger.error("Error revoking API key", error=str(e))
            return False

    def validate(
        self,
        key: str,
        client_ip: str | None = None,
    ) -> ApiKeyValidation | None:
        """
        Valide une clé API et récupère la config de l'agent associé.

        Args:
            key: Clé API complète (ex: sk-proj-xxxx...).
            client_ip: Adresse IP du client pour logging.

        Returns:
            ApiKeyValidation avec les permissions et config agent.
        """
        key_hash = self._hash_key(key)

        try:
            response = self.client.rpc(
                "validate_api_key",
                {
                    "p_key_hash": key_hash,
                    "p_client_ip": client_ip,
                },
            ).execute()

            if response.data:
                data = response.data[0]

                return ApiKeyValidation(
                    is_valid=data["is_valid"],
                    key_id=data.get("key_id"),
                    agent_id=data.get("agent_id"),
                    user_id=data.get("user_id"),
                    scopes=data.get("scopes") or [],
                    rate_limit=data.get("rate_limit_per_minute") or 60,
                    rejection_reason=data.get("rejection_reason"),
                    # Config agent
                    model_id=data.get("model_id"),
                    system_prompt=data.get("system_prompt"),
                    rag_enabled=data.get("rag_enabled"),
                    agent_name=data.get("agent_name"),
                )
            return None

        except Exception as e:
            self.logger.error("Error validating API key", error=str(e))
            return None

    def list_keys(
        self,
        user_id: str | None = None,
        agent_id: str | None = None,
        page: int = 1,
        per_page: int = 20,
        include_inactive: bool = False,
    ) -> tuple[list[ApiKeyInfo], int]:
        """
        Liste les clés API avec pagination.

        Args:
            user_id: Filtrer par utilisateur.
            agent_id: Filtrer par agent.
            page: Numéro de page (1-indexed).
            per_page: Nombre de résultats par page.
            include_inactive: Inclure les clés révoquées.

        Returns:
            Tuple (liste des clés, total).
        """
        # JOIN avec agents via api_keys.agent_id
        query = self.table.select("*, agents(id, name, model_id, rag_enabled)", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)

        if agent_id:
            query = query.eq("agent_id", agent_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        # Pagination
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)
        query = query.order("created_at", desc=True)

        response = query.execute()

        keys = [ApiKeyInfo(**self._format_key_data(k)) for k in response.data]
        total = response.count or len(keys)

        return keys, total

    def get_by_agent(self, agent_id: str) -> list[ApiKeyInfo]:
        """
        Récupère toutes les clés d'un agent.

        Args:
            agent_id: UUID de l'agent.

        Returns:
            Liste des clés API.
        """
        try:
            response = (
                self.table.select("*, agents(id, name, model_id, rag_enabled)")
                .eq("agent_id", agent_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .execute()
            )

            return [ApiKeyInfo(**self._format_key_data(k)) for k in response.data]
        except Exception as e:
            self.logger.error("Error fetching agent keys", agent_id=agent_id, error=str(e))
            return []

    def count_user_keys(self, user_id: str) -> int:
        """
        Compte les clés actives d'un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            Nombre de clés.
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
            self.logger.error("Error counting user keys", error=str(e))
            return 0

    def get_usage_stats(
        self,
        key_id: str,
        days: int = 30,
    ) -> ApiKeyUsageStats | None:
        """
        Récupère les statistiques d'utilisation d'une clé.
        """
        try:
            response = self.client.rpc(
                "get_api_key_stats", {"p_key_id": key_id, "p_days": days}
            ).execute()

            if response.data:
                data = response.data[0]
                return ApiKeyUsageStats(
                    total_requests=data.get("total_requests") or 0,
                    avg_response_time=data.get("avg_response_time"),
                    error_rate=data.get("error_rate") or 0,
                    requests_by_endpoint=data.get("requests_by_endpoint") or {},
                    requests_by_day=data.get("requests_by_day") or {},
                )
            return None

        except Exception as e:
            self.logger.error("Error getting API key stats", error=str(e))
            return None

    def update_last_used(self, key_id: str, client_ip: str | None = None) -> None:
        """
        Met à jour la date de dernière utilisation.

        Args:
            key_id: UUID de la clé.
            client_ip: Adresse IP du client.
        """
        try:
            self.table.update(
                {
                    "last_used_at": datetime.utcnow().isoformat(),
                    "last_used_ip": client_ip,
                }
            ).eq("id", key_id).execute()
        except Exception as e:
            self.logger.error("Error updating last used", error=str(e))

    @staticmethod
    def _hash_key(key: str) -> str:
        """Calcule le hash SHA-256 d'une clé."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _format_key_data(data: dict) -> dict:
        """
        Formate les données de la base pour le modèle.
        
        Architecture v2: L'agent est récupéré via JOIN sur api_keys.agent_id.
        """
        # Extraire les données de l'agent depuis le JOIN
        agent_data = data.get("agents", {}) or {}

        return {
            "id": data["id"],
            "agent_id": data.get("agent_id"),
            "name": data["name"],
            "prefix": data["key_prefix"],
            "scopes": data["scopes"] or [],
            "rate_limit_per_minute": data["rate_limit_per_minute"],
            "is_active": data["is_active"],
            "expires_at": data.get("expires_at"),
            "last_used_at": data.get("last_used_at"),
            "created_at": data.get("created_at"),
            # Données de l'agent (depuis le JOIN)
            "agent_name": agent_data.get("name"),
            "agent_model_id": agent_data.get("model_id", "mistral-large-latest"),
            "rag_enabled": agent_data.get("rag_enabled", True),
        }
