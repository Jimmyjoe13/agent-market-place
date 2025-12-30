"""
Stripe Service
==============

Gère les interactions avec l'API Stripe :
- Création de sessions de paiement (Checkout)
- Gestion du portail client
- Traitement des webhooks
- Synchronisation des abonnements
"""

import stripe
from typing import Any, Optional
from src.config.settings import get_settings
from src.config.logging_config import get_logger
from src.repositories.user_repository import UserRepository

logger = get_logger(__name__)

class StripeService:
    def __init__(self):
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key
        self.webhook_secret = settings.stripe_webhook_secret
        self.user_repo = UserRepository()
        self.frontend_url = settings.frontend_url

    async def create_checkout_session(self, user_id: str, plan_type: str) -> str:
        """
        Crée une session Stripe Checkout pour un utilisateur.
        """
        settings = get_settings()
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Utilisateur non trouvé")

        # Déterminer le Price ID (Stripe utilise des Price IDs pour les abonnements)
        # Note: Dans sa requête, l'utilisateur a donné des Product IDs. 
        # Pour Checkout en mode abonnement, il faut techniquement le Price ID.
        # Si prod_xxx est passé, Stripe peut essayer de trouver le prix par défaut if set.
        price_id = settings.stripe_plan_pro_monthly if plan_type == "monthly" else settings.stripe_plan_pro_yearly

        try:
            session = stripe.checkout.Session.create(
                customer_email=user.email,
                client_reference_id=user_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    },
                ],
                mode="subscription",
                success_url=f"{self.frontend_url}/settings?tab=billing&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.frontend_url}/settings?tab=billing",
                metadata={
                    "user_id": user_id,
                    "plan_type": plan_type
                }
            )
            return session.url
        except Exception as e:
            logger.error("Stripe Checkout Error", error=str(e))
            raise

    async def create_portal_session(self, user_id: str) -> str:
        """
        Crée une session pour le portail client Stripe.
        """
        user_data = self.user_repo.table.select("stripe_customer_id").eq("id", user_id).single().execute().data
        customer_id = user_data.get("stripe_customer_id") if user_data else None

        if not customer_id:
            # Si pas encore de client Stripe, on ne peut pas ouvrir le portail
            raise ValueError("Aucun abonnement actif trouvé")

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{self.frontend_url}/settings?tab=billing",
            )
            return session.url
        except Exception as e:
            logger.error("Stripe Portal Error", error=str(e))
            raise

    async def handle_webhook(self, payload: bytes, sig_header: str) -> bool:
        """
        Traite les événements envoyés par Stripe.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False

        # Traitement des événements
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await self._handle_checkout_completed(session)
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await self._handle_subscription_updated(subscription)
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await self._handle_subscription_deleted(subscription)

        return True

    async def _handle_checkout_completed(self, session: Any):
        user_id = session.get("client_reference_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not user_id:
            return

        # Mettre à jour l'utilisateur en DB
        self.user_repo.table.update({
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "plan_slug": "pro",
            "subscription_status": "active"
        }).eq("id", user_id).execute()
        
        logger.info("Subscription activated", user_id=user_id, customer_id=customer_id)

    async def _handle_subscription_updated(self, subscription: Any):
        customer_id = subscription.get("customer")
        status = subscription.get("status")
        
        # Trouver l'utilisateur par stripe_customer_id
        self.user_repo.table.update({
            "subscription_status": status
        }).eq("stripe_customer_id", customer_id).execute()

    async def _handle_subscription_deleted(self, subscription: Any):
        customer_id = subscription.get("customer")
        
        # Retour au plan free
        self.user_repo.table.update({
            "plan_slug": "free",
            "subscription_status": "canceled"
        }).eq("stripe_customer_id", customer_id).execute()
