"""
Tests for Document Processor Service
=====================================
"""

import pytest
from uuid import uuid4

from src.services.document_processor import (
    DocumentProcessor,
    RecursiveTextSplitter,
    ChunkingConfig,
    JobStatus,
    get_document_processor,
)


class TestRecursiveTextSplitter:
    """Tests pour le splitter de texte."""
    
    @pytest.fixture
    def splitter(self):
        """Fixture pour un splitter avec configuration de test."""
        config = ChunkingConfig(
            chunk_size=100,
            chunk_overlap=20,
            min_chunk_size=10,
        )
        return RecursiveTextSplitter(config)
    
    def test_short_text_not_split(self, splitter):
        """Un texte court n'est pas divisé."""
        text = "Ceci est un texte court."
        chunks = splitter.split(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_empty_text_returns_empty(self, splitter):
        """Un texte vide retourne une liste vide."""
        chunks = splitter.split("")
        assert chunks == []
    
    def test_long_text_is_split(self, splitter):
        """Un texte long est divisé en chunks."""
        # Créer un texte de plus de 100 caractères
        text = "Lorem ipsum dolor sit amet. " * 10  # ~280 chars
        chunks = splitter.split(text)
        
        assert len(chunks) > 1
    
    def test_chunks_respect_max_size(self, splitter):
        """Les chunks respectent la taille maximale (avec overlap)."""
        text = "Paragraphe un.\n\nParagraphe deux.\n\nParagraphe trois.\n\n" * 5
        chunks = splitter.split(text)
        
        # Vérifier la taille (avec marge pour l'overlap)
        for chunk in chunks:
            # L'overlap peut dépasser légèrement à cause du préfixe "..."
            assert len(chunk) <= 150  # chunk_size + overlap + marge
    
    def test_uses_separator_hierarchy(self):
        """Le splitter utilise la hiérarchie de séparateurs."""
        config = ChunkingConfig(
            chunk_size=50,
            chunk_overlap=0,
            separator="\n\n",
            fallback_separators=["\n", ". "],
        )
        splitter = RecursiveTextSplitter(config)
        
        text = "Premier paragraphe.\n\nDeuxième paragraphe.\n\nTroisième."
        chunks = splitter.split(text)
        
        # Doit utiliser \n\n comme séparateur principal
        assert len(chunks) >= 2
    
    def test_overlap_between_chunks(self):
        """L'overlap est appliqué entre les chunks."""
        config = ChunkingConfig(
            chunk_size=50,
            chunk_overlap=10,
        )
        splitter = RecursiveTextSplitter(config)
        
        text = "A" * 40 + "\n\n" + "B" * 40 + "\n\n" + "C" * 40
        chunks = splitter.split(text)
        
        # Les chunks après le premier doivent contenir le préfixe d'overlap
        if len(chunks) > 1:
            assert " ... " in chunks[1]  # Marqueur d'overlap


class TestDocumentProcessor:
    """Tests pour le Document Processor."""
    
    @pytest.fixture
    def processor(self):
        """Fixture pour un processor de test."""
        return DocumentProcessor(batch_size=2, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_create_job(self, processor):
        """create_job crée un job avec le bon statut."""
        job_id = await processor.create_job(
            api_key_id=str(uuid4()),
            user_id=str(uuid4()),
            content="Test content for processing.",
            source_filename="test.txt",
            source_type="text",
        )
        
        assert job_id is not None
        
        status = await processor.get_job_status(job_id)
        assert status is not None
        assert status["status"] == JobStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_get_job_status_returns_none_for_unknown(self, processor):
        """get_job_status retourne None pour un job inconnu."""
        status = await processor.get_job_status(uuid4())
        assert status is None
    
    @pytest.mark.asyncio
    async def test_job_includes_source_info(self, processor):
        """Le job contient les infos sur la source."""
        job_id = await processor.create_job(
            api_key_id=str(uuid4()),
            user_id=str(uuid4()),
            content="Test content",
            source_filename="document.pdf",
            source_type="pdf",
        )
        
        status = await processor.get_job_status(job_id)
        assert status["source_filename"] == "document.pdf"


class TestDocumentProcessorSingleton:
    """Tests pour le singleton du processor."""
    
    def test_get_document_processor_returns_same_instance(self):
        """get_document_processor retourne toujours la même instance."""
        proc1 = get_document_processor()
        proc2 = get_document_processor()
        
        assert proc1 is proc2


class TestChunkingConfig:
    """Tests pour la configuration de chunking."""
    
    def test_default_config(self):
        """La config par défaut est valide."""
        config = ChunkingConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.min_chunk_size == 100
        assert config.separator == "\n\n"
    
    def test_custom_config(self):
        """Une config personnalisée est acceptée."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=50,
            separator="---",
        )
        
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.separator == "---"
