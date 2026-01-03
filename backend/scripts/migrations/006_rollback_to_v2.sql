-- ============================================
-- Migration 006: Rollback vers Architecture v2
-- Date: 2026-01-03
-- ============================================
-- 
-- Cette migration annule les changements de la migration 004
-- et restaure l'architecture v2 stable où:
-- - api_keys.agent_id → agents.id (la clé dépend de l'agent)
-- ============================================

-- ============================================
-- Étape 1: Supprimer les vues dépendantes D'ABORD
-- ============================================
DROP VIEW IF EXISTS public.agent_dashboard CASCADE;

-- ============================================
-- Étape 2: Supprimer la colonne agents.api_key_id si elle existe
-- ============================================
ALTER TABLE public.agents DROP COLUMN IF EXISTS api_key_id;

-- ============================================
-- Étape 2: Ajouter api_keys.agent_id si elle n'existe pas
-- (Elle devrait exister dans le schéma original, mais au cas où)
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'api_keys' 
        AND column_name = 'agent_id'
    ) THEN
        ALTER TABLE public.api_keys ADD COLUMN agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE;
    END IF;
END
$$;

-- ============================================
-- Étape 3: Recréer la vue agent_dashboard
-- ============================================
DROP VIEW IF EXISTS public.agent_dashboard CASCADE;

CREATE OR REPLACE VIEW public.agent_dashboard AS
SELECT 
    a.id,
    a.user_id,
    a.name,
    a.description,
    a.model_id,
    a.rag_enabled,
    a.is_active,
    a.tokens_used_this_month,
    a.requests_today,
    a.created_at,
    COUNT(DISTINCT ak.id) AS api_keys_count,
    COUNT(DISTINCT d.id) AS documents_count,
    COUNT(DISTINCT c.id) AS conversations_count
FROM public.agents a
LEFT JOIN public.api_keys ak ON ak.agent_id = a.id AND ak.is_active = TRUE
LEFT JOIN public.documents d ON d.agent_id = a.id
LEFT JOIN public.conversations c ON c.agent_id = a.id AND c.created_at > NOW() - INTERVAL '30 days'
GROUP BY a.id;

-- ============================================
-- Étape 4: Restaurer la fonction validate_api_key pour v2
-- ============================================
DROP FUNCTION IF EXISTS public.validate_api_key(TEXT);
DROP FUNCTION IF EXISTS public.validate_api_key(TEXT, TEXT);

CREATE OR REPLACE FUNCTION public.validate_api_key(
    p_key_hash TEXT,
    p_client_ip TEXT DEFAULT NULL
)
RETURNS TABLE (
    is_valid BOOLEAN,
    key_id UUID,
    agent_id UUID,
    user_id UUID,
    scopes TEXT[],
    rate_limit_per_minute INT,
    rejection_reason TEXT,
    model_id TEXT,
    system_prompt TEXT,
    rag_enabled BOOLEAN,
    agent_name TEXT
) AS $$
DECLARE
    v_key RECORD;
    v_agent RECORD;
BEGIN
    -- Récupérer la clé API avec son agent lié via api_keys.agent_id
    SELECT k.*, a.id as a_id, a.name as a_name, a.model_id as a_model_id, 
           a.system_prompt as a_system_prompt, a.rag_enabled as a_rag_enabled
    INTO v_key
    FROM public.api_keys k
    LEFT JOIN public.agents a ON k.agent_id = a.id
    WHERE k.key_hash = p_key_hash
    LIMIT 1;
    
    -- Clé non trouvée
    IF v_key IS NULL THEN
        RETURN QUERY SELECT 
            FALSE, NULL::UUID, NULL::UUID, NULL::UUID, 
            ARRAY[]::TEXT[], 60, 'invalid_key'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Clé révoquée
    IF NOT v_key.is_active THEN
        RETURN QUERY SELECT 
            FALSE, v_key.id, v_key.agent_id, v_key.user_id, 
            v_key.scopes, v_key.rate_limit_per_minute, 'key_revoked'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            FALSE, v_key.id, v_key.agent_id, v_key.user_id, 
            v_key.scopes, v_key.rate_limit_per_minute, 'key_expired'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Mettre à jour last_used_at
    UPDATE public.api_keys 
    SET last_used_at = NOW(), last_used_ip = p_client_ip
    WHERE id = v_key.id;
    
    -- Retourner les informations
    RETURN QUERY SELECT 
        TRUE,
        v_key.id,
        v_key.agent_id,
        v_key.user_id,
        v_key.scopes,
        v_key.rate_limit_per_minute,
        NULL::TEXT,
        COALESCE(v_key.a_model_id, 'mistral-large-latest'),
        v_key.a_system_prompt,
        COALESCE(v_key.a_rag_enabled, TRUE),
        v_key.a_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Accorder les permissions
GRANT EXECUTE ON FUNCTION public.validate_api_key(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.validate_api_key(TEXT, TEXT) TO authenticated;

-- ============================================
-- Étape 5: Recréer l'index sur agent_id
-- ============================================
CREATE INDEX IF NOT EXISTS idx_api_keys_agent ON public.api_keys(agent_id);

-- ============================================
-- Fin du rollback
-- ============================================
