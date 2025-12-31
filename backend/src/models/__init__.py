"""
Models module for Agent Market Place - Pydantic data models.

Version 2.0.0 - Refactored with agents/api_keys separation and profiles.
"""

from src.models.document import Document, DocumentCreate, DocumentMetadata, SourceType
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    FeedbackFlag,
    FlagType,
)
from src.models.agent import (
    AgentCreate,
    AgentUpdate,
    AgentInfo,
    AgentWithStats,
    AgentConfig,
    AgentListResponse,
)
from src.models.api_key import (
    ApiKeyScope,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyInfo,
    ApiKeyValidation,
    ApiKeyUsageStats,
    ApiKeyListResponse,
    # Deprecated but kept for backward compat
    AgentConfigUpdate,
)
from src.models.user import (
    UserRole,
    OAuthProvider,
    # New names
    ProfileCreate,
    ProfileUpdate,
    ProfileInfo,
    ProfileWithSubscription,
    # Backward compat aliases
    UserCreate,
    UserUpdate,
    UserInfo,
    UserWithSubscription,
    SessionInfo,
    OAuthCallback,
    OAuthTokenResponse,
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
