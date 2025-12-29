"""Models module for RAG Agent IA - Pydantic data models."""

from src.models.document import Document, DocumentCreate, DocumentMetadata, SourceType
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    FeedbackFlag,
    FlagType,
)
from src.models.api_key import (
    ApiKeyScope,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyInfo,
    ApiKeyValidation,
    ApiKeyUsageStats,
    AgentConfig,
    AgentConfigUpdate,
)
from src.models.user import (
    UserRole,
    OAuthProvider,
    UserCreate,
    UserUpdate,
    UserInfo,
    UserWithSubscription,
    SessionInfo,
)
from src.models.subscription import (
    BillingPeriod,
    SubscriptionStatus,
    PlanSlug,
    PlanInfo,
    SubscriptionInfo,
    SubscriptionWithPlan,
    UsageStats,
)

__all__ = [
    # Document models
    "Document",
    "DocumentCreate", 
    "DocumentMetadata",
    "SourceType",
    # Conversation models
    "Conversation",
    "ConversationCreate",
    "FeedbackFlag",
    "FlagType",
    # API Key models
    "ApiKeyScope",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyInfo",
    "ApiKeyValidation",
    "ApiKeyUsageStats",
    "AgentConfig",
    "AgentConfigUpdate",
    # User models
    "UserRole",
    "OAuthProvider",
    "UserCreate",
    "UserUpdate",
    "UserInfo",
    "UserWithSubscription",
    "SessionInfo",
    # Subscription models
    "BillingPeriod",
    "SubscriptionStatus",
    "PlanSlug",
    "PlanInfo",
    "SubscriptionInfo",
    "SubscriptionWithPlan",
    "UsageStats",
]
