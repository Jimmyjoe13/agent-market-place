-- ============================================
-- Migration: Fix get_user_usage function
-- ============================================
-- Date: 2026-01-02
-- Description: 
--   La fonction get_user_usage lisait les compteurs depuis usage_records,
--   mais ces compteurs n'étaient jamais mis à jour lors de la création
--   de clés API, documents ou agents.
--   
--   Cette migration corrige le problème en comptant DIRECTEMENT
--   les enregistrements réels dans les tables api_keys, documents et agents.
--   
--   Seul requests_count reste lu depuis usage_records car c'est un compteur
--   qui est incrémenté à chaque requête API.
-- ============================================

-- Supprimer l'ancienne fonction si elle existe
DROP FUNCTION IF EXISTS public.get_user_usage(UUID);

-- Créer la nouvelle fonction avec comptage réel
CREATE OR REPLACE FUNCTION public.get_user_usage(p_user_id UUID)
RETURNS TABLE (
    requests_count INT,
    documents_count INT,
    api_keys_count INT,
    agents_count INT,
    tokens_used BIGINT,
    requests_limit INT,
    documents_limit INT,
    api_keys_limit INT,
    agents_limit INT,
    plan_slug TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_period TEXT;
    v_requests_count INT;
    v_tokens_used BIGINT;
    v_documents_count INT;
    v_api_keys_count INT;
    v_agents_count INT;
    v_plan_limits RECORD;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- 1. Récupérer les limites du plan de l'utilisateur
    SELECT 
        COALESCE(p.requests_per_month, 100) as requests_limit,
        COALESCE(p.documents_limit, 10) as documents_limit,
        COALESCE(p.api_keys_limit, 1) as api_keys_limit,
        COALESCE(p.agents_limit, 1) as agents_limit,
        COALESCE(p.slug, 'free') as slug
    INTO v_plan_limits
    FROM public.profiles pr
    LEFT JOIN public.subscriptions s ON s.user_id = pr.id AND s.status = 'active'
    LEFT JOIN public.plans p ON p.id = s.plan_id
    WHERE pr.id = p_user_id;
    
    -- Fallback sur plan free si pas trouvé
    IF v_plan_limits IS NULL THEN
        v_plan_limits := ROW(100, 10, 1, 1, 'free');
    END IF;
    
    -- 2. Compter les requêtes et tokens depuis usage_records (compteur incrémental)
    SELECT 
        COALESCE(ur.requests_count, 0),
        COALESCE(ur.tokens_used, 0)
    INTO v_requests_count, v_tokens_used
    FROM public.usage_records ur
    WHERE ur.user_id = p_user_id AND ur.period = v_period;
    
    -- Fallback si pas de record
    IF v_requests_count IS NULL THEN
        v_requests_count := 0;
        v_tokens_used := 0;
    END IF;
    
    -- 3. Compter les DOCUMENTS réels (COUNT direct)
    SELECT COUNT(*)::INT INTO v_documents_count
    FROM public.documents d
    WHERE d.user_id = p_user_id;
    
    -- 4. Compter les CLÉS API réelles actives (COUNT direct)
    SELECT COUNT(*)::INT INTO v_api_keys_count
    FROM public.api_keys ak
    WHERE ak.user_id = p_user_id AND ak.is_active = TRUE;
    
    -- 5. Compter les AGENTS réels actifs (COUNT direct)
    SELECT COUNT(*)::INT INTO v_agents_count
    FROM public.agents a
    WHERE a.user_id = p_user_id AND a.is_active = TRUE;
    
    -- 6. Retourner le résultat
    RETURN QUERY SELECT 
        v_requests_count,
        v_documents_count,
        v_api_keys_count,
        v_agents_count,
        v_tokens_used,
        v_plan_limits.requests_limit,
        v_plan_limits.documents_limit,
        v_plan_limits.api_keys_limit,
        v_plan_limits.agents_limit,
        v_plan_limits.slug;
END;
$$;

-- Ajouter un commentaire
COMMENT ON FUNCTION public.get_user_usage IS 'Récupère l''usage réel: comptage direct des documents, clés API et agents + requests depuis usage_records';

-- ============================================
-- TEST: Vérifier que la fonction fonctionne
-- ============================================
-- Exécutez ceci manuellement après la migration pour tester:
-- SELECT * FROM get_user_usage('VOTRE_USER_ID');
