-- ============================================
-- Migration 005: Corriger validate_api_key
-- Date: 2026-01-03
-- ============================================
-- 
-- Cette migration corrige la fonction validate_api_key
-- pour utiliser la nouvelle architecture v3 où l'agent
-- est lié via agents.api_key_id au lieu de api_keys.agent_id.
-- ============================================

-- Supprimer l'ancienne fonction
DROP FUNCTION IF EXISTS public.validate_api_key(TEXT);
DROP FUNCTION IF EXISTS public.validate_api_key(TEXT, TEXT);

-- Recréer la fonction avec la nouvelle architecture
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
    -- Récupérer la clé API
    SELECT k.* INTO v_key
    FROM public.api_keys k
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
            FALSE, v_key.id, NULL::UUID, v_key.user_id, 
            v_key.scopes, v_key.rate_limit_per_minute, 'key_revoked'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            FALSE, v_key.id, NULL::UUID, v_key.user_id, 
            v_key.scopes, v_key.rate_limit_per_minute, 'key_expired'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Récupérer l'agent lié (architecture v3: agents.api_key_id -> api_keys.id)
    SELECT a.* INTO v_agent
    FROM public.agents a
    WHERE a.api_key_id = v_key.id
    LIMIT 1;
    
    -- Mettre à jour last_used_at
    UPDATE public.api_keys 
    SET last_used_at = NOW(), last_used_ip = p_client_ip
    WHERE id = v_key.id;
    
    -- Retourner les informations
    RETURN QUERY SELECT 
        TRUE,
        v_key.id,
        v_agent.id,  -- Peut être NULL si pas d'agent
        v_key.user_id,
        v_key.scopes,
        v_key.rate_limit_per_minute,
        NULL::TEXT,
        COALESCE(v_agent.model_id, 'mistral-large-latest'),
        v_agent.system_prompt,
        COALESCE(v_agent.rag_enabled, TRUE),
        v_agent.name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Accorder les permissions
GRANT EXECUTE ON FUNCTION public.validate_api_key(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.validate_api_key(TEXT, TEXT) TO authenticated;
