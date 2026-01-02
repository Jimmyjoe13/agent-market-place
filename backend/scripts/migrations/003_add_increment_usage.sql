-- ============================================
-- Migration: Add increment_user_usage and check_user_limits functions
-- ============================================
-- Date: 2026-01-02
-- Description: 
--   Ajoute les fonctions manquantes pour le tracking d'usage:
--   1. increment_user_usage: incrémente les compteurs de requêtes/tokens
--   2. check_user_limits: vérifie si l'utilisateur peut faire une action
--   
--   Ces fonctions sont critiques pour la monétisation et le contrôle
--   des utilisateurs freemium.
-- ============================================

-- Supprimer les anciennes fonctions si elles existent
DROP FUNCTION IF EXISTS public.increment_user_requests(UUID);
DROP FUNCTION IF EXISTS public.increment_user_usage(UUID, INT, BIGINT);
DROP FUNCTION IF EXISTS public.check_user_limits(UUID, VARCHAR);

-- ============================================
-- Fonction: increment_user_usage
-- ============================================
CREATE OR REPLACE FUNCTION public.increment_user_usage(
    p_user_id UUID,
    p_requests INT DEFAULT 1,
    p_tokens BIGINT DEFAULT 0
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_period TEXT;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Upsert: créer ou mettre à jour le record d'usage
    INSERT INTO public.usage_records (user_id, period, requests_count, tokens_used)
    VALUES (p_user_id, v_period, p_requests, p_tokens)
    ON CONFLICT (user_id, period)
    DO UPDATE SET
        requests_count = usage_records.requests_count + p_requests,
        tokens_used = usage_records.tokens_used + p_tokens,
        updated_at = NOW();
END;
$$;

-- ============================================
-- Fonction: increment_user_requests (alias rétrocompat)
-- ============================================
CREATE OR REPLACE FUNCTION public.increment_user_requests(p_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    PERFORM public.increment_user_usage(p_user_id, 1, 0);
END;
$$;

-- ============================================
-- Fonction: check_user_limits
-- Vérifie si l'utilisateur peut faire une action
-- ============================================
CREATE OR REPLACE FUNCTION public.check_user_limits(
    p_user_id UUID,
    p_action VARCHAR(20) DEFAULT 'request'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_period TEXT;
    v_requests_count INT;
    v_documents_count INT;
    v_api_keys_count INT;
    v_agents_count INT;
    v_requests_limit INT;
    v_documents_limit INT;
    v_api_keys_limit INT;
    v_agents_limit INT;
    v_plan_slug TEXT;
    v_allowed BOOLEAN;
    v_reason TEXT;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- 1. Récupérer les limites du plan de l'utilisateur
    SELECT 
        COALESCE(p.requests_per_month, 100),
        COALESCE(p.documents_limit, 10),
        COALESCE(p.api_keys_limit, 1),
        COALESCE(p.agents_limit, 1),
        COALESCE(p.slug, 'free')
    INTO v_requests_limit, v_documents_limit, v_api_keys_limit, v_agents_limit, v_plan_slug
    FROM public.profiles pr
    LEFT JOIN public.subscriptions s ON s.user_id = pr.id AND s.status = 'active'
    LEFT JOIN public.plans p ON p.id = s.plan_id
    WHERE pr.id = p_user_id;
    
    -- Fallback sur plan free si pas trouvé
    IF v_plan_slug IS NULL THEN
        v_requests_limit := 100;
        v_documents_limit := 10;
        v_api_keys_limit := 1;
        v_agents_limit := 1;
        v_plan_slug := 'free';
    END IF;
    
    -- 2. Compter les requêtes depuis usage_records
    SELECT COALESCE(ur.requests_count, 0)
    INTO v_requests_count
    FROM public.usage_records ur
    WHERE ur.user_id = p_user_id AND ur.period = v_period;
    
    IF v_requests_count IS NULL THEN
        v_requests_count := 0;
    END IF;
    
    -- 3. Compter les documents, clés API et agents réels
    SELECT COUNT(*)::INT INTO v_documents_count
    FROM public.documents d WHERE d.user_id = p_user_id;
    
    SELECT COUNT(*)::INT INTO v_api_keys_count
    FROM public.api_keys ak WHERE ak.user_id = p_user_id AND ak.is_active = TRUE;
    
    SELECT COUNT(*)::INT INTO v_agents_count
    FROM public.agents a WHERE a.user_id = p_user_id AND a.is_active = TRUE;
    
    -- 4. Vérifier selon l'action
    v_allowed := TRUE;
    v_reason := NULL;
    
    CASE p_action
        WHEN 'request' THEN
            -- -1 = illimité
            IF v_requests_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_plan_slug = 'free' AND v_requests_count >= v_requests_limit THEN
                -- Free plan: hard limit, pas d'overage
                v_allowed := FALSE;
                v_reason := 'quota_exceeded';
            ELSE
                -- Plans payants: overage autorisé
                v_allowed := TRUE;
            END IF;
            
        WHEN 'document' THEN
            IF v_documents_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_documents_count >= v_documents_limit THEN
                v_allowed := FALSE;
                v_reason := 'documents_limit_reached';
            END IF;
            
        WHEN 'api_key' THEN
            IF v_api_keys_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_api_keys_count >= v_api_keys_limit THEN
                v_allowed := FALSE;
                v_reason := 'api_keys_limit_reached';
            END IF;
            
        WHEN 'agent' THEN
            IF v_agents_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_agents_count >= v_agents_limit THEN
                v_allowed := FALSE;
                v_reason := 'agents_limit_reached';
            END IF;
            
        ELSE
            v_allowed := FALSE;
            v_reason := 'unknown_action';
    END CASE;
    
    -- 5. Retourner le résultat
    RETURN jsonb_build_object(
        'allowed', v_allowed,
        'reason', v_reason,
        'plan', v_plan_slug,
        'usage', jsonb_build_object(
            'requests', v_requests_count,
            'documents', v_documents_count,
            'api_keys', v_api_keys_count,
            'agents', v_agents_count
        ),
        'limits', jsonb_build_object(
            'requests', v_requests_limit,
            'documents', v_documents_limit,
            'api_keys', v_api_keys_limit,
            'agents', v_agents_limit
        )
    );
END;
$$;

-- Commentaires
COMMENT ON FUNCTION public.increment_user_usage IS 'Incrémente les compteurs de requêtes et tokens pour un utilisateur';
COMMENT ON FUNCTION public.increment_user_requests IS 'Alias pour incrémenter de 1 requête (rétrocompatibilité)';
COMMENT ON FUNCTION public.check_user_limits IS 'Vérifie si l''utilisateur peut faire une action (request, document, api_key, agent)';

-- ============================================
-- Vérification: Tester les fonctions
-- ============================================
-- Après migration, testez avec:
-- SELECT increment_user_usage('VOTRE_USER_ID', 1, 100);
-- SELECT check_user_limits('VOTRE_USER_ID', 'request');
-- SELECT * FROM usage_records WHERE user_id = 'VOTRE_USER_ID';
