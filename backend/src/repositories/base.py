"""
Base Repository
================

Classe abstraite définissant l'interface commune pour tous les repositories.
Implémente le pattern Repository pour l'accès aux données Supabase.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from supabase import Client, create_client

from src.config.logging_config import LoggerMixin
from src.config.settings import get_settings

T = TypeVar("T")


class BaseRepository(ABC, LoggerMixin, Generic[T]):
    """
    Repository de base pour l'accès à Supabase.

    Fournit les méthodes CRUD communes et la connexion à la base.

    Attributes:
        table_name: Nom de la table Supabase.
        client: Client Supabase initialisé.
    """

    def __init__(self, table_name: str) -> None:
        """
        Initialise le repository.

        Args:
            table_name: Nom de la table dans Supabase.
        """
        self.table_name = table_name
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Client Supabase avec lazy initialization."""
        if self._client is None:
            settings = get_settings()
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
            )
        return self._client

    @property
    def table(self) -> Any:
        """Accès direct à la table."""
        return self.client.table(self.table_name)

    @abstractmethod
    def get_by_id(self, id: str) -> T | None:
        """Récupère un enregistrement par son ID."""
        pass

    @abstractmethod
    def create(self, data: dict[str, Any]) -> T:
        """Crée un nouvel enregistrement."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Supprime un enregistrement."""
        pass
