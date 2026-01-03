"""
API Key Repository
===================

Repository pour la gestion des clés API dans Supabase.

Ce module fournit les opérations CRUD pour les clés API :
- Création avec génération sécurisée
- Validation avec mise à jour d'usage
- Révocation et listing

Architecture v3:
- 1 Clé API = 1 Agent = 1 RAG
- L'agent est lié à la clé via agents.api_key_id
- Supprimer la clé supprime l'agent (CASCADE)
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
    Chaque clé est liée à un agent.

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
            # Récupérer la clé
            key_response = self.table.select("*").eq("id", id).single().execute()
            
            if not key_response.data:
                return None
            
            # Récupérer l'agent lié (via agents.api_key_id)
            agent_response = (
                self.client.from_("agents")
                .select("id, name, model_id, rag_enabled")
                .eq("api_key_id", id)
                .maybeSingle()
                .execute()
            )
            
            return ApiKeyInfo(**self._format_key_data(
                key_response.data, 
                agent_response.data if agent_response.data else None
            ))
        except Exception as e:
            self.logger.error("Error fetching API key", id=id, error=str(e))
            return None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Crée une nouvelle clé API.

        Architecture v3: La clé est créée d'abord, l'agent ensuite.

        Args:
            data: Dictionnaire avec:
                - name: Nom de la clé
                - user_id: UUID de l'utilisateur (requis)
                - scopes: Liste des permissions
                - rate_limit_per_minute: Limite par minute
                - expires_in_days: Jours avant expiration

        Returns:
            Dictionnaire avec la clé complète (⚠️ affichée une seule fois).
        """
        # Validation
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
        page: int = 1,
        per_page: int = 20,
        include_inactive: bool = False,
    ) -> tuple[list[ApiKeyInfo], int]:
        """
        Liste les clés API avec pagination.

        Architecture v3: Récupère les agents via agents.api_key_id.

        Args:
            user_id: Filtrer par utilisateur.
            page: Numéro de page (1-indexed).
            per_page: Nombre de résultats par page.
            include_inactive: Inclure les clés révoquées.

        Returns:
            Tuple (liste des clés, total).
        """
        query = self.table.select("*", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        # Pagination
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)
        query = query.order("created_at", desc=True)

        response = query.execute()

        # Récupérer les agents associés pour chaque clé
        key_ids = [k["id"] for k in response.data]
        agents_map = {}
        
        if key_ids:
            agents_response = (
                self.client.from_("agents")
                .select("api_key_id, id, name, model_id, rag_enabled")
                .in_("api_key_id", key_ids)
                .execute()
            )
            agents_map = {a["api_key_id"]: a for a in agents_response.data}

        keys = [
            ApiKeyInfo(**self._format_key_data(k, agents_map.get(k["id"])))
            for k in response.data
        ]
        total = response.count or len(keys)

        return keys, total

    # Note: get_by_agent obsolète dans architecture v3 (1 clé = 1 agent)

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
    def _format_key_data(data: dict, agent_data: dict | None = None) -> dict:
        """
        Formate les données de la base pour le modèle.
        
        Architecture v3: agent_data est passé séparément car la relation
        est maintenant agents.api_key_id -> api_keys.id.
        """
        agent = agent_data or {}

        return {
            "id": data["id"],
            "agent_id": agent.get("id"),  # ID de l'agent lié
            "name": data["name"],
            "prefix": data["key_prefix"],
            "scopes": data["scopes"] or [],
            "rate_limit_per_minute": data["rate_limit_per_minute"],
            "is_active": data["is_active"],
            "expires_at": data.get("expires_at"),
            "last_used_at": data.get("last_used_at"),
            "created_at": data.get("created_at"),
            # Données de l'agent
            "agent_name": agent.get("name"),
            "agent_model_id": agent.get("model_id", "mistral-large-latest"),
            "rag_enabled": agent.get("rag_enabled", True),
        }
