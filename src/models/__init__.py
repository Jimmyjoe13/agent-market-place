"""Models module for RAG Agent IA - Pydantic data models."""

from src.models.document import Document, DocumentCreate, DocumentMetadata, SourceType
from src.models.conversation import (
    Conversation,
    ConversationCreate,
    FeedbackFlag,
    FlagType,
)

__all__ = [
    "Document",
    "DocumentCreate", 
    "DocumentMetadata",
    "SourceType",
    "Conversation",
    "ConversationCreate",
    "FeedbackFlag",
    "FlagType",
]
