-- ============================================
-- Migration 011: Fix Real-time Entity Counts
-- Date: 2026-01-04
-- ============================================
-- 
-- PROBLÈME: 
-- get_user_usage lit api_keys_count et agents_count depuis usage_records
-- Mais ces compteurs ne sont pas mis à jour en temps réel.
-- Le dashboard affiche 0/2 alors qu'il y a des agents/clés créés.
--
-- SOLUTION:
-- Compter directement depuis les tables agents et api_keys
-- au lieu de lire les compteurs de usage_records
-- ============================================

-- Supprimer l'ancienne version
DROP FUNCTION IF EXISTS public.get_user_usage(UUID);

-- Recréer avec le comptage réel des entités
CREATE OR REPLACE FUNCTION public.get_user_usage(p_user_id UUID)
RETURNS TABLE (
    requests_count INT,
    documents_count INT,
    api_keys_count INT,
    agents_count INT,
    requests_limit INT,
    documents_limit INT,
    api_keys_limit INT,
    agents_limit INT,
    plan_slug TEXT,
    overage_amount_cents INT
)
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
    v_overage INT := 0;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Récupérer le plan_slug directement depuis profiles
    SELECT pr.plan_slug INTO v_plan_slug
    FROM public.profiles pr
    WHERE pr.id = p_user_id;
    
    -- Si pas de plan_slug, utiliser 'free' par défaut
    IF v_plan_slug IS NULL OR v_plan_slug = '' THEN
        v_plan_slug := 'free';
    END IF;
    
    -- Récupérer les limites du plan
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
    
    -- Compter les requêtes depuis usage_records (tracking mensuel)
    SELECT COALESCE(ur.requests_count, 0)
    INTO v_requests_count
    FROM public.usage_records ur
    WHERE ur.user_id = p_user_id AND ur.period = v_period;
    
    -- Si pas de record, initialiser à 0
    IF v_requests_count IS NULL THEN
        v_requests_count := 0;
    END IF;
    
    -- COMPTER LES DOCUMENTS RÉELS (pas depuis usage_records)
    SELECT COUNT(*)::INT INTO v_documents_count
    FROM public.documents d
    WHERE d.user_id = p_user_id;
    
    -- COMPTER LES CLÉS API RÉELLES ACTIVES
    SELECT COUNT(*)::INT INTO v_api_keys_count
    FROM public.api_keys ak
    WHERE ak.user_id = p_user_id AND ak.is_active = TRUE;
    
    -- COMPTER LES AGENTS RÉELS ACTIFS
    SELECT COUNT(*)::INT INTO v_agents_count
    FROM public.agents a
    WHERE a.user_id = p_user_id AND a.is_active = TRUE;
    
    -- Calculer l'overage
    IF v_requests_count > v_requests_limit AND v_overage_price > 0 THEN
        v_overage := ((v_requests_count - v_requests_limit) * v_overage_price)::INT;
    END IF;
    
    -- Retourner les résultats
    RETURN QUERY SELECT 
        v_requests_count,
        v_documents_count,
        v_api_keys_count,
        v_agents_count,
        v_requests_limit,
        v_documents_limit,
        v_api_keys_limit,
        v_agents_limit,
        v_plan_slug,
        v_overage;
END;
$$;

-- ============================================
-- VÉRIFICATION
-- ============================================
-- Teste avec ton user ID:
-- SELECT * FROM get_user_usage('634bb545-8a83-4c6c-a5ba-2c8200d91682');
-- 
-- Tu devrais maintenant voir:
-- - api_keys_count = 1 (ta vraie clé)
-- - agents_count = 1 (ton vrai agent)
-- ============================================
