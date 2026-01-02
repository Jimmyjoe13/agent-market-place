"""
Subscription & Plan Models
===========================

Modèles Pydantic pour le système de monétisation.

Ce module définit les structures de données pour :
- Plans d'abonnement (Free, Pro, Scale, Enterprise)
- Subscriptions utilisateur
- Usage et facturation
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class BillingPeriod(str, Enum):
    """Période de facturation."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Statut d'un abonnement."""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PAUSED = "paused"


class PlanSlug(str, Enum):
    """Identifiants des plans disponibles."""

    FREE = "free"
    PRO = "pro"
    SCALE = "scale"
    ENTERPRISE = "enterprise"


# ===== Plan Models =====


class PlanFeature(BaseModel):
    """Feature d'un plan."""

    name: str = Field(..., description="Nom de la feature")
    included: bool = Field(default=True, description="Incluse dans le plan")
    limit: int | None = Field(default=None, description="Limite si applicable")


class PlanInfo(BaseModel):
    """
    Informations complètes d'un plan.

    Utilisé pour l'affichage sur la page pricing.
    """

    id: UUID = Field(..., description="Identifiant unique")
    slug: PlanSlug = Field(..., description="Identifiant du plan")
    name: str = Field(..., description="Nom d'affichage")
    description: str | None = Field(default=None, description="Description")

    # Prix
    price_monthly_cents: int = Field(default=0, description="Prix mensuel en centimes")
    price_yearly_cents: int = Field(default=0, description="Prix annuel en centimes")

    # Quotas
    requests_per_month: int = Field(default=100, description="Requêtes/mois (-1 = illimité)")
    api_keys_limit: int = Field(default=1, description="Limite clés API (-1 = illimité)")
    documents_limit: int = Field(default=10, description="Limite documents (-1 = illimité)")

    # Overage
    overage_price_cents: float = Field(default=0, description="Prix/requête au-delà du quota")

    # Features
    features: list[str] = Field(default_factory=list, description="Liste des features")

    # Meta
    display_order: int = Field(default=0, description="Ordre d'affichage")
    is_active: bool = Field(default=True, description="Disponible pour nouveaux abonnements")

    model_config = {"from_attributes": True}

    @property
    def price_monthly(self) -> float:
        """Prix mensuel en euros."""
        return self.price_monthly_cents / 100

    @property
    def price_yearly(self) -> float:
        """Prix annuel en euros."""
        return self.price_yearly_cents / 100

    @property
    def monthly_savings_percent(self) -> int:
        """Économie en % avec l'abonnement annuel."""
        if self.price_monthly_cents == 0:
            return 0
        yearly_monthly_equivalent = self.price_yearly_cents / 12
        savings = (
            (self.price_monthly_cents - yearly_monthly_equivalent) / self.price_monthly_cents * 100
        )
        return int(savings)


class PlanListResponse(BaseModel):
    """Réponse avec la liste des plans."""

    plans: list[PlanInfo] = Field(..., description="Liste des plans")


# ===== Subscription Models =====


class SubscriptionInfo(BaseModel):
    """
    Informations d'abonnement utilisateur.

    Utilisé dans le dashboard et pour les vérifications de quota.
    """

    id: UUID = Field(..., description="Identifiant unique")
    user_id: UUID = Field(..., description="ID utilisateur")
    plan_id: UUID = Field(..., description="ID du plan")

    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    billing_period: BillingPeriod = Field(default=BillingPeriod.MONTHLY)

    # Stripe (si applicable)
    stripe_subscription_id: str | None = Field(default=None)
    stripe_customer_id: str | None = Field(default=None)

    # Période
    current_period_start: datetime = Field(..., description="Début période")
    current_period_end: datetime = Field(..., description="Fin période")

    # Annulation
    canceled_at: datetime | None = Field(default=None)
    cancel_at_period_end: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    model_config = {"from_attributes": True}


class SubscriptionWithPlan(SubscriptionInfo):
    """Subscription avec détails du plan."""

    plan: PlanInfo = Field(..., description="Détails du plan")


class SubscriptionCreate(BaseModel):
    """Création d'un abonnement."""

    plan_slug: PlanSlug = Field(..., description="Plan choisi")
    billing_period: BillingPeriod = Field(default=BillingPeriod.MONTHLY)
    stripe_payment_method_id: str | None = Field(
        default=None, description="ID Stripe du moyen de paiement"
    )


class SubscriptionUpdate(BaseModel):
    """Mise à jour d'un abonnement (upgrade/downgrade)."""

    plan_slug: PlanSlug | None = Field(default=None, description="Nouveau plan")
    billing_period: BillingPeriod | None = Field(default=None, description="Nouvelle période")
    cancel_at_period_end: bool | None = Field(default=None, description="Annuler à la fin")


# ===== Usage Models =====


class UsageStats(BaseModel):
    """
    Statistiques d'usage du mois en cours.

    Utilisé dans le dashboard pour afficher la consommation.
    """

    period: str = Field(..., description="Période (YYYY-MM)")

    # Compteurs
    requests_count: int = Field(default=0, description="Requêtes effectuées")
    documents_count: int = Field(default=0, description="Documents créés")
    api_keys_count: int = Field(default=0, description="Clés API actives")
    agents_count: int = Field(default=0, description="Agents actifs")
    tokens_used: int = Field(default=0, description="Tokens consommés")

    # Limites du plan
    requests_limit: int = Field(default=100, description="Limite requêtes")
    documents_limit: int = Field(default=10, description="Limite documents")
    api_keys_limit: int = Field(default=1, description="Limite clés")
    agents_limit: int = Field(default=1, description="Limite agents")

    # Overage
    overage_requests: int = Field(default=0, description="Requêtes au-delà du quota")
    overage_amount_cents: int = Field(default=0, description="Montant overage")

    @property
    def requests_percentage(self) -> int:
        """Pourcentage de requêtes utilisées."""
        if self.requests_limit <= 0:
            return 0  # Illimité
        return min(100, int(self.requests_count / self.requests_limit * 100))

    @property
    def is_over_quota(self) -> bool:
        """True si au-delà du quota."""
        return self.requests_limit > 0 and self.requests_count > self.requests_limit


class UsageRecord(BaseModel):
    """Enregistrement d'usage détaillé."""

    id: UUID = Field(...)
    user_id: UUID = Field(...)
    subscription_id: UUID | None = Field(default=None)
    period: str = Field(...)

    requests_count: int = Field(default=0)
    documents_count: int = Field(default=0)
    api_keys_count: int = Field(default=0)

    overage_requests: int = Field(default=0)
    overage_amount_cents: int = Field(default=0)

    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    model_config = {"from_attributes": True}


# ===== Billing Models =====


class Invoice(BaseModel):
    """Facture générée."""

    id: str = Field(..., description="ID Stripe de la facture")
    amount_cents: int = Field(..., description="Montant en centimes")
    status: str = Field(..., description="Statut (paid, open, void)")
    currency: str = Field(default="eur", description="Devise")
    period_start: datetime = Field(..., description="Début période")
    period_end: datetime = Field(..., description="Fin période")
    invoice_url: str | None = Field(default=None, description="URL PDF")
    created_at: datetime = Field(...)


class CheckoutSession(BaseModel):
    """Session de paiement Stripe Checkout."""

    session_id: str = Field(..., description="ID de la session Checkout")
    url: str = Field(..., description="URL de redirection vers Stripe")
    expires_at: datetime = Field(..., description="Expiration de la session")


class BillingPortalSession(BaseModel):
    """Session du portail de facturation Stripe."""

    url: str = Field(..., description="URL du portail Stripe")
