"""
Models module for Agent Market Place - Pydantic data models.

Version 2.0.0 - Refactored with agents/api_keys separation and profiles.
"""

from src.models.agent import (
    AgentConfig,
    AgentCreate,
    AgentInfo,
    AgentListResponse,
    AgentUpdate,
    AgentWithStats,
)
from src.models.api_key import (
    # Deprecated but kept for backward compat
    AgentConfigUpdate,
    ApiKeyCreate,
    ApiKeyInfo,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyScope,
    ApiKeyUsageStats,
    ApiKeyValidation,
)
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    FeedbackFlag,
    FlagType,
)
from src.models.document import Document, DocumentCreate, DocumentMetadata, SourceType
from src.models.subscription import (
    BillingPeriod,
    PlanInfo,
    PlanSlug,
    SubscriptionInfo,
    SubscriptionStatus,
    SubscriptionWithPlan,
    UsageStats,
)
from src.models.user import (
    OAuthCallback,
    OAuthProvider,
    OAuthTokenResponse,
    # New names
    ProfileCreate,
    ProfileInfo,
    ProfileUpdate,
    ProfileWithSubscription,
    SessionInfo,
    # Backward compat aliases
    UserCreate,
    UserInfo,
    UserRole,
    UserUpdate,
    UserWithSubscription,
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
    # Agent models (NEW)
    "AgentCreate",
    "AgentUpdate",
    "AgentInfo",
    "AgentWithStats",
    "AgentConfig",
    "AgentListResponse",
    # API Key models
    "ApiKeyScope",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyInfo",
    "ApiKeyValidation",
    "ApiKeyUsageStats",
    "ApiKeyListResponse",
    "AgentConfigUpdate",  # Deprecated
    # Profile/User models
    "UserRole",
    "OAuthProvider",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileInfo",
    "ProfileWithSubscription",
    "UserCreate",  # Alias
    "UserUpdate",  # Alias
    "UserInfo",  # Alias
    "UserWithSubscription",  # Alias
    "SessionInfo",
    "OAuthCallback",
    "OAuthTokenResponse",
    # Subscription models
    "BillingPeriod",
    "SubscriptionStatus",
    "PlanSlug",
    "PlanInfo",
    "SubscriptionInfo",
    "SubscriptionWithPlan",
    "UsageStats",
]
