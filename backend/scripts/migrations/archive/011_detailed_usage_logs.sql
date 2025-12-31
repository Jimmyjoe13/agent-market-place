-- ============================================
-- Migration 011: Detailed Usage Logs
-- RAG Agent IA - Logs pour debugging DX
-- ============================================
-- 
-- Cette migration étend les logs d'utilisation avec des infos
-- détaillées pour le debugging par les développeurs.
--
-- Features:
--   - Contexte RAG trouvé (preview)
--   - Réponse LLM (preview)
--   - Intent de routage
--   - Latence
--
-- Breaking Changes: Aucun
-- ============================================

-- ============================================
-- 1. Extension api_key_usage_logs
-- ============================================

-- Contexte RAG
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS rag_context_found BOOLEAN DEFAULT FALSE;

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS rag_sources_count INT DEFAULT 0;

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS rag_context_preview TEXT;

-- Réponse LLM
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS llm_response_preview TEXT;

-- Routage
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS routing_intent VARCHAR(50);

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS routing_confidence FLOAT;

-- Performance
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS latency_ms INT;

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS embedding_latency_ms INT;

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS llm_latency_ms INT;

-- Erreurs
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS error_type VARCHAR(100);

ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS error_details TEXT;

-- ============================================
-- 2. Index pour requêtes dashboard
-- ============================================

-- Index pour filtrage par intent
CREATE INDEX IF NOT EXISTS idx_usage_logs_routing_intent
ON api_key_usage_logs(routing_intent)
WHERE routing_intent IS NOT NULL;

-- Index pour filtrage par erreurs
CREATE INDEX IF NOT EXISTS idx_usage_logs_errors
ON api_key_usage_logs(error_type)
WHERE error_type IS NOT NULL;

-- Index pour analyse de latence
CREATE INDEX IF NOT EXISTS idx_usage_logs_latency
ON api_key_usage_logs(latency_ms)
WHERE latency_ms IS NOT NULL;

-- ============================================
-- 3. Vue pour dashboard des logs
-- ============================================

CREATE OR REPLACE VIEW agent_logs_dashboard AS
SELECT 
    aul.id,
    aul.created_at,
    ak.agent_name,
    ak.id as api_key_id,
    aul.endpoint,
    aul.status_code,
    aul.prompt_tokens,
    aul.completion_tokens,
    aul.prompt_tokens + aul.completion_tokens as total_tokens,
    aul.model_used,
    aul.routing_intent,
    aul.routing_confidence,
    aul.rag_context_found,
    aul.rag_sources_count,
    aul.latency_ms,
    aul.error_type,
    CASE 
        WHEN aul.error_type IS NOT NULL THEN 'error'
        WHEN aul.rag_context_found THEN 'rag'
        ELSE 'direct'
    END as response_type
FROM api_key_usage_logs aul
JOIN api_keys ak ON aul.api_key_id = ak.id
ORDER BY aul.created_at DESC;

-- ============================================
-- 4. Vue pour agrégats par agent
-- ============================================

CREATE OR REPLACE VIEW agent_usage_summary AS
SELECT 
    ak.id as api_key_id,
    ak.agent_name,
    ak.model_id,
    COUNT(aul.id) as total_requests,
    SUM(aul.prompt_tokens + aul.completion_tokens) as total_tokens,
    AVG(aul.latency_ms) as avg_latency_ms,
    COUNT(CASE WHEN aul.error_type IS NOT NULL THEN 1 END) as error_count,
    COUNT(CASE WHEN aul.rag_context_found THEN 1 END) as rag_requests,
    MAX(aul.created_at) as last_request_at
FROM api_keys ak
LEFT JOIN api_key_usage_logs aul ON ak.id = aul.api_key_id
    AND aul.created_at > NOW() - INTERVAL '30 days'
WHERE ak.is_active = TRUE
GROUP BY ak.id, ak.agent_name, ak.model_id;

-- ============================================
-- 5. Fonction pour log détaillé
-- ============================================

