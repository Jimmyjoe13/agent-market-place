"""
Stripe Service
==============

Gère les interactions avec l'API Stripe :
- Création de sessions de paiement (Checkout)
- Gestion du portail client
- Traitement des webhooks
- Synchronisation des abonnements
"""

from typing import Any

import stripe

from src.config.logging_config import get_logger
from src.config.settings import get_settings
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

        # Déterminer le Price ID
        price_id = (
            settings.stripe_price_pro_monthly
            if plan_type == "monthly"
            else settings.stripe_price_pro_yearly
        )

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
                metadata={"user_id": user_id, "plan_type": plan_type},
            )
            return session.url
        except Exception as e:
            logger.error("Stripe Checkout Error", error=str(e))
            raise

    async def create_portal_session(self, user_id: str) -> str:
        """
        Crée une session pour le portail client Stripe.
        """
        user_data = (
            self.user_repo.table.select("stripe_customer_id")
            .eq("id", user_id)
            .single()
            .execute()
            .data
        )
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

        Sécurité anti-rejeu:
        - Vérifie que l'event n'a pas déjà été traité
        - Vérifie que l'event n'est pas trop vieux (> 5 minutes)
        - Enregistre l'event_id après traitement réussi
        """
        import time

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except ValueError:
            logger.warning("Webhook: Invalid payload")
            return False
        except stripe.error.SignatureVerificationError:
            logger.warning("Webhook: Invalid signature")
            return False

        event_id = event.get("id")
        event_type = event.get("type")
        event_created = event.get("created", 0)

        # Vérification 1: Event trop vieux (> 5 minutes = 300 secondes)
        current_time = int(time.time())
        if current_time - event_created > 300:
            logger.warning(
                "Webhook rejected: Event too old",
                event_id=event_id,
                event_age_seconds=current_time - event_created,
            )
            return False

        # Vérification 2: Event déjà traité (anti-rejeu)
        if self._is_event_already_processed(event_id):
            logger.warning(
                "Webhook rejected: Replay attack detected", event_id=event_id, event_type=event_type
            )
            return False

        # Traitement des événements
        try:
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                await self._handle_checkout_completed(session)
            elif event_type == "customer.subscription.updated":
                subscription = event["data"]["object"]
                await self._handle_subscription_updated(subscription)
            elif event_type == "customer.subscription.deleted":
                subscription = event["data"]["object"]
                await self._handle_subscription_deleted(subscription)

            # Enregistrer l'event comme traité
            self._mark_event_as_processed(event_id, event_type)

            logger.info("Webhook processed successfully", event_id=event_id, event_type=event_type)
            return True

        except Exception as e:
            logger.error(
                "Webhook processing error", event_id=event_id, event_type=event_type, error=str(e)
            )
            # Ne pas marquer comme traité en cas d'erreur pour permettre un retry
            return False

    def _is_event_already_processed(self, event_id: str) -> bool:
        """Vérifie si un event a déjà été traité."""
        try:
            result = (
                self.user_repo.client.table("processed_webhook_events")
                .select("event_id")
                .eq("event_id", event_id)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error("Error checking webhook event", error=str(e))
            # En cas d'erreur DB, on refuse par précaution
            return True

    def _mark_event_as_processed(self, event_id: str, event_type: str) -> None:
        """Enregistre un event comme traité."""
        try:
            self.user_repo.client.table("processed_webhook_events").insert(
                {"event_id": event_id, "event_type": event_type}
            ).execute()
        except Exception as e:
            # Log mais ne pas échouer - l'event est déjà traité
            logger.warning(
                "Failed to mark webhook event as processed", event_id=event_id, error=str(e)
            )

    async def _handle_checkout_completed(self, session: Any):
        user_id = session.get("client_reference_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not user_id:
            return

        # Mettre à jour l'utilisateur en DB
        self.user_repo.table.update(
            {
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "plan_slug": "pro",
                "subscription_status": "active",
            }
        ).eq("id", user_id).execute()

        logger.info("Subscription activated", user_id=user_id, customer_id=customer_id)

    async def _handle_subscription_updated(self, subscription: Any):
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        # Trouver l'utilisateur par stripe_customer_id
        self.user_repo.table.update({"subscription_status": status}).eq(
            "stripe_customer_id", customer_id
        ).execute()

    async def _handle_subscription_deleted(self, subscription: Any):
        customer_id = subscription.get("customer")

        # Retour au plan free
        self.user_repo.table.update({"plan_slug": "free", "subscription_status": "canceled"}).eq(
            "stripe_customer_id", customer_id
        ).execute()
