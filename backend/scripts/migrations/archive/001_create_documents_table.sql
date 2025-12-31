-- ============================================
-- Migration 001: Create Documents Table
-- RAG Agent IA - Supabase Vector Store
-- ============================================

-- Enable the pgvector extension (required for embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Table: documents
-- Stocke les documents vectorisés pour le RAG
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Contenu du document
    content TEXT NOT NULL,
    
    -- Vecteur d'embedding (dimension 1024 pour Mistral Embed)
    embedding VECTOR(1024),
    
    -- Métadonnées flexibles (source, type, auteur, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Source du document (github, pdf, linkedin, manual)
    source_type VARCHAR(50) NOT NULL,
    
    -- Identifiant unique de la source (URL, file path, etc.)
    source_id VARCHAR(500),
    
    -- Hash du contenu pour éviter les doublons
    content_hash VARCHAR(64),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Indexes pour optimiser les recherches
-- ============================================

-- Index sur le type de source
CREATE INDEX IF NOT EXISTS idx_documents_source_type 
ON documents(source_type);

-- Index sur les métadonnées (GIN pour JSONB)
CREATE INDEX IF NOT EXISTS idx_documents_metadata 
ON documents USING gin(metadata);

-- Index sur le hash pour détecter les doublons
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash 
ON documents(content_hash) WHERE content_hash IS NOT NULL;

-- Index HNSW pour recherche vectorielle rapide
-- (IVFFlat est une alternative si HNSW pose problème)
CREATE INDEX IF NOT EXISTS idx_documents_embedding 
ON documents USING hnsw(embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================
-- Trigger pour mise à jour automatique de updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Commentaires sur la table
-- ============================================
COMMENT ON TABLE documents IS 'Table de stockage des documents vectorisés pour le système RAG';
COMMENT ON COLUMN documents.content IS 'Contenu textuel du document';
COMMENT ON COLUMN documents.embedding IS 'Vecteur d''embedding généré par Mistral Embed (1024 dimensions)';
COMMENT ON COLUMN documents.metadata IS 'Métadonnées flexibles au format JSONB';
COMMENT ON COLUMN documents.source_type IS 'Type de source: github, pdf, linkedin, manual';
COMMENT ON COLUMN documents.source_id IS 'Identifiant unique de la source originale';
COMMENT ON COLUMN documents.content_hash IS 'Hash SHA-256 du contenu pour déduplication';
