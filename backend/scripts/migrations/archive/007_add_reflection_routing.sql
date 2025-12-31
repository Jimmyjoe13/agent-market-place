-- ============================================
-- Migration 007: Add Reflection & Routing Data
-- RAG Agent IA - Mode Réflexion & Orchestration
-- ============================================
-- 
-- Cette migration ajoute le support pour :
-- 1. Le mode réflexion (Chain-of-Thought)
-- 2. Les informations de routage intelligent
-- 3. Les métriques de performance de l'orchestrateur
--
-- Prérequis : Migration 003 (conversations table)
-- ============================================

-- ============================================
-- Ajout des colonnes pour les données de réflexion
-- ============================================

-- Processus de pensée (Chain-of-Thought)
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS thought_process TEXT;

COMMENT ON COLUMN conversations.thought_process IS 
'Processus de réflexion interne de l''IA (Chain-of-Thought) si le mode réflexion est activé';

-- Informations de routage intelligent
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS routing_info JSONB DEFAULT NULL;

COMMENT ON COLUMN conversations.routing_info IS 
'Informations de routage intelligent (intent, confidence, latency_ms, etc.)';

-- Mode réflexion utilisé
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS reflection_enabled BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN conversations.reflection_enabled IS 
'Indique si le mode réflexion était activé pour cette conversation';

-- Provider LLM utilisé
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50) DEFAULT 'mistral';

COMMENT ON COLUMN conversations.llm_provider IS 
'Provider LLM utilisé pour la génération (mistral, openai, gemini, etc.)';

-- ============================================
-- Table: routing_analytics
-- Statistiques sur le routage intelligent
-- ============================================
CREATE TABLE IF NOT EXISTS routing_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Période d'agrégation
    date DATE NOT NULL,
    
    -- Compteurs par intent
    intent_general_count INTEGER DEFAULT 0,
    intent_documents_count INTEGER DEFAULT 0,
    intent_web_search_count INTEGER DEFAULT 0,
    intent_hybrid_count INTEGER DEFAULT 0,
    intent_greeting_count INTEGER DEFAULT 0,
    
    -- Métriques de performance
    avg_routing_latency_ms INTEGER DEFAULT 0,
    avg_total_latency_ms INTEGER DEFAULT 0,
    
    -- Taux de cache hit
    cache_hit_count INTEGER DEFAULT 0,
    cache_miss_count INTEGER DEFAULT 0,
    
    -- Métriques de réflexion
    reflection_usage_count INTEGER DEFAULT 0,
    avg_reflection_tokens INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT routing_analytics_date_unique UNIQUE (date)
);

-- Index sur la date pour les requêtes temporelles
CREATE INDEX IF NOT EXISTS idx_routing_analytics_date 
ON routing_analytics(date DESC);

COMMENT ON TABLE routing_analytics IS 
'Statistiques agrégées quotidiennes sur le routage intelligent et le mode réflexion';

-- ============================================
-- Ajout d'un index sur les conversations avec réflexion
-- ============================================
CREATE INDEX IF NOT EXISTS idx_conversations_reflection 
ON conversations(reflection_enabled) 
WHERE reflection_enabled = TRUE;

-- Index sur le provider LLM
CREATE INDEX IF NOT EXISTS idx_conversations_provider 
ON conversations(llm_provider);

-- Index GIN sur routing_info pour les requêtes JSONB
CREATE INDEX IF NOT EXISTS idx_conversations_routing_info 
ON conversations USING GIN (routing_info jsonb_path_ops)
WHERE routing_info IS NOT NULL;

