"""
API Key Repository
===================

Repository pour la gestion des clés API dans Supabase.

Ce module fournit les opérations CRUD pour les clés API :
- Création avec génération sécurisée
- Validation avec mise à jour d'usage
- Révocation et listing

Example:
    >>> from src.repositories.api_key_repository import ApiKeyRepository
    >>> repo = ApiKeyRepository()
    >>> key_data = repo.create("My App", ["query", "feedback"])
    >>> print(f"Clé créée: {key_data['key']}")  # Sauvegarder immédiatement!
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.models.api_key import ApiKeyInfo, ApiKeyValidation, ApiKeyUsageStats, AgentConfig
from src.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKeyInfo]):
    """
    Repository pour les opérations sur les clés API.
    
    Gère la création, validation et révocation des clés.
    Les clés sont stockées sous forme de hash SHA-256.
    Supporté multi-tenant via user_id.
    
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
        Récupère une clé API par son ID.
        
        Args:
            id: UUID de la clé.
            
        Returns:
            ApiKeyInfo ou None si non trouvée.
        """
        try:
            response = (
                self.table
                .select("*")
                .eq("id", id)
                .single()
                .execute()
            )
            if response.data:
                return ApiKeyInfo(**self._format_key_data(response.data))
            return None
        except Exception as e:
            self.logger.error("Error fetching API key", id=id, error=str(e))
            return None
    
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Crée une nouvelle clé API.
        
        Args:
            data: Dictionnaire avec name, scopes, rate_limit, etc.
            
        Returns:
            Dictionnaire avec la clé complète (⚠️ affichée une seule fois).
            
        Example:
            >>> repo = ApiKeyRepository()
            >>> result = repo.create({
            ...     "name": "Production",
            ...     "scopes": ["query"],
            ...     "rate_limit_per_minute": 100
            ... })
            >>> print(result["key"])  # rag_a1b2c3d4...
        """
        # Générer la clé aléatoire
        random_part = secrets.token_hex(self.KEY_LENGTH // 2)
        full_key = f"{self.KEY_PREFIX}{random_part}"
        
        # Calculer le hash et le préfixe
        key_hash = self._hash_key(full_key)
        key_prefix = full_key[:12]  # rag_ + 8 chars
        
        # Calculer la date d'expiration
        expires_at = None
        if data.get("expires_in_days"):
            expires_at = datetime.utcnow() + timedelta(days=data["expires_in_days"])
        
        # Préparer les données pour insertion
        insert_data = {
            "name": data["name"],
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "scopes": data.get("scopes", ["query"]),
            "rate_limit_per_minute": data.get("rate_limit_per_minute", 100),
            "monthly_quota": data.get("monthly_quota", 0),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "metadata": data.get("metadata", {}),
        }
        
        # Ajouter user_id si fourni (multi-tenant)
        if data.get("user_id"):
            insert_data["user_id"] = data["user_id"]
        
        # Ajouter agent_config si fourni
        agent_config = data.get("agent_config", {})
        if isinstance(agent_config, dict):
            insert_data["model_id"] = agent_config.get("model_id", "mistral-large-latest")
            insert_data["system_prompt"] = agent_config.get("system_prompt")
            insert_data["rag_enabled"] = agent_config.get("rag_enabled", True)
            insert_data["agent_name"] = agent_config.get("agent_name")
        
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
        
        La clé reste dans la base mais devient inutilisable.
        
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
        Valide une clé API.
        
        Vérifie que la clé existe, est active, non expirée,
        et n'a pas dépassé son quota.
        
        Args:
            key: Clé API complète (ex: rag_xxxx...).
            client_ip: Adresse IP du client pour logging.
            
        Returns:
            ApiKeyValidation avec les permissions ou None si invalide.
            
        Example:
            >>> validation = repo.validate("rag_a1b2c3d4...")
            >>> if validation and validation.is_valid:
            ...     print(f"Scopes: {validation.scopes}")
        """
        key_hash = self._hash_key(key)
        
        try:
            response = self.client.rpc(
                "validate_api_key",
                {
                    "p_key_hash": key_hash,
                    "p_client_ip": client_ip,
                }
            ).execute()
            
            if response.data:
                data = response.data[0]
                
                # Construire AgentConfig si la clé est valide
                agent_config = None
                if data["is_valid"]:
                    agent_config = AgentConfig(
                        model_id=data.get("model_id") or "mistral-large-latest",
                        system_prompt=data.get("system_prompt"),
                        rag_enabled=data.get("rag_enabled", True),
                        agent_name=data.get("agent_name"),
                    )
                
                return ApiKeyValidation(
                    id=data["id"] if data["id"] else None,
                    user_id=data.get("user_id"),
                    scopes=data["scopes"] or [],
                    rate_limit=data["rate_limit_per_minute"] or 100,
                    is_valid=data["is_valid"],
                    rejection_reason=data["rejection_reason"],
                    agent_config=agent_config,
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
        
        Args:
            user_id: Filtrer par utilisateur (multi-tenant).
            page: Numéro de page (1-indexed).
            per_page: Nombre de résultats par page.
            include_inactive: Inclure les clés révoquées.
            
        Returns:
            Tuple (liste des clés, total).
        """
        query = self.table.select("*", count="exact")
        
        # Filtre multi-tenant
        if user_id:
            query = query.eq("user_id", user_id)
        
        if not include_inactive:
            query = query.eq("is_active", True)
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)
        query = query.order("created_at", desc=True)
        
        response = query.execute()
        
        keys = [
            ApiKeyInfo(**self._format_key_data(k))
            for k in response.data
        ]
        total = response.count or len(keys)
        
        return keys, total
    
    def get_usage_stats(
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
            ApiKeyUsageStats avec les métriques.
        """
        try:
            response = self.client.rpc(
                "get_api_key_stats",
                {"p_key_id": key_id, "p_days": days}
            ).execute()
            
            if response.data:
                data = response.data[0]
                return ApiKeyUsageStats(
                    total_requests=data["total_requests"] or 0,
                    avg_response_time=data["avg_response_time"],
                    error_rate=data["error_rate"] or 0,
                    requests_by_endpoint=data["requests_by_endpoint"] or {},
                    requests_by_day=data["requests_by_day"] or {},
                )
            return None
            
        except Exception as e:
            self.logger.error("Error getting API key stats", error=str(e))
            return None
    
    def log_usage(
        self,
        key_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Enregistre une utilisation de clé API.
        
        Args:
            key_id: UUID de la clé.
            endpoint: Endpoint appelé.
            method: Méthode HTTP.
            status_code: Code de réponse.
            response_time_ms: Temps de réponse.
            client_ip: IP du client.
            user_agent: User-Agent du client.
            
        Returns:
            True si le log a été créé.
        """
        try:
            self.client.table("api_key_usage_logs").insert({
                "api_key_id": key_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "client_ip": client_ip,
                "user_agent": user_agent[:500] if user_agent else None,
            }).execute()
            return True
        except Exception as e:
            self.logger.error("Error logging API usage", error=str(e))
            return False
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Calcule le hash SHA-256 d'une clé."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def _format_key_data(data: dict) -> dict:
        """Formate les données de la base pour le modèle."""
        return {
            "id": data["id"],
            "name": data["name"],
            "prefix": data["key_prefix"],
            "scopes": data["scopes"] or [],
            "rate_limit_per_minute": data["rate_limit_per_minute"],
            "monthly_quota": data.get("monthly_quota", 0),
            "monthly_usage": data.get("monthly_usage", 0),
            "is_active": data["is_active"],
            "expires_at": data.get("expires_at"),
            "last_used_at": data.get("last_used_at"),
            "created_at": data["created_at"],
            # Agent config fields
            "agent_model_id": data.get("model_id", "mistral-large-latest"),
            "agent_name": data.get("agent_name"),
            "rag_enabled": data.get("rag_enabled", True),
        }
