"""
Background Worker
==================

Worker pour traitement asynchrone des jobs lourds.

Usage:
    python -m src.workers.worker

En production, utiliser un process manager comme supervisord ou systemd.
"""

import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from redis import Redis
from rq import Queue, Worker

from src.config.logging_config import get_logger, setup_logging
from src.config.settings import get_settings


def run_worker() -> None:
    """
    Lance le worker RQ pour traiter les jobs en arrière-plan.

    Le worker écoute la queue 'ingestion' et exécute les tâches
    d'ingestion de documents (GitHub, PDF, etc.).
    """
    setup_logging()
    logger = get_logger("worker")
    settings = get_settings()

    if not settings.redis_url:
        logger.error("REDIS_URL not configured, worker cannot start")
        sys.exit(1)

    logger.info("Starting RQ worker", redis_url=settings.redis_url.split("@")[-1])

    try:
        redis_conn = Redis.from_url(settings.redis_url)

        # Tester la connexion
        redis_conn.ping()
        logger.info("Redis connection successful")

        # Créer les queues à écouter
        queues = [
            Queue("ingestion", connection=redis_conn),
            Queue("default", connection=redis_conn),
        ]

        # Créer et lancer le worker
        worker = Worker(queues, connection=redis_conn)

        logger.info("Worker started, listening for jobs...")
        worker.work(with_scheduler=True)

    except Exception as e:
        logger.error("Worker failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    run_worker()
