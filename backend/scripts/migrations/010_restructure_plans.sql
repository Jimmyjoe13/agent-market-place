-- ============================================
-- Migration 010: Restructuration Système de Plans
-- Date: 2026-01-04
-- ============================================
-- 
-- PROBLÈME: 
-- 1. Le webhook Stripe met à jour profiles.plan_slug mais ne crée pas
--    d'entrée dans subscriptions
-- 2. get_user_usage utilise subscriptions pour les limites, donc 
--    les utilisateurs Pro voient les limites null/Free
--
-- SOLUTION:
-- 1. Modifier get_user_usage pour utiliser profiles.plan_slug directement
-- 2. Restructurer les plans pour rentabilité (500 req/mois + overage)
-- ============================================

-- ============================================
-- 1. Mettre à jour le plan Pro
-- ============================================
UPDATE public.plans 
SET 
    name = 'Pro',
    description = 'Évolutif avec vos besoins - 500 requêtes incluses',
    price_monthly_cents = 2999,
    price_yearly_cents = 31188,
    requests_per_month = 500,
    api_keys_limit = 2,
    documents_limit = 25,
    agents_limit = 2,
    overage_price_cents = 6.0,
    features = '["500 requêtes/mois incluses", "2 agents", "25 documents", "2 clés API", "Support email prioritaire", "BYOK (Bring Your Own Key)", "Webhooks", "Export des données"]',
    updated_at = NOW()
WHERE slug = 'pro';

-- ============================================
-- 2. S'assurer que le plan Free a les bonnes limites
-- ============================================
UPDATE public.plans 
SET 
    requests_per_month = 100,
    api_keys_limit = 1,
    documents_limit = 10,
    agents_limit = 1,
    overage_price_cents = 0,
    features = '["100 requêtes/mois", "1 agent", "10 documents", "1 clé API", "Support communauté"]',
    updated_at = NOW()
WHERE slug = 'free';

-- ============================================
-- 3. Corriger get_user_usage pour utiliser profiles.plan_slug
-- ============================================
-- Cette fonction utilise maintenant directement le plan_slug du profil
-- au lieu de passer par la table subscriptions (qui peut être vide)

-- Supprimer l'ancienne version (signature différente)
DROP FUNCTION IF EXISTS public.get_user_usage(UUID);

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
    v_requests_limit INT;
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
    
    RETURN QUERY
    SELECT 
        COALESCE(ur.requests_count, 0)::INT,
        COALESCE(ur.documents_count, 0)::INT,
        COALESCE(ur.api_keys_count, 0)::INT,
        COALESCE(ur.agents_count, 0)::INT,
        COALESCE(p.requests_per_month, 100)::INT,
        COALESCE(p.documents_limit, 10)::INT,
        COALESCE(p.api_keys_limit, 1)::INT,
        COALESCE(p.agents_limit, 1)::INT,
        v_plan_slug,
        -- Calcul de l'overage
        CASE 
            WHEN COALESCE(ur.requests_count, 0) > COALESCE(p.requests_per_month, 100) 
                 AND COALESCE(p.overage_price_cents, 0) > 0
            THEN ((COALESCE(ur.requests_count, 0) - COALESCE(p.requests_per_month, 100)) 
                  * COALESCE(p.overage_price_cents, 0))::INT
            ELSE 0
        END
    FROM public.profiles pr
    -- Jointure directe sur le plan slug, pas sur subscriptions
    LEFT JOIN public.plans p ON p.slug = v_plan_slug
    LEFT JOIN public.usage_records ur ON ur.user_id = pr.id AND ur.period = v_period
    WHERE pr.id = p_user_id;
END;
$$;

-- ============================================
-- 4. Fonction de calcul d'overage (pour usage dans les rapports)
-- ============================================
CREATE OR REPLACE FUNCTION public.calculate_overage_amount(
    p_user_id UUID,
    p_period TEXT
) RETURNS INT AS $$
DECLARE
    v_usage_count INT;
    v_requests_limit INT;
    v_overage_price NUMERIC;
    v_plan_slug TEXT;
