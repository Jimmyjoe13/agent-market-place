"""
Repositories module - Database access layer using Repository pattern.

Version 2.0.0 - Added AgentRepository, ProfileRepository alias.
"""

from src.repositories.agent_repository import AgentRepository
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.base import BaseRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.repositories.user_repository import ProfileRepository, UserRepository

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "ConversationRepository",
    "ApiKeyRepository",
    "AgentRepository",
    "UserRepository",
    "ProfileRepository",
    "SubscriptionRepository",
]
