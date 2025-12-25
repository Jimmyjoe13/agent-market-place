"""
Conversation Repository
========================

Repository pour la gestion des conversations et du feedback loop.
"""

from typing import Any
from uuid import UUID

from src.models.conversation import (
    Conversation,
    ConversationCreate,
    FeedbackFlag,
    FlagType,
    ConversationAnalytics,
)
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository pour les conversations et le feedback."""
    
    def __init__(self) -> None:
        """Initialise le repository conversations."""
        super().__init__("conversations")
    
    def get_by_id(self, id: str) -> Conversation | None:
        """Récupère une conversation par ID."""
        try:
            response = self.table.select("*").eq("id", id).single().execute()
            if response.data:
                return Conversation(**response.data)
            return None
        except Exception as e:
            self.logger.error("Error fetching conversation", error=str(e))
            return None
    
    def create(self, data: dict[str, Any]) -> Conversation:
        """Crée une nouvelle conversation."""
        response = self.table.insert(data).execute()
        self.logger.info("Conversation logged", id=response.data[0]["id"])
        return Conversation(**response.data[0])
    
    def delete(self, id: str) -> bool:
        """Supprime une conversation."""
        try:
            self.table.delete().eq("id", id).execute()
            return True
        except Exception as e:
            self.logger.error("Error deleting conversation", error=str(e))
            return False
    
    def log_conversation(self, conv: ConversationCreate) -> Conversation:
        """
        Enregistre une nouvelle conversation.
        
        Args:
            conv: Données de la conversation.
            
        Returns:
            Conversation créée.
        """
        data = {
            "session_id": conv.session_id,
            "user_query": conv.user_query,
            "ai_response": conv.ai_response,
            "context_sources": [s.model_dump() for s in conv.context_sources],
            "metadata": conv.metadata.model_dump(),
        }
        return self.create(data)
    
    def add_feedback(
        self,
        conversation_id: UUID,
        score: int,
        comment: str | None = None,
    ) -> bool:
        """Ajoute un feedback à une conversation."""
        try:
            self.table.update({
                "feedback_score": score,
                "feedback_comment": comment,
            }).eq("id", str(conversation_id)).execute()
            return True
        except Exception as e:
            self.logger.error("Error adding feedback", error=str(e))
            return False
    
    def flag_for_training(
        self,
        conversation_id: UUID,
        flag_type: FlagType = FlagType.TO_VECTORIZE,
        notes: str | None = None,
    ) -> bool:
        """Marque une conversation pour ré-injection."""
        try:
            self.client.rpc("flag_for_training", {
                "p_conversation_id": str(conversation_id),
                "p_flag_type": flag_type.value,
                "p_notes": notes,
            }).execute()
            return True
        except Exception as e:
            self.logger.error("Error flagging conversation", error=str(e))
            return False
    
    def get_by_session(self, session_id: str) -> list[Conversation]:
        """Récupère toutes les conversations d'une session."""
        response = (
            self.table.select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return [Conversation(**c) for c in response.data]
    
    def get_pending_training(self, limit: int = 50) -> list[dict[str, Any]]:
        """Récupère les données en attente de vectorisation."""
        response = self.client.rpc("get_pending_training_data", {
            "p_limit": limit,
        }).execute()
        return response.data
    
    def get_analytics(self, days: int = 30) -> ConversationAnalytics | None:
        """Récupère les statistiques des conversations."""
        try:
            response = self.client.rpc("get_conversation_analytics", {
                "p_days": days,
            }).execute()
            if response.data:
                return ConversationAnalytics(**response.data[0])
            return None
        except Exception as e:
            self.logger.error("Error getting analytics", error=str(e))
            return None
