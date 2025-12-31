-- ============================================
-- Migration 002: Create Similarity Search Function
-- RAG Agent IA - Supabase Vector Store
-- ============================================

-- ============================================
-- Fonction: match_documents
-- Recherche par similarité cosinus
-- ============================================
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1024),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_source_type VARCHAR(50) DEFAULT NULL,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    source_type VARCHAR(50),
    source_id VARCHAR(500),
    similarity FLOAT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        d.source_type,
        d.source_id,
        1 - (d.embedding <=> query_embedding) AS similarity,
        d.created_at
    FROM documents d
    WHERE 
        -- Filtre par seuil de similarité
        1 - (d.embedding <=> query_embedding) > match_threshold
        -- Filtre optionnel par type de source
        AND (filter_source_type IS NULL OR d.source_type = filter_source_type)
        -- Filtre optionnel par métadonnées (containment)
        AND (filter_metadata IS NULL OR d.metadata @> filter_metadata)
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- Fonction: match_documents_hybrid
-- Recherche hybride (vectorielle + full-text)
-- ============================================
CREATE OR REPLACE FUNCTION match_documents_hybrid(
    query_embedding VECTOR(1024),
    query_text TEXT,
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.7,
    text_weight FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    source_type VARCHAR(50),
    similarity FLOAT,
    text_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        d.source_type,
        1 - (d.embedding <=> query_embedding) AS similarity,
        ts_rank(to_tsvector('french', d.content), plainto_tsquery('french', query_text)) AS text_rank,
        (
            vector_weight * (1 - (d.embedding <=> query_embedding)) +
            text_weight * ts_rank(to_tsvector('french', d.content), plainto_tsquery('french', query_text))
        ) AS combined_score
    FROM documents d
    WHERE 
        1 - (d.embedding <=> query_embedding) > match_threshold
        OR to_tsvector('french', d.content) @@ plainto_tsquery('french', query_text)
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- ============================================
-- Fonction: get_document_stats
-- Statistiques sur les documents
-- ============================================
CREATE OR REPLACE FUNCTION get_document_stats()
RETURNS TABLE (
    total_documents BIGINT,
    documents_by_source JSONB,
    avg_content_length NUMERIC,
    last_updated TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_documents,
        jsonb_object_agg(
            COALESCE(d.source_type, 'unknown'),
            source_counts.count
        ) AS documents_by_source,
        ROUND(AVG(LENGTH(d.content))::NUMERIC, 2) AS avg_content_length,
        MAX(d.updated_at) AS last_updated
    FROM documents d
    LEFT JOIN (
        SELECT source_type, COUNT(*) as count
        FROM documents
        GROUP BY source_type
    ) source_counts ON d.source_type = source_counts.source_type
    GROUP BY source_counts.source_type, source_counts.count
    LIMIT 1;
END;
$$;

-- ============================================
-- Fonction: delete_duplicates
-- Supprime les documents en double basé sur content_hash
-- ============================================
CREATE OR REPLACE FUNCTION delete_duplicates()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH duplicates AS (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY content_hash 
                   ORDER BY created_at ASC
               ) AS rn
        FROM documents
        WHERE content_hash IS NOT NULL
    )
    DELETE FROM documents
    WHERE id IN (
        SELECT id FROM duplicates WHERE rn > 1
    );
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- ============================================
-- Commentaires
-- ============================================
COMMENT ON FUNCTION match_documents IS 'Recherche vectorielle par similarité cosinus avec filtres optionnels';
COMMENT ON FUNCTION match_documents_hybrid IS 'Recherche hybride combinant similarité vectorielle et full-text search';
COMMENT ON FUNCTION get_document_stats IS 'Retourne les statistiques globales sur les documents';
COMMENT ON FUNCTION delete_duplicates IS 'Supprime les documents dupliqués basé sur le hash du contenu';
