"""
Billing Routes
==============

Endpoints pour la gestion des abonnements et paiements Stripe.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Optional
from src.api.auth import get_current_user
from src.models.user import UserWithSubscription, UserInfo
from src.services.stripe_service import StripeService

router = APIRouter(prefix="/billing", tags=["Billing"])

def get_stripe_service():
    return StripeService()

@router.post("/checkout")
async def create_checkout(
    plan: str, # "monthly" or "yearly"
    user: UserWithSubscription = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """
    Crée une session Stripe Checkout.
    """
    try:
        url = await stripe_service.create_checkout_session(str(user.id), plan)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal")
async def create_portal(
    user: UserWithSubscription = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """
    Crée une session pour le portail client Stripe.
    """
    try:
        url = await stripe_service.create_portal_session(str(user.id))
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """
    Webhook Stripe pour recevoir les événements de paiement.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
    payload = await request.body()
    success = await stripe_service.handle_webhook(payload, stripe_signature)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
    return {"status": "success"}
