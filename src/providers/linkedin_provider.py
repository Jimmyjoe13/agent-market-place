"""
LinkedIn Provider
==================

Provider pour l'extraction de données LinkedIn.
L'API LinkedIn étant restreinte, ce provider utilise des exports JSON/PDF.
"""

import json
from pathlib import Path
from typing import Any, Iterator

from src.models.document import SourceType
from src.providers.base import BaseProvider, ExtractedContent
from src.providers.pdf_provider import PDFProvider


class LinkedInProvider(BaseProvider):
    """
    Provider pour les données LinkedIn.
    
    Supporte deux formats d'import:
    - Export JSON de LinkedIn (via GDPR request)
    - Export PDF du profil
    
    Pour obtenir vos données LinkedIn:
    1. Allez dans Paramètres > Confidentialité > Obtenir une copie de vos données
    2. Sélectionnez les données souhaitées
    3. Téléchargez l'archive ZIP
    """
    
    def __init__(self) -> None:
        """Initialise le provider LinkedIn."""
        self._pdf_provider = PDFProvider(chunk_by_page=False)
    
    @property
    def source_type(self) -> SourceType:
        """Type de source: LinkedIn."""
        return SourceType.LINKEDIN
    
    def extract(self, source: str) -> Iterator[ExtractedContent]:
        """
        Extrait les données LinkedIn depuis un fichier.
        
        Args:
            source: Chemin vers le fichier (JSON ou PDF).
            
        Yields:
            ExtractedContent pour chaque section extraite.
        """
        path = Path(source)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        if path.suffix.lower() == ".json":
            yield from self._extract_json(path)
        elif path.suffix.lower() == ".pdf":
            yield from self._extract_pdf(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
    
    def _extract_json(self, path: Path) -> Iterator[ExtractedContent]:
        """Extrait depuis un export JSON LinkedIn."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Profile de base
            if "Profile" in data:
                yield from self._extract_profile(data["Profile"], path)
            
            # Expériences
            if "Positions" in data:
                yield from self._extract_positions(data["Positions"], path)
            
            # Formations
            if "Education" in data:
                yield from self._extract_education(data["Education"], path)
            
            # Compétences
            if "Skills" in data:
                yield from self._extract_skills(data["Skills"], path)
            
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON", error=str(e))
            raise
    
    def _extract_profile(
        self,
        profile: dict[str, Any],
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait les informations de profil."""
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}"
        headline = profile.get("headline", "")
        summary = profile.get("summary", "")
        
        content = f"""# Profil LinkedIn - {name}

## Titre
{headline}

## Résumé
{summary}
"""
        
        if content.strip():
            yield ExtractedContent(
                content=content,
                source_id=f"linkedin:{path.stem}:profile",
                metadata={
                    "title": f"LinkedIn - {name}",
                    "author": name,
                    "tags": ["linkedin", "profile"],
                    "extra": {
                        "section": "profile",
                        "headline": headline,
                    },
                },
            )
    
    def _extract_positions(
        self,
        positions: list[dict[str, Any]],
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait les expériences professionnelles."""
        if not positions:
            return
        
        content_parts = ["# Expériences Professionnelles\n"]
        
        for pos in positions:
            title = pos.get("title", "")
            company = pos.get("companyName", "")
            description = pos.get("description", "")
            start = pos.get("startDate", "")
            end = pos.get("endDate", "Présent")
            
            content_parts.append(f"""
## {title} @ {company}
**Période**: {start} - {end}

{description}
""")
        
        yield ExtractedContent(
            content="\n".join(content_parts),
            source_id=f"linkedin:{path.stem}:positions",
            metadata={
                "title": "LinkedIn - Expériences",
                "tags": ["linkedin", "experience", "work"],
                "extra": {
                    "section": "positions",
                    "count": len(positions),
                },
            },
        )
    
    def _extract_education(
        self,
        education: list[dict[str, Any]],
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait les formations."""
        if not education:
            return
        
        content_parts = ["# Formation\n"]
        
        for edu in education:
            school = edu.get("schoolName", "")
            degree = edu.get("degree", "")
            field = edu.get("fieldOfStudy", "")
            
            content_parts.append(f"""
## {school}
**Diplôme**: {degree}
**Domaine**: {field}
""")
        
        yield ExtractedContent(
            content="\n".join(content_parts),
            source_id=f"linkedin:{path.stem}:education",
            metadata={
                "title": "LinkedIn - Formation",
                "tags": ["linkedin", "education"],
                "extra": {
                    "section": "education",
                    "count": len(education),
                },
            },
        )
    
    def _extract_skills(
        self,
        skills: list[dict[str, Any]],
        path: Path,
    ) -> Iterator[ExtractedContent]:
        """Extrait les compétences."""
        if not skills:
            return
        
        skill_list = [s.get("name", "") for s in skills if s.get("name")]
        
        content = f"""# Compétences LinkedIn

{', '.join(skill_list)}
"""
        
        yield ExtractedContent(
            content=content,
            source_id=f"linkedin:{path.stem}:skills",
            metadata={
                "title": "LinkedIn - Compétences",
                "tags": ["linkedin", "skills", "competences"],
                "extra": {
                    "section": "skills",
                    "skills": skill_list,
                },
            },
        )
    
    def _extract_pdf(self, path: Path) -> Iterator[ExtractedContent]:
        """Extrait depuis un PDF de profil LinkedIn."""
        for extracted in self._pdf_provider.extract(str(path)):
            # Modifier les métadonnées pour LinkedIn
            extracted.source_id = f"linkedin:pdf:{path.stem}"
            extracted.metadata["tags"] = ["linkedin", "profile", "pdf"]
            yield extracted
