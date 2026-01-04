-- ============================================
-- Migration 012: Fix check_user_limits to use profiles.plan_slug
-- Date: 2026-01-04
-- ============================================
-- 
-- PROBLÈME: 
-- check_user_limits utilise subscriptions pour récupérer le plan, mais la table 
-- subscriptions peut être vide (le webhook Stripe met à jour profiles.plan_slug).
-- Résultat: les utilisateurs Pro voient les limites du plan Free.
--
-- SOLUTION:
-- Utiliser profiles.plan_slug directement, comme dans get_user_usage (migration 011).
-- ============================================

-- Supprimer l'ancienne version
DROP FUNCTION IF EXISTS public.check_user_limits(UUID, VARCHAR);

-- Recréer avec la bonne logique
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
    v_plan_slug TEXT;
    v_requests_count INT;
    v_documents_count INT;
    v_api_keys_count INT;
    v_agents_count INT;
    v_requests_limit INT;
    v_documents_limit INT;
    v_api_keys_limit INT;
    v_agents_limit INT;
    v_overage_price NUMERIC;
    v_allowed BOOLEAN;
    v_reason TEXT;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- 1. Récupérer le plan_slug DIRECTEMENT depuis profiles (pas subscriptions!)
    SELECT pr.plan_slug INTO v_plan_slug
    FROM public.profiles pr
    WHERE pr.id = p_user_id;
    
    -- Fallback sur 'free' si pas de plan
    IF v_plan_slug IS NULL OR v_plan_slug = '' THEN
        v_plan_slug := 'free';
    END IF;
    
    -- 2. Récupérer les limites depuis le plan correspondant
    SELECT 
        COALESCE(p.requests_per_month, 100),
        COALESCE(p.documents_limit, 10),
        COALESCE(p.api_keys_limit, 1),
        COALESCE(p.agents_limit, 1),
        COALESCE(p.overage_price_cents, 0)
    INTO 
        v_requests_limit,
        v_documents_limit,
        v_api_keys_limit,
        v_agents_limit,
        v_overage_price
    FROM public.plans p 
    WHERE p.slug = v_plan_slug;
    
    -- Si le plan n'existe pas, fallback sur les valeurs par défaut
    IF v_requests_limit IS NULL THEN
        v_requests_limit := 100;
        v_documents_limit := 10;
        v_api_keys_limit := 1;
        v_agents_limit := 1;
        v_overage_price := 0;
    END IF;
    
    -- 3. Compter les requêtes depuis usage_records
    SELECT COALESCE(ur.requests_count, 0)
    INTO v_requests_count
    FROM public.usage_records ur
    WHERE ur.user_id = p_user_id AND ur.period = v_period;
    
    IF v_requests_count IS NULL THEN
        v_requests_count := 0;
    END IF;
    
    -- 4. Compter les documents, clés API et agents ACTIFS en temps réel
    SELECT COUNT(*)::INT INTO v_documents_count
    FROM public.documents d WHERE d.user_id = p_user_id;
    
    SELECT COUNT(*)::INT INTO v_api_keys_count
    FROM public.api_keys ak WHERE ak.user_id = p_user_id AND ak.is_active = TRUE;
    
    SELECT COUNT(*)::INT INTO v_agents_count
    FROM public.agents a WHERE a.user_id = p_user_id AND a.is_active = TRUE;
    
    -- 5. Vérifier selon l'action demandée
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
    
    -- 6. Retourner le résultat
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
COMMENT ON FUNCTION public.check_user_limits IS 'Vérifie si l''utilisateur peut faire une action (utilise profiles.plan_slug directement)';

-- ============================================
-- VÉRIFICATION
-- ============================================
-- Teste avec ton user ID:
-- SELECT check_user_limits('634bb545-8a83-4c6c-a5ba-2c8200d91682', 'api_key');
-- 
-- Tu devrais maintenant voir:
-- - "plan": "pro"
-- - "limits": {"api_keys": 2, ...}
-- - "usage": {"api_keys": 1, ...}
-- - "allowed": true
-- ============================================
