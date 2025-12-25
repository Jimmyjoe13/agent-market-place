#!/usr/bin/env python3
"""
Script d'Ingestion de Données
==============================

Script CLI pour ingérer des données depuis différentes sources
dans le Vector Store Supabase.

Usage:
    python -m scripts.ingest --github owner/repo
    python -m scripts.ingest --pdf /path/to/cv.pdf
    python -m scripts.ingest --linkedin /path/to/export.json
"""

import argparse
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging_config import setup_logging, get_logger
from src.providers.github_provider import GithubProvider
from src.providers.pdf_provider import PDFProvider
from src.providers.linkedin_provider import LinkedInProvider
from src.services.vectorization_service import VectorizationService


def main() -> None:
    """Point d'entrée principal du script."""
    setup_logging()
    logger = get_logger("ingest")
    
    parser = argparse.ArgumentParser(
        description="Ingestion de données vers le Vector Store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/ingest.py --github langchain-ai/langchain
  python scripts/ingest.py --pdf ./cv/mon_cv.pdf
  python scripts/ingest.py --linkedin ./exports/linkedin_export.json
  python scripts/ingest.py --github user/repo1 user/repo2 --skip-duplicates
        """,
    )
    
    parser.add_argument(
        "--github",
        nargs="+",
        metavar="REPO",
        help="Repositories GitHub à ingérer (format: owner/repo)",
    )
    parser.add_argument(
        "--pdf",
        nargs="+",
        metavar="FILE",
        help="Fichiers PDF à ingérer",
    )
    parser.add_argument(
        "--linkedin",
        nargs="+",
        metavar="FILE",
        help="Exports LinkedIn à ingérer (JSON ou PDF)",
    )
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        default=True,
        help="Ignorer les documents déjà présents (défaut: True)",
    )
    parser.add_argument(
        "--chunk-pages",
        action="store_true",
        help="Pour les PDFs, créer un document par page",
    )
    
    args = parser.parse_args()
    
    # Vérifier qu'au moins une source est spécifiée
    if not any([args.github, args.pdf, args.linkedin]):
        parser.print_help()
        sys.exit(1)
    
    vectorization = VectorizationService()
    total_stats = {
        "processed": 0,
        "created": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    # Ingestion GitHub
    if args.github:
        logger.info("Processing GitHub repositories", count=len(args.github))
        provider = GithubProvider()
        stats = vectorization.ingest_from_provider(
            provider,
            args.github,
            skip_duplicates=args.skip_duplicates,
        )
        _update_stats(total_stats, stats)
    
    # Ingestion PDF
    if args.pdf:
        logger.info("Processing PDF files", count=len(args.pdf))
        provider = PDFProvider(chunk_by_page=args.chunk_pages)
        stats = vectorization.ingest_from_provider(
            provider,
            args.pdf,
            skip_duplicates=args.skip_duplicates,
        )
        _update_stats(total_stats, stats)
    
    # Ingestion LinkedIn
    if args.linkedin:
        logger.info("Processing LinkedIn exports", count=len(args.linkedin))
        provider = LinkedInProvider()
        stats = vectorization.ingest_from_provider(
            provider,
            args.linkedin,
            skip_duplicates=args.skip_duplicates,
        )
        _update_stats(total_stats, stats)
    
    # Résumé final
    logger.info(
        "Ingestion completed",
        total_processed=total_stats["processed"],
        total_created=total_stats["created"],
        total_skipped=total_stats["skipped"],
        total_errors=total_stats["errors"],
    )
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DE L'INGESTION")
    print("=" * 50)
    print(f"✅ Documents traités : {total_stats['processed']}")
    print(f"📝 Documents créés   : {total_stats['created']}")
    print(f"⏭️  Documents ignorés : {total_stats['skipped']}")
    print(f"❌ Erreurs           : {total_stats['errors']}")
    print("=" * 50)


def _update_stats(total: dict, stats) -> None:
    """Met à jour les statistiques totales."""
    total["processed"] += stats.total_processed
    total["created"] += stats.total_created
    total["skipped"] += stats.total_skipped
    total["errors"] += stats.total_errors


if __name__ == "__main__":
    main()