-- ============================================
-- Fonction: log_conversation_v2
-- Version enrichie avec support réflexion
-- ============================================
CREATE OR REPLACE FUNCTION log_conversation_v2(
    p_session_id VARCHAR(100),
    p_user_query TEXT,
    p_ai_response TEXT,
    p_context_sources JSONB DEFAULT '[]'::jsonb,
    p_metadata JSONB DEFAULT '{}'::jsonb,
    p_thought_process TEXT DEFAULT NULL,
    p_routing_info JSONB DEFAULT NULL,
    p_reflection_enabled BOOLEAN DEFAULT FALSE,
    p_llm_provider VARCHAR(50) DEFAULT 'mistral',
    p_user_id UUID DEFAULT NULL
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
        metadata,
        thought_process,
        routing_info,
        reflection_enabled,
        llm_provider,
        user_id
    ) VALUES (
        p_session_id,
        p_user_query,
        p_ai_response,
        p_context_sources,
        p_metadata,
        p_thought_process,
        p_routing_info,
        p_reflection_enabled,
        p_llm_provider,
        p_user_id
    )
    RETURNING id INTO new_id;
    
    -- Mettre à jour les analytics de routage
    IF p_routing_info IS NOT NULL THEN
        PERFORM update_routing_analytics(
            p_routing_info->>'intent',
            (p_routing_info->>'latency_ms')::INTEGER,
            p_reflection_enabled
        );
    END IF;
    
    RETURN new_id;
END;
$$;

COMMENT ON FUNCTION log_conversation_v2 IS 
'Enregistre une conversation avec support complet pour réflexion et routage';

