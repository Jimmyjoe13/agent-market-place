"""
Profile Repository (formerly User Repository)
===============================================

Repository pour la gestion des profils utilisateurs dans Supabase.

Ce module fournit les opérations CRUD pour les profils :
- Synchronisation avec auth.users (via trigger)
- Récupération par email ou provider_id
- Mise à jour du profil et dernière connexion

Architecture v2:
- La table `profiles` est liée à `auth.users` par FK cascade
- Les profils sont créés automatiquement par trigger lors de l'inscription
- Ce repository gère les updates et les reads
"""

from datetime import datetime
from typing import Any

from src.models.user import (
    ProfileInfo as UserInfo,
)
from src.models.user import (
    ProfileWithSubscription as UserWithSubscription,
)
from src.repositories.base import BaseRepository
from src.utils.encryption import decrypt_value, encrypt_value


class UserRepository(BaseRepository[UserInfo]):
    """
    Repository pour les opérations sur les profils utilisateurs.

    Note: Renommé "ProfileRepository" serait plus précis, mais on garde
    "UserRepository" pour la rétro-compatibilité.

    La table sous-jacente est `profiles` (pas `users`).
    """

    def __init__(self) -> None:
        """Initialise le repository profiles."""
        # Important: la table est maintenant "profiles" pas "users"
        super().__init__("profiles")

    def get_by_id(self, id: str) -> UserInfo | None:
        """
        Récupère un profil par son ID.

        Args:
            id: UUID du profil (= auth.users.id).

        Returns:
            UserInfo ou None si non trouvé.
        """
        try:
            response = self.table.select("*").eq("id", id).single().execute()
            if response.data:
                return self._map_to_user_info(response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching profile", id=id, error=str(e))
            return None

    def _map_to_user_info(self, data: dict[str, Any]) -> UserInfo:
        """Convertit les données brutes en UserInfo avec résumé BYOK."""
        # Gérer les clés BYOK chiffrées
        encrypted_keys = data.get("provider_keys_encrypted", {}) or {}
        summary = {k: bool(v) for k, v in encrypted_keys.items()}

        # Créer une copie sans les champs internes
        data_copy = data.copy()
        data_copy.pop("provider_keys_encrypted", None)

        return UserInfo(**data_copy, provider_keys_summary=summary)

    def get_by_email(self, email: str) -> UserInfo | None:
        """
        Récupère un profil par email.

        Args:
            email: Email de l'utilisateur.

        Returns:
            UserInfo ou None si non trouvé.
        """
        try:
            response = self.table.select("*").eq("email", email.lower()).single().execute()
            if response.data:
                return self._map_to_user_info(response.data)
            return None
        except Exception:
            self.logger.debug("Profile not found by email", email=email)
            return None

    def get_by_provider(self, provider: str, provider_id: str) -> UserInfo | None:
        """
        Récupère un profil par provider OAuth.

        Args:
            provider: Provider OAuth (google, github).
            provider_id: ID unique du provider.

        Returns:
            UserInfo ou None si non trouvé.
        """
        try:
            response = (
                self.table.select("*")
                .eq("provider", provider)
                .eq("provider_id", provider_id)
                .single()
                .execute()
            )
            if response.data:
                return self._map_to_user_info(response.data)
            return None
        except Exception:
            self.logger.debug("Profile not found by provider", provider=provider)
            return None

    def create(self, data: dict[str, Any]) -> UserInfo:
        """
        Crée ou met à jour un profil.

        Note: En v2, les profils sont créés automatiquement par trigger
        lors de l'inscription. Cette méthode est surtout utilisée pour
        les tests ou les cas spéciaux.

        Args:
            data: Données du profil.

        Returns:
            UserInfo créé.
        """
        if "email" in data:
            data["email"] = data["email"].lower()

        response = self.table.upsert(data).execute()
        user = self._map_to_user_info(response.data[0])

        self.logger.info(
            "Profile created/updated",
            user_id=str(user.id),
            email=user.email,
        )

        return user

    def delete(self, id: str) -> bool:
        """
        Supprime un profil.

        Note: Ceci ne supprime pas auth.users. Pour supprimer complètement
        un utilisateur, il faut utiliser l'API admin Supabase.

        Args:
            id: UUID du profil.

        Returns:
            True si supprimé avec succès.
        """
        try:
            self.table.delete().eq("id", id).execute()
            self.logger.info("Profile deleted", id=id)
            return True
        except Exception as e:
            self.logger.error("Error deleting profile", error=str(e))
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
        Récupère ou met à jour un profil OAuth.

        En v2, les profils sont créés par trigger lors de l'inscription.
        Cette méthode :
        1. Cherche un profil existant
        2. Le met à jour avec les infos OAuth
        3. Met à jour last_login_at

        Args:
            email: Email de l'utilisateur.
            name: Nom d'affichage.
            provider: Provider OAuth (google, github).
            provider_id: ID unique du provider.
            avatar_url: URL de l'avatar.

        Returns:
            UserInfo existant ou mis à jour.
        """
        # 1. Chercher par email (car le trigger a déjà créé le profil)
        user = self.get_by_email(email)

        if user:
            # Mettre à jour les infos OAuth et last_login
            update_data = {
                "provider": provider,
                "provider_id": provider_id,
                "last_login_at": datetime.utcnow().isoformat(),
                "email_verified": True,
            }
            if name:
                update_data["name"] = name
            if avatar_url:
                update_data["avatar_url"] = avatar_url

            self.table.update(update_data).eq("id", str(user.id)).execute()

            # Créer subscription Free si pas encore fait
            self._ensure_subscription(str(user.id))

            return self.get_by_id(str(user.id)) or user

        # 2. Fallback: créer le profil (cas rare, trigger devrait l'avoir fait)
        self.logger.warning("Profile not found, creating manually", email=email)

        user_data = {
            "email": email.lower(),
            "name": name,
            "avatar_url": avatar_url,
            "provider": provider,
            "provider_id": provider_id,
            "email_verified": True,
            "last_login_at": datetime.utcnow().isoformat(),
        }

        user = self.create(user_data)
        self._ensure_subscription(str(user.id))

        return user

    def _ensure_subscription(self, user_id: str) -> None:
        """S'assure qu'un utilisateur a une subscription active."""
        try:
            # Vérifier si une subscription existe
            sub_check = (
                self.client.table("subscriptions")
                .select("id")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )

            if sub_check.data:
                return  # Déjà une subscription

            # Créer une subscription Free
            plan_response = (
                self.client.table("plans").select("id").eq("slug", "free").single().execute()
            )

            if plan_response.data:
                self.client.table("subscriptions").insert(
                    {
                        "user_id": user_id,
                        "plan_id": plan_response.data["id"],
                        "status": "active",
                        "billing_period": "monthly",
                    }
                ).execute()

                self.logger.info("Default subscription created", user_id=user_id)
        except Exception as e:
            self.logger.error("Error ensuring subscription", error=str(e))

    def update_last_login(self, user_id: str) -> None:
        """Met à jour la date de dernière connexion."""
        try:
            self.table.update(
                {
                    "last_login_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", user_id).execute()
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
            provider_keys: Clés BYOK à mettre à jour.

        Returns:
            UserInfo mis à jour ou None si erreur.
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url
        if provider_keys is not None:
            # Récupérer les clés actuelles
            current_data = (
                self.table.select("provider_keys_encrypted")
                .eq("id", user_id)
                .single()
                .execute()
                .data
            )
            current_keys = (
                (current_data.get("provider_keys_encrypted") or {}) if current_data else {}
            )

            # Chiffrer et mettre à jour
            for provider, key in provider_keys.items():
                if key:
                    current_keys[provider] = encrypt_value(key)
                elif provider in current_keys:
                    del current_keys[provider]

            update_data["provider_keys_encrypted"] = current_keys

        if not update_data:
            return self.get_by_id(user_id)

        try:
            response = self.table.update(update_data).eq("id", user_id).execute()
            if response.data:
                return self._map_to_user_info(response.data[0])
            return None
        except Exception as e:
            self.logger.error("Error updating profile", error=str(e))
            return None

    def get_user_with_subscription(self, user_id: str) -> UserWithSubscription | None:
        """
        Récupère un profil avec ses informations d'abonnement.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            UserWithSubscription ou None si non trouvé.
        """
        try:
            # Récupérer le profil
            profile_response = self.table.select("*").eq("id", user_id).single().execute()
            if not profile_response.data:
                return None

            profile_data = profile_response.data
            user = self._map_to_user_info(profile_data)

            # Récupérer l'usage via RPC
            usage_response = self.client.rpc(
                "get_user_usage",
                {
                    "p_user_id": user_id,
                },
            ).execute()
            usage_data = usage_response.data[0] if usage_response.data else {}

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

            # Priorité: lire depuis le profil (mis à jour par webhook Stripe)
            effective_plan_slug = profile_data.get("plan_slug") or plan_data.get("slug", "free")
            effective_status = profile_data.get("subscription_status") or sub_data.get(
                "status", "inactive"
            )

            plan_name_map = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
            effective_plan_name = plan_data.get("name") or plan_name_map.get(
                effective_plan_slug, "Free"
            )

            return UserWithSubscription(
                **user.model_dump(),
                plan_slug=effective_plan_slug,
                plan_name=effective_plan_name,
                subscription_status=effective_status,
                billing_period=sub_data.get("billing_period", "monthly"),
                current_period_end=sub_data.get("current_period_end"),
                requests_used=usage_data.get("requests_count", 0),
                requests_limit=usage_data.get("requests_limit", 100),
                documents_used=usage_data.get("documents_count", 0),
                documents_limit=usage_data.get("documents_limit", 10),
                api_keys_used=usage_data.get("api_keys_count", 0),
                api_keys_limit=usage_data.get("api_keys_limit", 1),
                agents_used=usage_data.get("agents_count", 0),
                agents_limit=usage_data.get("agents_limit", 1),
            )
        except Exception as e:
            self.logger.error("Error getting user with subscription", error=str(e))
            return None

    def get_byok_key(self, user_id: str, provider: str) -> str | None:
        """
        Récupère une clé BYOK déchiffrée pour un provider.

        Args:
            user_id: UUID de l'utilisateur.
            provider: Nom du provider (openai, anthropic, etc.).

        Returns:
            Clé déchiffrée ou None.
        """
        try:
            response = (
                self.table.select("provider_keys_encrypted").eq("id", user_id).single().execute()
            )

            if response.data:
                encrypted_keys = response.data.get("provider_keys_encrypted", {}) or {}
                encrypted_key = encrypted_keys.get(provider)
                if encrypted_key:
                    return decrypt_value(encrypted_key)
            return None
        except Exception as e:
            self.logger.error("Error getting BYOK key", error=str(e))
            return None

    def get_decrypted_provider_keys(self, user_id: str) -> dict[str, str]:
        """
        Récupère toutes les clés BYOK déchiffrées pour un utilisateur.

        Cette méthode récupère toutes les clés provider (OpenAI, Mistral, DeepSeek, etc.)
        stockées de manière chiffrée et les retourne déchiffrées.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            Dictionnaire {provider: api_key} avec les clés déchiffrées.
            Retourne un dict vide si aucune clé ou erreur.
        """
        try:
            response = (
                self.table.select("provider_keys_encrypted").eq("id", user_id).single().execute()
            )

            if not response.data:
                return {}

            encrypted_keys = response.data.get("provider_keys_encrypted", {}) or {}

            # Déchiffrer toutes les clés disponibles
            decrypted_keys = {}
            for provider, encrypted_key in encrypted_keys.items():
                if encrypted_key:
                    try:
                        decrypted_keys[provider] = decrypt_value(encrypted_key)
                    except Exception as decrypt_err:
                        self.logger.warning(
                            "Failed to decrypt key for provider",
                            provider=provider,
                            error=str(decrypt_err),
                        )
                        # Continue avec les autres clés même si une échoue
                        continue

            return decrypted_keys

        except Exception as e:
            self.logger.error("Error getting decrypted provider keys", error=str(e))
            return {}


# Alias pour clarté
ProfileRepository = UserRepository
