"""
User Repository
================

Repository pour la gestion des utilisateurs dans Supabase.

Ce module fournit les opérations CRUD pour les utilisateurs :
- Création via OAuth (Google, GitHub)
- Récupération par email ou provider_id
- Mise à jour du profil et dernière connexion

Example:
    >>> from src.repositories.user_repository import UserRepository
    >>> repo = UserRepository()
    >>> user = repo.get_or_create_oauth_user("user@example.com", "Google User", "google", "123456")
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.models.user import UserCreate, UserInfo, UserWithSubscription, OAuthProvider
from src.repositories.base import BaseRepository
from src.utils.encryption import encrypt_value, decrypt_value


class UserRepository(BaseRepository[UserInfo]):
    """
    Repository pour les opérations sur les utilisateurs.
    
    Gère la création OAuth, mise à jour et récupération des utilisateurs.
    """
    
    def __init__(self) -> None:
        """Initialise le repository users."""
        super().__init__("users")
    
    def get_by_id(self, id: str) -> UserInfo | None:
        """
        Récupère un utilisateur par son ID.
        
        Args:
            id: UUID de l'utilisateur.
            
        Returns:
            UserInfo ou None si non trouvé.
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
                return UserInfo(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching user", id=id, error=str(e))
            return None

    def _map_to_user_info(self, data: dict[str, Any]) -> UserInfo:
        """Ajoute le résumé des clés BYOK au UserInfo."""
        keys = data.get("provider_keys", {}) or {}
        summary = {k: bool(v) for k, v in keys.items()}
        # On ne passe pas provider_keys au constructeur car il n'est pas dans le modèle UserInfo
        data_copy = data.copy()
        if "provider_keys" in data_copy:
            del data_copy["provider_keys"]
        return UserInfo(**data_copy, provider_keys_summary=summary)
    
    def get_by_email(self, email: str) -> UserInfo | None:
        """
        Récupère un utilisateur par email.
        
        Args:
            email: Email de l'utilisateur.
            
        Returns:
            UserInfo ou None si non trouvé.
        """
        try:
            response = (
                self.table
                .select("*")
                .eq("email", email.lower())
                .single()
                .execute()
            )
            if response.data:
                return UserInfo(**response.data)
            return None
        except Exception as e:
            self.logger.debug("User not found by email", email=email)
            return None
    
    def get_by_provider(self, provider: str, provider_id: str) -> UserInfo | None:
        """
        Récupère un utilisateur par provider OAuth.
        
        Args:
            provider: Provider OAuth (google, github).
            provider_id: ID unique du provider.
            
        Returns:
            UserInfo ou None si non trouvé.
        """
        try:
            response = (
                self.table
                .select("*")
                .eq("provider", provider)
                .eq("provider_id", provider_id)
                .single()
                .execute()
            )
            if response.data:
                return UserInfo(**response.data)
            return None
        except Exception as e:
            self.logger.debug("User not found by provider", provider=provider)
            return None
    
    def create(self, data: dict[str, Any]) -> UserInfo:
        """
        Crée un nouvel utilisateur.
        
        Args:
            data: Données de l'utilisateur.
            
        Returns:
            UserInfo créé.
        """
        # Normaliser l'email
        if "email" in data:
            data["email"] = data["email"].lower()
        
        response = self.table.insert(data).execute()
        user = UserInfo(**response.data[0])
        
        self.logger.info(
            "User created",
            user_id=str(user.id),
            email=user.email,
            provider=user.provider,
        )
        
        return user
    
    def delete(self, id: str) -> bool:
        """
        Supprime un utilisateur.
        
        Args:
            id: UUID de l'utilisateur.
            
        Returns:
            True si supprimé avec succès.
        """
        try:
            self.table.delete().eq("id", id).execute()
            self.logger.info("User deleted", id=id)
            return True
        except Exception as e:
            self.logger.error("Error deleting user", error=str(e))
            return False
    
    def get_or_create_oauth_user(
        self,
        email: str,
        name: str | None,
        provider: str,
        provider_id: str,
        avatar_url: str | None = None,
    ) -> UserInfo:
        """
        Récupère ou crée un utilisateur OAuth.
        
        Utilisé lors du callback OAuth pour :
        1. Vérifier si l'utilisateur existe (par provider_id ou email)
        2. Le créer si non existant
        3. Mettre à jour last_login_at
        
        Args:
            email: Email de l'utilisateur.
            name: Nom d'affichage.
            provider: Provider OAuth (google, github).
            provider_id: ID unique du provider.
            avatar_url: URL de l'avatar.
            
        Returns:
            UserInfo existant ou nouvellement créé.
        """
        # 1. Chercher par provider_id
        user = self.get_by_provider(provider, provider_id)
        
        if user:
            # Mettre à jour last_login_at
            self.update_last_login(str(user.id))
            return user
        
        # 2. Chercher par email (cas du merge de comptes)
        user = self.get_by_email(email)
        
        if user:
            # Mettre à jour le provider_id si différent
            if user.provider != provider:
                self.logger.warning(
                    "User exists with different provider",
                    existing_provider=user.provider,
                    new_provider=provider,
                )
            self.update_last_login(str(user.id))
            return user
        
        # 3. Créer un nouvel utilisateur
        user_data = {
            "email": email.lower(),
            "name": name,
            "avatar_url": avatar_url,
            "provider": provider,
            "provider_id": provider_id,
            "email_verified": True,  # Vérifié par OAuth provider
            "last_login_at": datetime.utcnow().isoformat(),
        }
        
        user = self.create(user_data)
        
        # Créer la subscription Free par défaut
        self._create_default_subscription(str(user.id))
        
        return user
    
    def _create_default_subscription(self, user_id: str) -> None:
        """Crée un abonnement Free pour un nouvel utilisateur."""
        try:
            # Récupérer le plan Free
            plan_response = (
                self.client.table("plans")
                .select("id")
                .eq("slug", "free")
                .single()
                .execute()
            )
            
            if plan_response.data:
                self.client.table("subscriptions").insert({
                    "user_id": user_id,
                    "plan_id": plan_response.data["id"],
                    "status": "active",
                    "billing_period": "monthly",
                }).execute()
                
                self.logger.info("Default subscription created", user_id=user_id)
        except Exception as e:
            self.logger.error("Error creating default subscription", error=str(e))
    
    def update_last_login(self, user_id: str) -> None:
        """Met à jour la date de dernière connexion."""
        try:
            self.table.update({
                "last_login_at": datetime.utcnow().isoformat(),
            }).eq("id", user_id).execute()
        except Exception as e:
            self.logger.error("Error updating last login", error=str(e))
    
    def update_profile(
        self,
        user_id: str,
        name: str | None = None,
        avatar_url: str | None = None,
        provider_keys: dict[str, str] | None = None,
    ) -> UserInfo | None:
        """
        Met à jour le profil utilisateur.
        
        Args:
            user_id: UUID de l'utilisateur.
            name: Nouveau nom (si fourni).
            avatar_url: Nouvelle URL avatar (si fourni).
            
        Returns:
            UserInfo mis à jour ou None si erreur.
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url
        if provider_keys is not None:
            # Récupérer les clés actuelles pour fusionner
            current_user_data = self.table.select("provider_keys").eq("id", user_id).single().execute().data
            current_keys = (current_user_data.get("provider_keys") or {}) if current_user_data else {}
            
            # Chiffrer et mettre à jour
            for provider, key in provider_keys.items():
                if key:
                    current_keys[provider] = encrypt_value(key)
                elif provider in current_keys:
                    del current_keys[provider]
            
            update_data["provider_keys"] = current_keys
        
        if not update_data:
            return self.get_by_id(user_id)
        
        try:
            response = (
                self.table
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )
            if response.data:
                return self._map_to_user_info(response.data[0])
            return None
        except Exception as e:
            self.logger.error("Error updating profile", error=str(e))
            return None
    
    def get_user_with_subscription(self, user_id: str) -> UserWithSubscription | None:
        """
        Récupère un utilisateur avec ses informations d'abonnement.
        
        Args:
            user_id: UUID de l'utilisateur.
            
        Returns:
            UserWithSubscription ou None si non trouvé.
        """
        try:
            # Récupérer l'utilisateur avec son abonnement et usage
            response = self.client.rpc("get_user_usage", {
                "p_user_id": user_id,
            }).execute()
            
            user = self.get_by_id(user_id)
            if not user:
                return None
            
            usage_data = response.data[0] if response.data else {}
            
            # Récupérer les infos subscription
            sub_response = (
                self.client.table("subscriptions")
                .select("*, plans(*)")
                .eq("user_id", user_id)
                .eq("status", "active")
                .single()
                .execute()
            )
            
            sub_data = sub_response.data if sub_response.data else {}
            plan_data = sub_data.get("plans", {}) if sub_data else {}
            
            return UserWithSubscription(
                **user.model_dump(),
                plan_slug=plan_data.get("slug", "free"),
                plan_name=plan_data.get("name", "Free"),
                subscription_status=sub_data.get("status", "active"),
                billing_period=sub_data.get("billing_period", "monthly"),
                current_period_end=sub_data.get("current_period_end"),
                requests_used=usage_data.get("requests_count", 0),
                requests_limit=usage_data.get("requests_limit", 100),
                documents_used=usage_data.get("documents_count", 0),
                documents_limit=usage_data.get("documents_limit", 10),
                api_keys_used=usage_data.get("api_keys_count", 0),
                api_keys_limit=usage_data.get("api_keys_limit", 1),
            )
        except Exception as e:
            self.logger.error("Error getting user with subscription", error=str(e))
            return None
