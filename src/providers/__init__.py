"""Data Providers module - Data ingestion from external sources."""

from src.providers.base import BaseProvider, ExtractedContent
from src.providers.github_provider import GithubProvider
from src.providers.pdf_provider import PDFProvider
from src.providers.linkedin_provider import LinkedInProvider

__all__ = [
    "BaseProvider",
    "ExtractedContent",
    "GithubProvider", 
    "PDFProvider",
    "LinkedInProvider",
]