BEGIN
    -- Récupérer le plan slug de l'utilisateur
    SELECT plan_slug INTO v_plan_slug
    FROM profiles
    WHERE id = p_user_id;
    
    IF v_plan_slug IS NULL THEN
        v_plan_slug := 'free';
    END IF;
    
    -- Récupérer les limites du plan
    SELECT requests_per_month, overage_price_cents 
    INTO v_requests_limit, v_overage_price
    FROM plans
    WHERE slug = v_plan_slug;
    
    -- Récupérer l'usage
    SELECT COALESCE(requests_count, 0) INTO v_usage_count
    FROM usage_records
    WHERE user_id = p_user_id AND period = p_period;
    
    -- Calculer l'overage
    IF v_requests_limit > 0 AND v_usage_count > v_requests_limit AND v_overage_price > 0 THEN
        RETURN ((v_usage_count - v_requests_limit) * v_overage_price)::INT;
    END IF;
    
    RETURN 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 5. Fonction pour créer automatiquement une subscription 
--    quand un utilisateur passe en Pro
-- ============================================
CREATE OR REPLACE FUNCTION public.sync_subscription_from_profile()
RETURNS TRIGGER AS $$
DECLARE
    v_plan_id UUID;
BEGIN
    -- Si le plan_slug a changé vers 'pro' et le status est 'active'
    IF NEW.plan_slug = 'pro' AND NEW.subscription_status = 'active' THEN
        -- Récupérer l'ID du plan Pro
        SELECT id INTO v_plan_id FROM public.plans WHERE slug = 'pro';
        
        -- Créer ou mettre à jour la subscription
        INSERT INTO public.subscriptions (
            user_id, 
            plan_id, 
            status, 
            stripe_subscription_id,
            stripe_customer_id,
            current_period_start,
            current_period_end
        )
        VALUES (
            NEW.id,
            v_plan_id,
            'active',
            NEW.stripe_subscription_id,
            NEW.stripe_customer_id,
            NOW(),
            NOW() + INTERVAL '1 month'
        )
        ON CONFLICT (user_id) WHERE status = 'active'
        DO UPDATE SET
            plan_id = v_plan_id,
            status = 'active',
            stripe_subscription_id = NEW.stripe_subscription_id,
            stripe_customer_id = NEW.stripe_customer_id,
            updated_at = NOW();
    
    -- Si le plan passe à 'free' ou le status n'est plus 'active'
    ELSIF NEW.plan_slug = 'free' OR NEW.subscription_status != 'active' THEN
        -- Mettre à jour la subscription existante en 'canceled'
        UPDATE public.subscriptions
        SET status = 'canceled', canceled_at = NOW(), updated_at = NOW()
        WHERE user_id = NEW.id AND status = 'active';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Supprimer l'ancien trigger s'il existe
DROP TRIGGER IF EXISTS trigger_sync_subscription ON public.profiles;

-- Créer le trigger
CREATE TRIGGER trigger_sync_subscription
    AFTER UPDATE OF plan_slug, subscription_status ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.sync_subscription_from_profile();

-- ============================================
-- 6. Synchroniser les utilisateurs Pro existants
-- ============================================
-- Pour les utilisateurs déjà en Pro dans profiles, créer leur subscription
INSERT INTO public.subscriptions (user_id, plan_id, status, stripe_subscription_id, stripe_customer_id, current_period_start, current_period_end)
SELECT 
    pr.id,
    p.id,
    'active',
    pr.stripe_subscription_id,
    pr.stripe_customer_id,
    NOW(),
    NOW() + INTERVAL '1 month'
FROM public.profiles pr
CROSS JOIN public.plans p
WHERE pr.plan_slug = 'pro' 
  AND pr.subscription_status = 'active'
  AND p.slug = 'pro'
  AND NOT EXISTS (
      SELECT 1 FROM public.subscriptions s 
      WHERE s.user_id = pr.id AND s.status = 'active'
  );

-- ============================================
-- VÉRIFICATION POST-MIGRATION
-- ============================================
-- SELECT * FROM plans WHERE slug IN ('free', 'pro');
-- SELECT * FROM subscriptions WHERE status = 'active';
-- SELECT * FROM get_user_usage('YOUR_USER_ID_HERE');
-- ============================================
