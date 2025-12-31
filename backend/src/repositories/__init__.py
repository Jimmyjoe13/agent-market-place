"""
Repositories module - Database access layer using Repository pattern.

Version 2.0.0 - Added AgentRepository, ProfileRepository alias.
"""

from src.repositories.base import BaseRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.api_key_repository import ApiKeyRepository
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository, ProfileRepository
from src.repositories.subscription_repository import SubscriptionRepository

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
