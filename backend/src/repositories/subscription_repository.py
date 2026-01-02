"""
Subscription Repository
========================

Repository pour la gestion des abonnements et plans dans Supabase.

Ce module fournit les opérations pour :
- Lister les plans disponibles
- Gérer les subscriptions utilisateur
- Tracker l'usage pour facturation

Example:
    >>> from src.repositories.subscription_repository import SubscriptionRepository
    >>> repo = SubscriptionRepository()
    >>> plans = repo.list_plans()
    >>> usage = repo.get_user_usage("user-uuid")
"""

from datetime import datetime, timedelta
from typing import Any

from src.models.subscription import (
    BillingPeriod,
    PlanInfo,
    SubscriptionInfo,
    SubscriptionWithPlan,
    UsageStats,
)
from src.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[SubscriptionInfo]):
    """
    Repository pour les opérations sur les abonnements.

    Gère les plans, subscriptions et usage tracking.
    """

    def __init__(self) -> None:
        """Initialise le repository subscriptions."""
        super().__init__("subscriptions")

    def get_by_id(self, id: str) -> SubscriptionInfo | None:
        """Récupère une subscription par ID."""
        try:
            response = self.table.select("*").eq("id", id).single().execute()
            if response.data:
                return SubscriptionInfo(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching subscription", id=id, error=str(e))
            return None

    def create(self, data: dict[str, Any]) -> SubscriptionInfo:
        """Crée une nouvelle subscription."""
        response = self.table.insert(data).execute()
        return SubscriptionInfo(**response.data[0])

    def delete(self, id: str) -> bool:
        """Supprime une subscription."""
        try:
            self.table.delete().eq("id", id).execute()
            return True
        except Exception as e:
            self.logger.error("Error deleting subscription", error=str(e))
            return False

    # ===== Plans =====

    def list_plans(self, include_inactive: bool = False) -> list[PlanInfo]:
        """
        Liste tous les plans disponibles.

        Args:
            include_inactive: Inclure les plans désactivés.

        Returns:
            Liste des plans triés par display_order.
        """
        query = self.client.table("plans").select("*")

        if not include_inactive:
            query = query.eq("is_active", True)

        query = query.order("display_order")
        response = query.execute()

        return [PlanInfo(**p) for p in response.data]

    def get_plan_by_slug(self, slug: str) -> PlanInfo | None:
        """
        Récupère un plan par son slug.

        Args:
            slug: Identifiant du plan (free, pro, scale, enterprise).

        Returns:
            PlanInfo ou None si non trouvé.
        """
        try:
            response = self.client.table("plans").select("*").eq("slug", slug).single().execute()
            if response.data:
                return PlanInfo(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching plan", slug=slug, error=str(e))
            return None

    # ===== User Subscription =====

    def get_user_subscription(self, user_id: str) -> SubscriptionWithPlan | None:
        """
        Récupère l'abonnement actif d'un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            SubscriptionWithPlan ou None si pas d'abonnement.
        """
        try:
            response = (
                self.table.select("*, plans(*)")
                .eq("user_id", user_id)
                .eq("status", "active")
                .single()
                .execute()
            )

            if not response.data:
                return None

            sub_data = response.data
            plan_data = sub_data.pop("plans", {})

            return SubscriptionWithPlan(
                **sub_data,
                plan=PlanInfo(**plan_data) if plan_data else None,
            )
        except Exception:
            self.logger.debug("No active subscription found", user_id=user_id)
            return None

    def create_subscription(
        self,
        user_id: str,
        plan_slug: str,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY,
        stripe_subscription_id: str | None = None,
        stripe_customer_id: str | None = None,
    ) -> SubscriptionInfo | None:
        """
        Crée un nouvel abonnement pour un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.
            plan_slug: Slug du plan choisi.
            billing_period: Période de facturation.
            stripe_subscription_id: ID Stripe (si applicable).
            stripe_customer_id: Customer ID Stripe.

        Returns:
            SubscriptionInfo créée ou None si erreur.
        """
        # Récupérer le plan
        plan = self.get_plan_by_slug(plan_slug)
        if not plan:
            self.logger.error("Plan not found", slug=plan_slug)
            return None

        # Calculer la période
        period_days = 365 if billing_period == BillingPeriod.YEARLY else 30
        current_period_end = datetime.utcnow() + timedelta(days=period_days)

        # Annuler l'abonnement existant si présent
        existing = self.get_user_subscription(user_id)
        if existing:
            self.cancel_subscription(str(existing.id), immediate=True)

        # Créer le nouvel abonnement
        sub_data = {
            "user_id": user_id,
            "plan_id": str(plan.id),
            "status": "active",
            "billing_period": billing_period.value,
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_customer_id": stripe_customer_id,
            "current_period_start": datetime.utcnow().isoformat(),
            "current_period_end": current_period_end.isoformat(),
        }

        subscription = self.create(sub_data)

        self.logger.info(
            "Subscription created",
            user_id=user_id,
            plan=plan_slug,
            period=billing_period.value,
        )

        return subscription

    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
    ) -> bool:
        """
        Annule un abonnement.

        Args:
            subscription_id: UUID de la subscription.
            immediate: Si True, annulation immédiate. Sinon, à la fin de la période.

        Returns:
            True si annulé avec succès.
        """
        try:
            update_data = {
                "canceled_at": datetime.utcnow().isoformat(),
            }

            if immediate:
                update_data["status"] = "canceled"
            else:
                update_data["cancel_at_period_end"] = True

            self.table.update(update_data).eq("id", subscription_id).execute()

            self.logger.info(
                "Subscription canceled",
                subscription_id=subscription_id,
                immediate=immediate,
            )

            return True
        except Exception as e:
            self.logger.error("Error canceling subscription", error=str(e))
            return False

    def upgrade_subscription(
        self,
        user_id: str,
        new_plan_slug: str,
    ) -> SubscriptionInfo | None:
        """
        Upgrade/Downgrade un abonnement.

        Args:
            user_id: UUID de l'utilisateur.
            new_plan_slug: Nouveau plan.

        Returns:
            SubscriptionInfo mise à jour.
        """
        existing = self.get_user_subscription(user_id)
        if not existing:
            # Créer un nouvel abonnement
            return self.create_subscription(user_id, new_plan_slug)

        # Récupérer le nouveau plan
        new_plan = self.get_plan_by_slug(new_plan_slug)
        if not new_plan:
            return None

        try:
            # Mettre à jour le plan
            self.table.update(
                {
                    "plan_id": str(new_plan.id),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", str(existing.id)).execute()

            self.logger.info(
                "Subscription upgraded",
                user_id=user_id,
                old_plan=existing.plan.slug if existing.plan else "unknown",
                new_plan=new_plan_slug,
            )

            return self.get_user_subscription(user_id)
        except Exception as e:
            self.logger.error("Error upgrading subscription", error=str(e))
            return None

    # ===== Usage Tracking =====

    def get_user_usage(self, user_id: str) -> UsageStats | None:
        """
        Récupère l'usage du mois en cours pour un utilisateur.

        Args:
            user_id: UUID de l'utilisateur.

        Returns:
            UsageStats ou None si erreur.
        """
        try:
            response = self.client.rpc(
                "get_user_usage",
                {
                    "p_user_id": user_id,
                },
            ).execute()

            if not response.data:
                return None

            data = response.data[0]
            current_period = datetime.utcnow().strftime("%Y-%m")

            return UsageStats(
                period=current_period,
                requests_count=data.get("requests_count", 0),
                documents_count=data.get("documents_count", 0),
                api_keys_count=data.get("api_keys_count", 0),
                requests_limit=data.get("requests_limit", 100),
                documents_limit=data.get("documents_limit", 10),
                api_keys_limit=data.get("api_keys_limit", 1),
                overage_requests=data.get("overage_requests", 0),
            )
        except Exception as e:
            self.logger.error("Error getting user usage", error=str(e))
            return None

    def check_user_limits(
        self,
        user_id: str,
        action: str = "request",
    ) -> dict[str, Any]:
        """
        Vérifie si l'utilisateur peut effectuer une action.

        Args:
            user_id: UUID de l'utilisateur.
            action: Type d'action (request, document, api_key).

        Returns:
            Dict avec 'allowed' (bool), 'reason' (str), 'usage', 'limits'.
        """
        try:
            response = self.client.rpc(
                "check_user_limits",
                {
                    "p_user_id": user_id,
                    "p_action": action,
                },
            ).execute()

            if response.data:
                return response.data

            return {"allowed": False, "reason": "unknown_error"}
        except Exception as e:
            self.logger.error("Error checking user limits", error=str(e))
            return {"allowed": False, "reason": "database_error"}

    def increment_usage(
        self,
        user_id: str,
        usage_type: str = "requests",
        amount: int = 1,
    ) -> bool:
        """
        Incrémente un compteur d'usage.

        Args:
            user_id: UUID de l'utilisateur.
            usage_type: Type d'usage (requests, documents, api_keys).
            amount: Montant à incrémenter.

        Returns:
            True si incrémenté avec succès.
        """
        try:
            if usage_type == "requests":
                self.client.rpc(
                    "increment_user_requests",
                    {
                        "p_user_id": user_id,
                    },
                ).execute()
            else:
                # Pour documents et api_keys, mise à jour directe
                current_period = datetime.utcnow().strftime("%Y-%m")
                column = f"{usage_type}_count"

                # Upsert le record d'usage
                self.client.table("usage_records").upsert(
                    {
                        "user_id": user_id,
                        "period": current_period,
                        column: amount,
                    },
                    on_conflict="user_id,period",
                ).execute()

            return True
        except Exception as e:
            self.logger.error("Error incrementing usage", error=str(e))
            return False
