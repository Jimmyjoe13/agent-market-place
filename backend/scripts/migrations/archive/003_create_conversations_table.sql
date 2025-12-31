-- ============================================
-- Migration 003: Create Conversations & Feedback Tables
-- RAG Agent IA - Feedback Loop System
-- ============================================

-- ============================================
-- Table: conversations
-- Historique des conversations pour enrichissement
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session de conversation
    session_id VARCHAR(100) NOT NULL,
    
    -- Requête utilisateur
    user_query TEXT NOT NULL,
    
    -- Réponse générée par l'IA
    ai_response TEXT NOT NULL,
    
    -- Contextes utilisés pour la génération
    context_sources JSONB DEFAULT '[]'::jsonb,
    
    -- Métadonnées (modèle utilisé, tokens, temps de réponse, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Feedback utilisateur (null = pas de feedback)
    feedback_score INTEGER CHECK (feedback_score IS NULL OR (feedback_score >= 1 AND feedback_score <= 5)),
    feedback_comment TEXT,
    
    -- Flag pour ré-injection dans le Vector Store
    flagged_for_training BOOLEAN DEFAULT FALSE,
    training_processed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Table: feedback_flags
-- Gestion des flags de qualité pour amélioration
-- ============================================
CREATE TABLE IF NOT EXISTS feedback_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Référence à la conversation
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Type de flag
    flag_type VARCHAR(50) NOT NULL CHECK (
        flag_type IN ('excellent', 'needs_improvement', 'incorrect', 'missing_context', 'to_vectorize')
    ),
    
    -- Notes additionnelles
    notes TEXT,
    
    -- Qui a flaggé (pour multi-utilisateurs futur)
    flagged_by VARCHAR(100) DEFAULT 'system',
    
    -- Statut du traitement
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'completed', 'dismissed')
    ),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- ============================================
-- Indexes
-- ============================================

-- Index sur session_id pour regrouper les conversations
CREATE INDEX IF NOT EXISTS idx_conversations_session 
ON conversations(session_id);

-- Index sur les conversations flaggées pour training
CREATE INDEX IF NOT EXISTS idx_conversations_flagged 
ON conversations(flagged_for_training) 
WHERE flagged_for_training = TRUE;

-- Index sur le feedback score
CREATE INDEX IF NOT EXISTS idx_conversations_feedback 
ON conversations(feedback_score) 
WHERE feedback_score IS NOT NULL;

-- Index sur les flags en attente
CREATE INDEX IF NOT EXISTS idx_feedback_flags_pending 
ON feedback_flags(status) 
WHERE status = 'pending';

-- Index sur la date de création
CREATE INDEX IF NOT EXISTS idx_conversations_created 
ON conversations(created_at DESC);

-- ============================================
-- Fonction: log_conversation
-- Enregistre une interaction complète
-- ============================================
CREATE OR REPLACE FUNCTION log_conversation(
    p_session_id VARCHAR(100),
    p_user_query TEXT,
    p_ai_response TEXT,
    p_context_sources JSONB DEFAULT '[]'::jsonb,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    new_id UUID;
BEGIN
    INSERT INTO conversations (
        session_id,
        user_query,
        ai_response,
        context_sources,
        metadata
    ) VALUES (
        p_session_id,
        p_user_query,
        p_ai_response,
        p_context_sources,
        p_metadata
    )
    RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$;

-- ============================================
-- Fonction: flag_for_training
-- Marque une conversation pour ré-injection
-- ============================================
CREATE OR REPLACE FUNCTION flag_for_training(
    p_conversation_id UUID,
    p_flag_type VARCHAR(50) DEFAULT 'to_vectorize',
    p_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    -- Mettre à jour la conversation
    UPDATE conversations
    SET flagged_for_training = TRUE
    WHERE id = p_conversation_id;
    
    -- Créer le flag
    INSERT INTO feedback_flags (
        conversation_id,
        flag_type,
        notes
    ) VALUES (
        p_conversation_id,
        p_flag_type,
        p_notes
    );
    
    RETURN TRUE;
END;
$$;

-- ============================================
-- Fonction: get_pending_training_data
-- Récupère les données à vectoriser
-- ============================================
CREATE OR REPLACE FUNCTION get_pending_training_data(
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    conversation_id UUID,
    user_query TEXT,
    ai_response TEXT,
    feedback_score INTEGER,
    flag_type VARCHAR(50),
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS conversation_id,
        c.user_query,
        c.ai_response,
        c.feedback_score,
        f.flag_type,
        c.created_at
    FROM conversations c
    JOIN feedback_flags f ON c.id = f.conversation_id
    WHERE 
        c.flagged_for_training = TRUE
        AND c.training_processed_at IS NULL
        AND f.status = 'pending'
    ORDER BY c.created_at ASC
    LIMIT p_limit;
END;
$$;

-- ============================================
-- Fonction: get_conversation_analytics
-- Statistiques sur les conversations
-- ============================================
CREATE OR REPLACE FUNCTION get_conversation_analytics(
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_conversations BIGINT,
    avg_feedback_score NUMERIC,
    flagged_count BIGINT,
    feedback_distribution JSONB,
    daily_counts JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH date_range AS (
        SELECT NOW() - (p_days || ' days')::INTERVAL AS start_date
    ),
    daily AS (
        SELECT 
            DATE(created_at) AS day,
            COUNT(*) AS count
        FROM conversations, date_range
        WHERE created_at >= date_range.start_date
        GROUP BY DATE(created_at)
    ),
    feedback_dist AS (
        SELECT 
            feedback_score,
            COUNT(*) AS count
        FROM conversations
        WHERE feedback_score IS NOT NULL
        GROUP BY feedback_score
    )
    SELECT
        (SELECT COUNT(*) FROM conversations, date_range WHERE created_at >= date_range.start_date)::BIGINT,
        (SELECT ROUND(AVG(feedback_score)::NUMERIC, 2) FROM conversations WHERE feedback_score IS NOT NULL),
        (SELECT COUNT(*) FROM conversations WHERE flagged_for_training = TRUE)::BIGINT,
        (SELECT jsonb_object_agg(feedback_score::TEXT, count) FROM feedback_dist),
        (SELECT jsonb_object_agg(day::TEXT, count) FROM daily);
END;
$$;

-- ============================================
-- Commentaires
-- ============================================
COMMENT ON TABLE conversations IS 'Historique des conversations pour le feedback loop et enrichissement du RAG';
COMMENT ON TABLE feedback_flags IS 'Flags de qualité pour amélioration continue du système';
COMMENT ON FUNCTION log_conversation IS 'Enregistre une nouvelle interaction utilisateur/IA';
COMMENT ON FUNCTION flag_for_training IS 'Marque une conversation pour ré-injection dans le Vector Store';