CREATE OR REPLACE FUNCTION log_detailed_usage(
    p_api_key_id UUID,
    p_endpoint VARCHAR(200),
    p_status_code INT,
    p_prompt_tokens INT DEFAULT 0,
    p_completion_tokens INT DEFAULT 0,
    p_model_used VARCHAR(50) DEFAULT NULL,
    p_routing_intent VARCHAR(50) DEFAULT NULL,
    p_routing_confidence FLOAT DEFAULT NULL,
    p_rag_context_found BOOLEAN DEFAULT FALSE,
    p_rag_sources_count INT DEFAULT 0,
    p_rag_context_preview TEXT DEFAULT NULL,
    p_llm_response_preview TEXT DEFAULT NULL,
    p_latency_ms INT DEFAULT NULL,
    p_embedding_latency_ms INT DEFAULT NULL,
    p_llm_latency_ms INT DEFAULT NULL,
    p_error_type VARCHAR(100) DEFAULT NULL,
    p_error_details TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO api_key_usage_logs (
        api_key_id,
        endpoint,
        status_code,
        prompt_tokens,
        completion_tokens,
        model_used,
        routing_intent,
        routing_confidence,
        rag_context_found,
        rag_sources_count,
        rag_context_preview,
        llm_response_preview,
        latency_ms,
        embedding_latency_ms,
        llm_latency_ms,
        error_type,
        error_details
    ) VALUES (
        p_api_key_id,
        p_endpoint,
        p_status_code,
        p_prompt_tokens,
        p_completion_tokens,
        p_model_used,
        p_routing_intent,
        p_routing_confidence,
        p_rag_context_found,
        p_rag_sources_count,
        -- Tronquer les previews à 500 chars
        LEFT(p_rag_context_preview, 500),
        LEFT(p_llm_response_preview, 500),
        p_latency_ms,
        p_embedding_latency_ms,
        p_llm_latency_ms,
        p_error_type,
        p_error_details
    ) RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$;

-- ============================================
-- 6. Fonction pour récupérer les logs d'un agent
-- ============================================

CREATE OR REPLACE FUNCTION get_agent_logs(
    p_api_key_id UUID,
    p_limit INT DEFAULT 50,
    p_offset INT DEFAULT 0,
    p_intent_filter VARCHAR(50) DEFAULT NULL,
    p_error_only BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    id UUID,
    created_at TIMESTAMP WITH TIME ZONE,
    endpoint VARCHAR(200),
    status_code INT,
    total_tokens INT,
    model_used VARCHAR(50),
    routing_intent VARCHAR(50),
    rag_sources_count INT,
    latency_ms INT,
    error_type VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        aul.id,
        aul.created_at,
        aul.endpoint,
        aul.status_code,
        (aul.prompt_tokens + aul.completion_tokens)::INT as total_tokens,
        aul.model_used,
        aul.routing_intent,
        aul.rag_sources_count,
        aul.latency_ms,
        aul.error_type
    FROM api_key_usage_logs aul
    WHERE aul.api_key_id = p_api_key_id
        AND (p_intent_filter IS NULL OR aul.routing_intent = p_intent_filter)
        AND (NOT p_error_only OR aul.error_type IS NOT NULL)
    ORDER BY aul.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- ============================================
-- Comments
-- ============================================

COMMENT ON COLUMN api_key_usage_logs.rag_context_preview IS 'Preview du contexte RAG trouvé (500 chars max)';
COMMENT ON COLUMN api_key_usage_logs.llm_response_preview IS 'Preview de la réponse LLM (500 chars max)';
COMMENT ON COLUMN api_key_usage_logs.routing_intent IS 'Intent détecté par l''orchestrateur (general, documents, web, hybrid)';
COMMENT ON COLUMN api_key_usage_logs.latency_ms IS 'Latence totale de la requête en millisecondes';
COMMENT ON VIEW agent_logs_dashboard IS 'Vue pour le dashboard de logs développeur';
COMMENT ON VIEW agent_usage_summary IS 'Agrégats d''utilisation par agent (30 derniers jours)';
COMMENT ON FUNCTION log_detailed_usage IS 'Enregistre un log d''utilisation détaillé';
COMMENT ON FUNCTION get_agent_logs IS 'Récupère les logs d''un agent avec filtres';
