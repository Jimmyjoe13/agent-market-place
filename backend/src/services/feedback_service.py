"""
Feedback Service
=================

Service pour la gestion du feedback et l'apprentissage continu.
"""

from uuid import UUID

from src.config.logging_config import LoggerMixin
from src.models.conversation import FlagType
from src.models.document import DocumentCreate, DocumentMetadata, SourceType
from src.repositories.conversation_repository import ConversationRepository
from src.services.vectorization_service import VectorizationService


class FeedbackService(LoggerMixin):
    """
    Service de gestion du feedback et ré-injection.

    Permet de:
    - Ajouter des feedbacks aux conversations
    - Marquer des réponses pour ré-injection
    - Traiter les données flaggées pour enrichir le Vector Store
    """

    def __init__(self) -> None:
        """Initialise le service de feedback."""
        self._conversation_repo = ConversationRepository()
        self._vectorization = VectorizationService()

    def add_feedback(
        self,
        conversation_id: UUID,
        score: int,
        comment: str | None = None,
    ) -> bool:
        """
        Ajoute un feedback à une conversation.

        Args:
            conversation_id: ID de la conversation.
            score: Score de 1 à 5.
            comment: Commentaire optionnel.

        Returns:
            True si le feedback a été ajouté.
        """
        if not 1 <= score <= 5:
            raise ValueError("Score must be between 1 and 5")

        success = self._conversation_repo.add_feedback(
            conversation_id,
            score,
            comment,
        )

        if success:
            self.logger.info(
                "Feedback added",
                conversation_id=str(conversation_id),
                score=score,
            )

        return success

    def flag_for_training(
        self,
        conversation_id: UUID,
        flag_type: FlagType = FlagType.TO_VECTORIZE,
        notes: str | None = None,
    ) -> bool:
        """
        Marque une conversation pour ré-injection.

        Args:
            conversation_id: ID de la conversation.
            flag_type: Type de flag.
            notes: Notes additionnelles.

        Returns:
            True si le flag a été créé.
        """
        success = self._conversation_repo.flag_for_training(
            conversation_id,
            flag_type,
            notes,
        )

        if success:
            self.logger.info(
                "Conversation flagged",
                conversation_id=str(conversation_id),
                flag_type=flag_type.value,
            )

        return success

    def process_training_queue(self, limit: int = 50) -> int:
        """
        Traite les conversations flaggées.

        Transforme les bonnes réponses en documents
        et les injecte dans le Vector Store.

        Args:
            limit: Nombre maximum à traiter.

        Returns:
            Nombre de documents créés.
        """
        pending = self._conversation_repo.get_pending_training(limit)

        if not pending:
            self.logger.info("No pending training data")
            return 0

        created_count = 0

        for item in pending:
            try:
                # Créer un document à partir de la conversation
                content = self._format_training_content(
                    item["user_query"],
                    item["ai_response"],
                )

                doc = DocumentCreate(
                    content=content,
                    source_type=SourceType.CONVERSATION,
                    source_id=f"conversation:{item['conversation_id']}",
                    metadata=DocumentMetadata(
                        title=f"Q&A: {item['user_query'][:50]}...",
                        tags=["training", "qa", item.get("flag_type", "unknown")],
                        extra={
                            "original_conversation": str(item["conversation_id"]),
                            "feedback_score": item.get("feedback_score"),
                        },
                    ),
                )

                # Ingérer le document
                result = self._vectorization.ingest_documents([doc])

                if result.total_created > 0:
                    created_count += 1
                    self.logger.info(
                        "Training data ingested",
                        conversation_id=item["conversation_id"],
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to process training item",
                    conversation_id=item.get("conversation_id"),
                    error=str(e),
                )

        self.logger.info(
            "Training queue processed",
            processed=len(pending),
            created=created_count,
        )

        return created_count

    def _format_training_content(self, query: str, response: str) -> str:
        """Formate le contenu pour l'ingestion."""
        return f"""# Question
{query}

# Réponse
{response}
"""

    def get_analytics(self, days: int = 30) -> dict:
        """
        Récupère les statistiques de feedback.

        Args:
            days: Période en jours.

        Returns:
            Dictionnaire des statistiques.
        """
        analytics = self._conversation_repo.get_analytics(days)

        if analytics:
            return analytics.model_dump()

        return {
            "total_conversations": 0,
            "avg_feedback_score": None,
            "flagged_count": 0,
            "feedback_distribution": {},
            "daily_counts": {},
        }
