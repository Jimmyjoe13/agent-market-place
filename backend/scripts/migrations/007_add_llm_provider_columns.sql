-- ============================================
-- Migration 007 v2: Fix & Add LLM Provider Columns
-- Date: 2026-01-03
-- ============================================

-- 1. Nettoyage des conflits de fonctions (Erreur 42725)
DO $$ 
DECLARE 
    func_sig text;
BEGIN 
    -- Trouve toutes les variantes de log_conversation_v2 et les supprime
    FOR func_sig IN 
        SELECT format('%I.%I(%s)', ns.nspname, p.proname, oidvectortypes(p.proargtypes))
        FROM pg_proc p 
        INNER JOIN pg_namespace ns ON (p.pronamespace = ns.oid)
        WHERE ns.nspname = 'public' AND p.proname = 'log_conversation_v2'
    LOOP 
        RAISE NOTICE 'Dropping function: %', func_sig;
        EXECUTE 'DROP FUNCTION IF EXISTS ' || func_sig; 
    END LOOP; 
END $$;

-- 2. Mise à jour de la table conversations
ALTER TABLE public.conversations 
ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50) DEFAULT 'mistral';

-- Gestion intelligente de thought_process (TEXT -> JSONB si nécessaire)
DO $$
BEGIN
    -- Si la colonne existe en TEXT, on la convertit
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'conversations' 
        AND column_name = 'thought_process' AND data_type = 'text'
    ) THEN
        -- On essaie de convertir, sinon on met NULL
        BEGIN
            ALTER TABLE public.conversations 
            ALTER COLUMN thought_process TYPE JSONB USING thought_process::JSONB;
        EXCEPTION WHEN OTHERS THEN
            ALTER TABLE public.conversations 
            ALTER COLUMN thought_process TYPE JSONB USING NULL;
        END;
    -- Sinon on la crée si elle n'existe pas
    ELSE
        ALTER TABLE public.conversations 
        ADD COLUMN IF NOT EXISTS thought_process JSONB;
    END IF;
END $$;

ALTER TABLE public.conversations 
ADD COLUMN IF NOT EXISTS routing_info JSONB;

ALTER TABLE public.conversations 
ADD COLUMN IF NOT EXISTS reflection_enabled BOOLEAN DEFAULT FALSE;

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_llm_provider 
ON public.conversations(llm_provider);

CREATE INDEX IF NOT EXISTS idx_conversations_reflection 
ON public.conversations(reflection_enabled) 
WHERE reflection_enabled = TRUE;

-- 4. Commentaires
COMMENT ON COLUMN public.conversations.llm_provider IS 
  'Provider LLM utilisé pour cette conversation (mistral, openai, gemini, deepseek)';

COMMENT ON COLUMN public.conversations.thought_process IS 
  'Processus de réflexion de l''agent (pour mode reflection)';

COMMENT ON COLUMN public.conversations.routing_info IS 
  'Informations de routage (sélection du modèle, raison)';

COMMENT ON COLUMN public.conversations.reflection_enabled IS 
  'Indique si le mode réflexion était activé pour cette conversation';

-- 5. Création de la fonction log_conversation_v2 (Version Finale)
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

-- 6. Analytics Function (si besoin de refresh)
CREATE OR REPLACE FUNCTION public.get_conversation_analytics(
    p_days INT DEFAULT 30,
    p_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    total_conversations BIGINT,
    avg_feedback_score NUMERIC,
    conversations_with_reflection BIGINT,
    conversations_by_provider JSONB,
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
        jsonb_object_agg(
            COALESCE(c.llm_provider, 'unknown'),
            cnt
        ) AS conversations_by_provider,
        ROUND(AVG(c.latency_ms), 0) AS avg_latency_ms,
        SUM(COALESCE(c.prompt_tokens, 0) + COALESCE(c.completion_tokens, 0))::BIGINT AS total_tokens
    FROM public.conversations c
    LEFT JOIN LATERAL (
        SELECT c2.llm_provider, COUNT(*) as cnt
        FROM public.conversations c2
        WHERE c2.created_at > NOW() - (p_days || ' days')::INTERVAL
          AND (p_user_id IS NULL OR c2.user_id = p_user_id)
        GROUP BY c2.llm_provider
    ) provider_counts ON TRUE
    WHERE c.created_at > NOW() - (p_days || ' days')::INTERVAL
      AND (p_user_id IS NULL OR c.user_id = p_user_id);
END;
$$;
