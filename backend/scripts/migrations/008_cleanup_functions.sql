-- ============================================
-- Migration 008: Cleanup Duplicate Functions
-- Date: 2026-01-03
-- ============================================
-- 
-- Cette migration nettoie les fonctions SQL en doublon
-- qui causent l'erreur PGRST203 (cannot choose best candidate)
-- ============================================

-- 1. Supprimer TOUTES les versions de get_conversation_analytics
DO $$ 
DECLARE 
    func_sig text;
BEGIN 
    FOR func_sig IN 
        SELECT format('%I.%I(%s)', ns.nspname, p.proname, oidvectortypes(p.proargtypes))
        FROM pg_proc p 
        INNER JOIN pg_namespace ns ON (p.pronamespace = ns.oid)
        WHERE ns.nspname = 'public' 
        AND p.proname = 'get_conversation_analytics'
    LOOP 
        RAISE NOTICE 'Dropping function: %', func_sig;
        EXECUTE 'DROP FUNCTION IF EXISTS ' || func_sig; 
    END LOOP; 
END $$;

-- 2. Supprimer TOUTES les versions de log_conversation_v2
DO $$ 
DECLARE 
    func_sig text;
BEGIN 
    FOR func_sig IN 
        SELECT format('%I.%I(%s)', ns.nspname, p.proname, oidvectortypes(p.proargtypes))
        FROM pg_proc p 
        INNER JOIN pg_namespace ns ON (p.pronamespace = ns.oid)
        WHERE ns.nspname = 'public' 
        AND p.proname = 'log_conversation_v2'
    LOOP 
        RAISE NOTICE 'Dropping function: %', func_sig;
        EXECUTE 'DROP FUNCTION IF EXISTS ' || func_sig; 
    END LOOP; 
END $$;

-- 3. Recréer get_conversation_analytics avec UNE SEULE signature
CREATE OR REPLACE FUNCTION public.get_conversation_analytics(
    p_days INT DEFAULT 30
)
RETURNS TABLE (
    total_conversations BIGINT,
    avg_feedback_score NUMERIC,
    conversations_with_reflection BIGINT,
    avg_latency_ms NUMERIC,
    total_tokens BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT AS total_conversations,
        ROUND(AVG(c.feedback_score), 2) AS avg_feedback_score,
        COUNT(*) FILTER (WHERE c.reflection_enabled = TRUE)::BIGINT AS conversations_with_reflection,
        ROUND(AVG(c.latency_ms), 0) AS avg_latency_ms,
        SUM(COALESCE(c.prompt_tokens, 0) + COALESCE(c.completion_tokens, 0))::BIGINT AS total_tokens
    FROM public.conversations c
    WHERE c.created_at > NOW() - (p_days || ' days')::INTERVAL;
END;
$$;

COMMENT ON FUNCTION public.get_conversation_analytics(INT) IS 
  'Récupère les analytics de conversation pour les N derniers jours';

-- 4. Recréer log_conversation_v2 avec UNE SEULE signature
CREATE OR REPLACE FUNCTION public.log_conversation_v2(
    p_session_id TEXT,
    p_user_query TEXT,
    p_ai_response TEXT,
    p_user_id UUID DEFAULT NULL,
    p_agent_id UUID DEFAULT NULL,
    p_context_sources JSONB DEFAULT '[]'::JSONB,
    p_metadata JSONB DEFAULT '{}'::JSONB,
    p_prompt_tokens INT DEFAULT 0,
    p_completion_tokens INT DEFAULT 0,
    p_model_used TEXT DEFAULT NULL,
    p_latency_ms INT DEFAULT NULL,
    p_llm_provider VARCHAR(50) DEFAULT 'mistral',
    p_thought_process JSONB DEFAULT NULL,
    p_routing_info JSONB DEFAULT NULL,
    p_reflection_enabled BOOLEAN DEFAULT FALSE
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    INSERT INTO public.conversations (
        session_id,
        user_query,
        ai_response,
        user_id,
        agent_id,
        context_sources,
        metadata,
        prompt_tokens,
        completion_tokens,
        model_used,
        latency_ms,
        llm_provider,
        thought_process,
        routing_info,
        reflection_enabled
    ) VALUES (
        p_session_id,
        p_user_query,
        p_ai_response,
        p_user_id,
        p_agent_id,
        p_context_sources,
        p_metadata,
        p_prompt_tokens,
        p_completion_tokens,
        p_model_used,
        p_latency_ms,
        p_llm_provider,
        p_thought_process,
        p_routing_info,
        p_reflection_enabled
    )
    RETURNING id INTO v_conversation_id;
    
    RETURN v_conversation_id;
END;
$$;

COMMENT ON FUNCTION public.log_conversation_v2 IS 
  'Enregistre une conversation avec support complet des colonnes réflexion/routage';

-- ============================================
-- Migration terminée
-- ============================================