-- ============================================
-- Fonction: update_routing_analytics
-- Met à jour les statistiques de routage
-- ============================================
CREATE OR REPLACE FUNCTION update_routing_analytics(
    p_intent VARCHAR(50),
    p_routing_latency_ms INTEGER,
    p_reflection_enabled BOOLEAN DEFAULT FALSE
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    today DATE := CURRENT_DATE;
BEGIN
    -- Insérer ou mettre à jour la ligne pour aujourd'hui
    INSERT INTO routing_analytics (
        date,
        intent_general_count,
        intent_documents_count,
        intent_web_search_count,
        intent_hybrid_count,
        intent_greeting_count,
        avg_routing_latency_ms,
        reflection_usage_count,
        updated_at
    ) VALUES (
        today,
        CASE WHEN p_intent = 'general' THEN 1 ELSE 0 END,
        CASE WHEN p_intent = 'documents' THEN 1 ELSE 0 END,
        CASE WHEN p_intent = 'web_search' THEN 1 ELSE 0 END,
        CASE WHEN p_intent = 'hybrid' THEN 1 ELSE 0 END,
        CASE WHEN p_intent = 'greeting' THEN 1 ELSE 0 END,
        COALESCE(p_routing_latency_ms, 0),
        CASE WHEN p_reflection_enabled THEN 1 ELSE 0 END,
        NOW()
    )
    ON CONFLICT (date) DO UPDATE SET
        intent_general_count = routing_analytics.intent_general_count + 
            CASE WHEN p_intent = 'general' THEN 1 ELSE 0 END,
        intent_documents_count = routing_analytics.intent_documents_count + 
            CASE WHEN p_intent = 'documents' THEN 1 ELSE 0 END,
        intent_web_search_count = routing_analytics.intent_web_search_count + 
            CASE WHEN p_intent = 'web_search' THEN 1 ELSE 0 END,
        intent_hybrid_count = routing_analytics.intent_hybrid_count + 
            CASE WHEN p_intent = 'hybrid' THEN 1 ELSE 0 END,
        intent_greeting_count = routing_analytics.intent_greeting_count + 
            CASE WHEN p_intent = 'greeting' THEN 1 ELSE 0 END,
        avg_routing_latency_ms = (
            (routing_analytics.avg_routing_latency_ms * 
             (routing_analytics.intent_general_count + 
              routing_analytics.intent_documents_count +
              routing_analytics.intent_web_search_count +
              routing_analytics.intent_hybrid_count +
              routing_analytics.intent_greeting_count)) +
            COALESCE(p_routing_latency_ms, 0)
        ) / (
            routing_analytics.intent_general_count + 
            routing_analytics.intent_documents_count +
            routing_analytics.intent_web_search_count +
            routing_analytics.intent_hybrid_count +
            routing_analytics.intent_greeting_count + 1
        ),
        reflection_usage_count = routing_analytics.reflection_usage_count + 
            CASE WHEN p_reflection_enabled THEN 1 ELSE 0 END,
        updated_at = NOW();
END;
$$;

COMMENT ON FUNCTION update_routing_analytics IS 
'Met à jour les statistiques agrégées de routage pour la journée en cours';

-- ============================================
-- Fonction: get_routing_analytics
-- Récupère les statistiques de routage
-- ============================================
CREATE OR REPLACE FUNCTION get_routing_analytics(
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    date DATE,
    total_requests BIGINT,
    intent_distribution JSONB,
    avg_routing_latency_ms INTEGER,
    reflection_usage_rate NUMERIC,
    cache_hit_rate NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ra.date,
        (ra.intent_general_count + ra.intent_documents_count + 
         ra.intent_web_search_count + ra.intent_hybrid_count + 
         ra.intent_greeting_count)::BIGINT AS total_requests,
        jsonb_build_object(
            'general', ra.intent_general_count,
            'documents', ra.intent_documents_count,
            'web_search', ra.intent_web_search_count,
            'hybrid', ra.intent_hybrid_count,
            'greeting', ra.intent_greeting_count
        ) AS intent_distribution,
        ra.avg_routing_latency_ms,
        CASE 
            WHEN (ra.intent_general_count + ra.intent_documents_count + 
                  ra.intent_web_search_count + ra.intent_hybrid_count + 
                  ra.intent_greeting_count) > 0 
            THEN ROUND(
                (ra.reflection_usage_count::NUMERIC / 
                 (ra.intent_general_count + ra.intent_documents_count + 
                  ra.intent_web_search_count + ra.intent_hybrid_count + 
                  ra.intent_greeting_count)) * 100, 2
            )
            ELSE 0
        END AS reflection_usage_rate,
        CASE 
            WHEN (ra.cache_hit_count + ra.cache_miss_count) > 0 
            THEN ROUND(
                (ra.cache_hit_count::NUMERIC / 
                 (ra.cache_hit_count + ra.cache_miss_count)) * 100, 2
            )
            ELSE 0
        END AS cache_hit_rate
    FROM routing_analytics ra
    WHERE ra.date >= CURRENT_DATE - p_days
    ORDER BY ra.date DESC;
END;
$$;

COMMENT ON FUNCTION get_routing_analytics IS 
'Récupère les statistiques de routage agrégées sur une période donnée';

-- ============================================
-- Vue: conversations_with_routing
-- Vue enrichie des conversations avec routage
-- ============================================
CREATE OR REPLACE VIEW conversations_with_routing AS
SELECT 
    c.id,
    c.session_id,
    c.user_query,
    c.ai_response,
    c.thought_process,
    c.reflection_enabled,
    c.llm_provider,
    c.routing_info->>'intent' AS routing_intent,
    (c.routing_info->>'confidence')::NUMERIC AS routing_confidence,
    (c.routing_info->>'latency_ms')::INTEGER AS routing_latency_ms,
    c.routing_info->>'use_rag' AS used_rag,
    c.routing_info->>'use_web' AS used_web,
    c.feedback_score,
    c.created_at
FROM conversations c
ORDER BY c.created_at DESC;

COMMENT ON VIEW conversations_with_routing IS 
'Vue des conversations avec informations de routage extraites du JSONB';

-- ============================================
-- Commentaires finaux
-- ============================================
COMMENT ON COLUMN conversations.thought_process IS 
'Processus de réflexion Chain-of-Thought (stocké si mode réflexion activé)';

COMMENT ON COLUMN conversations.routing_info IS 
'Métadonnées de routage intelligent: intent, confidence, use_rag, use_web, latency_ms';
