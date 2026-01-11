"""
Agent Memory Repository
========================

Repository pour la gestion de la mémoire conversationnelle des agents.
Chaque agent maintient une fenêtre de N messages (configurable, rotation FIFO).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.repositories.base import BaseRepository


@dataclass
class MemoryMessage:
    """Message en mémoire."""
    
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sérialisation."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }


class AgentMemoryRepository(BaseRepository):
    """
    Repository pour la mémoire conversationnelle des agents.
    
    Chaque agent peut configurer sa propre limite de mémoire (0-100 messages).
    La rotation FIFO est automatique via les fonctions SQL.
    """

    def __init__(self) -> None:
        """Initialise le repository."""
        super().__init__("agent_memory")

    # ===== Implémentation des méthodes abstraites BaseRepository =====

    def get_by_id(self, id: str) -> MemoryMessage | None:
        """
        Récupère un message mémoire par son ID.
        
        Args:
            id: UUID du message.
            
        Returns:
            MemoryMessage ou None si non trouvé.
        """
        try:
            response = self.table.select("*").eq("id", id).execute()
            if response.data and len(response.data) > 0:
                msg = response.data[0]
                created_at = msg.get("created_at")
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except ValueError:
                        created_at = datetime.now()
                return MemoryMessage(
                    id=msg["id"],
                    role=msg["role"],
                    content=msg["content"],
                    created_at=created_at,
                )
            return None
        except Exception as e:
            self.logger.error("Failed to get memory message by id", error=str(e))
            return None

    def create(self, data: dict) -> MemoryMessage:
        """
        Crée un message mémoire directement (sans rotation FIFO).
        
        Note: Préférer add_message() qui gère la rotation automatique.
        
        Args:
            data: Dict avec agent_id, role, content, metadata (optionnel).
            
        Returns:
            MemoryMessage créé.
        """
        try:
            response = self.table.insert(data).execute()
            msg = response.data[0]
            created_at = msg.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    created_at = datetime.now()
            return MemoryMessage(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                created_at=created_at,
            )
        except Exception as e:
            self.logger.error("Failed to create memory message", error=str(e))
            raise

    def delete(self, id: str) -> bool:
        """
        Supprime un message mémoire par son ID.
        
        Args:
            id: UUID du message.
            
        Returns:
            True si succès.
        """
        try:
            self.table.delete().eq("id", id).execute()
            return True
        except Exception as e:
            self.logger.error("Failed to delete memory message", error=str(e))
            return False

    def add_message(
        self,
        agent_id: str,
        role: Literal["user", "assistant"],
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Ajoute un message à la mémoire de l'agent.
        
        Utilise la rotation FIFO via la fonction SQL.
        Respecte la limite configurable de l'agent.
        
        Args:
            agent_id: UUID de l'agent.
            role: 'user' ou 'assistant'.
            content: Contenu du message.
            metadata: Métadonnées optionnelles.
        """
        try:
            self.client.rpc(
                "add_agent_memory",
                {
                    "p_agent_id": agent_id,
                    "p_role": role,
                    "p_content": content,
                    "p_metadata": metadata or {},
                }
            ).execute()
            self.logger.debug(
                "Memory message added",
                agent_id=agent_id,
                role=role,
                content_length=len(content),
            )
        except Exception as e:
            self.logger.error("Failed to add memory message", error=str(e))

    def add_exchange(
        self,
        agent_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        Ajoute un échange complet (user + assistant) à la mémoire.
        
        Raccourci pratique pour ajouter les deux messages d'un coup.
        
        Args:
            agent_id: UUID de l'agent.
            user_message: Message de l'utilisateur.
            assistant_message: Réponse de l'assistant.
        """
        self.add_message(agent_id, "user", user_message)
        self.add_message(agent_id, "assistant", assistant_message)

    def get_messages(
        self,
        agent_id: str,
        limit: int | None = None,
    ) -> list[MemoryMessage]:
        """
        Récupère les messages de la mémoire d'un agent.
        
        Args:
            agent_id: UUID de l'agent.
            limit: Nombre max de messages (None = utilise la limite de l'agent).
            
        Returns:
            Liste des messages ordonnés chronologiquement.
        """
        try:
            response = self.client.rpc(
                "get_agent_memory",
                {
                    "p_agent_id": agent_id,
                    "p_limit": limit,
                }
            ).execute()
            
            messages = []
            for msg in response.data or []:
                # Supporter les deux formats (avant/après migration 014)
                # Après migration: memory_id, memory_role, memory_content, memory_created_at
                # Avant migration: id, role, content, created_at
                msg_id = msg.get("memory_id") or msg.get("id")
                msg_role = msg.get("memory_role") or msg.get("role")
                msg_content = msg.get("memory_content") or msg.get("content")
                created_at = msg.get("memory_created_at") or msg.get("created_at")
                
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except ValueError:
                        created_at = datetime.now()
                
                messages.append(MemoryMessage(
                    id=msg_id,
                    role=msg_role,
                    content=msg_content,
                    created_at=created_at,
                ))
            
            return messages
        except Exception as e:
            self.logger.error("Failed to get memory", error=str(e))
            return []

    def clear_memory(self, agent_id: str) -> bool:
        """
        Efface toute la mémoire d'un agent.
        
        Args:
            agent_id: UUID de l'agent.
            
        Returns:
            True si succès.
        """
        try:
            self.client.rpc(
                "clear_agent_memory",
                {"p_agent_id": agent_id}
            ).execute()
            self.logger.info("Agent memory cleared", agent_id=agent_id)
            return True
        except Exception as e:
            self.logger.error("Failed to clear memory", error=str(e))
            return False

    def get_as_llm_messages(
        self,
        agent_id: str,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """
        Récupère les messages formatés pour injection LLM.
        
        Args:
            agent_id: UUID de l'agent.
            limit: Nombre max de messages.
            
        Returns:
            Liste de dicts {"role": ..., "content": ...}
        """
        messages = self.get_messages(agent_id, limit)
        # Filtrer les messages valides uniquement (role et content non-None)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role and msg.content
        ]

    def get_memory_stats(self, agent_id: str) -> dict:
        """
        Récupère les statistiques de mémoire d'un agent.
        
        Args:
            agent_id: UUID de l'agent.
            
        Returns:
            Dict avec count, oldest_message, newest_message.
        """
        messages = self.get_messages(agent_id)
        
        if not messages:
            return {
                "count": 0,
                "oldest_message": None,
                "newest_message": None,
            }
        
        return {
            "count": len(messages),
            "oldest_message": messages[0].created_at.isoformat() if messages else None,
            "newest_message": messages[-1].created_at.isoformat() if messages else None,
        }
