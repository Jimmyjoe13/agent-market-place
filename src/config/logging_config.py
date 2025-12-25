"""
Logging Configuration Module
=============================

Configuration structurée du logging avec structlog.
Fournit des logs formatés et contextualisés pour le debugging et monitoring.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.config.settings import get_settings


def setup_logging() -> None:
    """
    Configure le système de logging structuré.
    
    Utilise structlog pour des logs JSON en production
    et des logs colorés en développement.
    
    Example:
        >>> setup_logging()
        >>> logger = get_logger("my_module")
        >>> logger.info("Application started", version="1.0.0")
    """
    settings = get_settings()
    
    # Processeurs communs
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if settings.is_production:
        # Production: JSON logs pour parsing automatique
        shared_processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ])
    else:
        # Développement: Logs colorés et lisibles
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configuration du logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Réduire le bruit des librairies tierces
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Retourne un logger structuré pour un module donné.
    
    Args:
        name: Nom du module (généralement __name__).
        
    Returns:
        structlog.BoundLogger: Logger configuré avec le contexte du module.
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing document", doc_id="123", source="github")
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """
    Mixin pour ajouter un logger à une classe.
    
    Hérite de cette classe pour obtenir automatiquement
    un attribut `logger` configuré.
    
    Example:
        >>> class MyService(LoggerMixin):
        ...     def process(self):
        ...         self.logger.info("Processing started")
    """
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Logger structuré pour la classe."""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """
    Helper pour logger un appel de fonction avec ses paramètres.
    
    Args:
        func_name: Nom de la fonction appelée.
        **kwargs: Paramètres de la fonction à logger.
        
    Example:
        >>> log_function_call("embed_text", text_length=500, model="mistral-embed")
    """
    logger = get_logger("function_call")
    logger.debug(
        "Function called",
        function=func_name,
        parameters={k: v for k, v in kwargs.items() if not k.startswith("_")},
    )
