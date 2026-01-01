"""
Tests unitaires pour StripeService - Protection anti-rejeu webhooks
====================================================================

Vérifie que les webhooks Stripe sont protégés contre:
- Les attaques par rejeu (même event_id)
- Les events trop vieux (> 5 minutes)
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def mock_stripe_settings():
    """Mock des settings pour Stripe."""
    settings = MagicMock()
    settings.stripe_secret_key = "sk_test_xxx"
    settings.stripe_webhook_secret = "whsec_xxx"
    settings.frontend_url = "http://localhost:3000"
    settings.stripe_price_pro_monthly = "price_monthly"
    settings.stripe_price_pro_yearly = "price_yearly"
    return settings


@pytest.fixture
def stripe_service(mock_stripe_settings):
    """Crée une instance de StripeService avec mocks."""
    with patch("src.services.stripe_service.get_settings", return_value=mock_stripe_settings):
        with patch("src.services.stripe_service.UserRepository") as mock_repo:
            mock_repo_instance = MagicMock()
            mock_repo_instance.client = MagicMock()
            mock_repo.return_value = mock_repo_instance
            
            from src.services.stripe_service import StripeService
            service = StripeService()
            yield service


@pytest.fixture
def valid_webhook_event():
    """Crée un event webhook valide."""
    return {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "created": int(time.time()),  # Event créé maintenant
        "data": {
            "object": {
                "client_reference_id": "user_123",
                "customer": "cus_xxx",
                "subscription": "sub_xxx"
            }
        }
    }


@pytest.fixture
def old_webhook_event():
    """Crée un event webhook trop vieux (10 minutes)."""
    return {
        "id": "evt_old_456",
        "type": "checkout.session.completed",
        "created": int(time.time()) - 600,  # 10 minutes
        "data": {
            "object": {
                "client_reference_id": "user_123",
                "customer": "cus_xxx",
                "subscription": "sub_xxx"
            }
        }
    }


class TestWebhookReplayProtection:
    """Tests pour la protection anti-rejeu des webhooks."""

    @pytest.mark.asyncio
    async def test_valid_webhook_is_processed(self, stripe_service, valid_webhook_event):
        """Un webhook valide et nouveau doit être traité."""
        import stripe
        
        with patch.object(stripe.Webhook, "construct_event", return_value=valid_webhook_event):
            # Mock: event non traité auparavant
            stripe_service._is_event_already_processed = MagicMock(return_value=False)
            stripe_service._mark_event_as_processed = MagicMock()
            stripe_service._handle_checkout_completed = AsyncMock()
            
            result = await stripe_service.handle_webhook(b"payload", "sig_header")
            
            assert result is True
            stripe_service._is_event_already_processed.assert_called_once_with("evt_test_123")
            stripe_service._mark_event_as_processed.assert_called_once_with(
                "evt_test_123", 
                "checkout.session.completed"
            )
            stripe_service._handle_checkout_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_replayed_webhook_is_rejected(self, stripe_service, valid_webhook_event):
        """Un webhook déjà traité doit être rejeté."""
        import stripe
        
        with patch.object(stripe.Webhook, "construct_event", return_value=valid_webhook_event):
            # Mock: event déjà traité
            stripe_service._is_event_already_processed = MagicMock(return_value=True)
            stripe_service._handle_checkout_completed = AsyncMock()
            
            result = await stripe_service.handle_webhook(b"payload", "sig_header")
            
            assert result is False
            stripe_service._is_event_already_processed.assert_called_once_with("evt_test_123")
            # Le handler ne doit pas être appelé
            stripe_service._handle_checkout_completed.assert_not_called()

    @pytest.mark.asyncio
    async def test_old_webhook_is_rejected(self, stripe_service, old_webhook_event):
        """Un webhook trop vieux (> 5 minutes) doit être rejeté."""
        import stripe
        
        with patch.object(stripe.Webhook, "construct_event", return_value=old_webhook_event):
            stripe_service._is_event_already_processed = MagicMock(return_value=False)
            stripe_service._handle_checkout_completed = AsyncMock()
            
            result = await stripe_service.handle_webhook(b"payload", "sig_header")
            
            assert result is False
            # Ne doit même pas vérifier si déjà traité car trop vieux - l'ordre est timestamp puis rejeu
            stripe_service._handle_checkout_completed.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_signature_is_rejected(self, stripe_service):
        """Un webhook avec signature invalide doit être rejeté."""
        import stripe
        
        with patch.object(
            stripe.Webhook, 
            "construct_event", 
            side_effect=stripe.error.SignatureVerificationError("Invalid", "sig")
        ):
            result = await stripe_service.handle_webhook(b"payload", "bad_sig")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_invalid_payload_is_rejected(self, stripe_service):
        """Un webhook avec payload invalide doit être rejeté."""
        import stripe
        
        with patch.object(
            stripe.Webhook, 
            "construct_event", 
            side_effect=ValueError("Invalid JSON")
        ):
            result = await stripe_service.handle_webhook(b"bad_payload", "sig")
            
            assert result is False


class TestWebhookEventStorage:
    """Tests pour le stockage des events traités."""

    def test_is_event_already_processed_returns_true_when_exists(self, stripe_service):
        """Doit retourner True si l'event existe en DB."""
        # Mock la réponse Supabase
        mock_response = MagicMock()
        mock_response.data = [{"event_id": "evt_123"}]
        stripe_service.user_repo.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = stripe_service._is_event_already_processed("evt_123")
        
        assert result is True

    def test_is_event_already_processed_returns_false_when_not_exists(self, stripe_service):
        """Doit retourner False si l'event n'existe pas en DB."""
        mock_response = MagicMock()
        mock_response.data = []
        stripe_service.user_repo.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = stripe_service._is_event_already_processed("evt_new")
        
        assert result is False

    def test_is_event_already_processed_returns_true_on_db_error(self, stripe_service):
        """Doit retourner True (refuser) en cas d'erreur DB par sécurité."""
        stripe_service.user_repo.client.table.side_effect = Exception("DB Error")
        
        result = stripe_service._is_event_already_processed("evt_123")
        
        assert result is True  # Refuse par précaution

    def test_mark_event_as_processed_inserts_record(self, stripe_service):
        """Doit insérer un enregistrement en DB."""
        stripe_service._mark_event_as_processed("evt_123", "checkout.session.completed")
        
        stripe_service.user_repo.client.table.assert_called_with("processed_webhook_events")
        stripe_service.user_repo.client.table.return_value.insert.assert_called_once_with({
            "event_id": "evt_123",
            "event_type": "checkout.session.completed"
        })

    def test_mark_event_as_processed_handles_error_gracefully(self, stripe_service):
        """Ne doit pas lever d'exception en cas d'erreur DB."""
        stripe_service.user_repo.client.table.return_value.insert.side_effect = Exception("DB Error")
        
        # Ne doit pas lever d'exception
        stripe_service._mark_event_as_processed("evt_123", "test")
