"""
PDF Provider
=============

Provider pour l'extraction de texte depuis des fichiers PDF.
Utilisé pour parser les CVs et documents PDF.
"""

from collections.abc import Iterator
from pathlib import Path

import fitz  # PyMuPDF

from src.models.document import SourceType
from src.providers.base import BaseProvider, ExtractedContent


class PDFProvider(BaseProvider):
    """
    Provider pour l'extraction de texte depuis des PDFs.

    Utilise PyMuPDF (fitz) pour un parsing rapide et précis.
    Supporte l'extraction par page ou document complet.

    Attributes:
        chunk_by_page: Si True, crée un document par page.
        min_content_length: Longueur minimum pour garder le contenu.
    """

    def __init__(
        self,
        chunk_by_page: bool = False,
        min_content_length: int = 50,
    ) -> None:
        """
        Initialise le provider PDF.

        Args:
            chunk_by_page: Créer un document par page.
            min_content_length: Longueur minimum du contenu.
        """
        self.chunk_by_page = chunk_by_page
        self.min_content_length = min_content_length

    @property
    def source_type(self) -> SourceType:
        """Type de source: PDF."""
        return SourceType.PDF

    def extract(self, source: str) -> Iterator[ExtractedContent]:
        """
        Extrait le texte d'un fichier PDF.

        Args:
            source: Chemin vers le fichier PDF.

        Yields:
            ExtractedContent pour chaque page ou document.
        """
        path = Path(source)

        if not path.exists():
            self.logger.error("PDF file not found", path=source)
            raise FileNotFoundError(f"PDF not found: {source}")

        if path.suffix.lower() != ".pdf":
            self.logger.error("Not a PDF file", path=source)
            raise ValueError(f"Not a PDF file: {source}")

        try:
            doc = fitz.open(str(path))
            self.logger.info(
                "Processing PDF",
                file=path.name,
                pages=doc.page_count,
            )

            if self.chunk_by_page:
                yield from self._extract_by_page(doc, path)
            else:
                yield from self._extract_full(doc, path)

            doc.close()

        except Exception as e:
            self.logger.error("PDF extraction failed", error=str(e))
            raise

    def _extract_full(
        self,
        doc: fitz.Document,
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait le PDF comme un seul document."""
        full_text = []

        for page in doc:
            text = page.get_text("text")
            if text.strip():
                full_text.append(text)

        content = "\n\n".join(full_text)

        if len(content) >= self.min_content_length:
            metadata = self._extract_metadata(doc, path)

            yield ExtractedContent(
                content=content,
                source_id=f"pdf:{path.name}",
                metadata=metadata,
            )

    def _extract_by_page(
        self,
        doc: fitz.Document,
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait chaque page comme un document séparé."""
        base_metadata = self._extract_metadata(doc, path)

        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")

            if len(text.strip()) >= self.min_content_length:
                metadata = {
                    **base_metadata,
                    "extra": {
                        **base_metadata.get("extra", {}),
                        "page_number": page_num,
                        "total_pages": doc.page_count,
                    },
                }

                yield ExtractedContent(
                    content=text,
                    source_id=f"pdf:{path.name}:page_{page_num}",
                    metadata=metadata,
                )

    def _extract_metadata(
        self,
        doc: fitz.Document,
        path: Path,
    ) -> dict:
        """Extrait les métadonnées du PDF."""
        pdf_metadata = doc.metadata or {}

        # Détecter si c'est un CV
        is_cv = self._detect_cv(doc)

        return {
            "title": pdf_metadata.get("title") or path.stem,
            "author": pdf_metadata.get("author"),
            "file_path": str(path.absolute()),
            "language": "fr",
            "tags": ["cv", "resume"] if is_cv else ["document", "pdf"],
            "extra": {
                "pages": doc.page_count,
                "creator": pdf_metadata.get("creator"),
                "producer": pdf_metadata.get("producer"),
                "creation_date": pdf_metadata.get("creationDate"),
                "is_cv": is_cv,
            },
        }

    def _detect_cv(self, doc: fitz.Document) -> bool:
        """
        Détecte si le PDF est un CV.

        Recherche des mots-clés typiques des CVs.
        """
        cv_keywords = {
            "curriculum vitae",
            "cv",
            "resume",
            "résumé",
            "expérience professionnelle",
            "formation",
            "compétences",
            "skills",
            "education",
            "work experience",
            "professional experience",
        }

        # Analyser les premières pages
        sample_text = ""
        for i, page in enumerate(doc):
            if i >= 2:  # Limiter à 2 pages
                break
            sample_text += page.get_text("text").lower()

        # Compter les mots-clés trouvés
        matches = sum(1 for kw in cv_keywords if kw in sample_text)
        return matches >= 2

    def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "uploaded.pdf",
    ) -> Iterator[ExtractedContent]:
        """
        Extrait depuis des bytes (pour uploads).

        Args:
            pdf_bytes: Contenu binaire du PDF.
            filename: Nom du fichier pour les métadonnées.

        Yields:
            ExtractedContent pour chaque document.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            full_text = []
            for page in doc:
                text = page.get_text("text")
                if text.strip():
                    full_text.append(text)

            content = "\n\n".join(full_text)

            if len(content) >= self.min_content_length:
                yield ExtractedContent(
                    content=content,
                    source_id=f"pdf:upload:{filename}",
                    metadata={
                        "title": filename,
                        "tags": ["uploaded", "pdf"],
                        "extra": {"pages": doc.page_count},
                    },
                )

            doc.close()

        except Exception as e:
            self.logger.error("PDF bytes extraction failed", error=str(e))
            raise
