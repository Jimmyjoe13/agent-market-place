-- ============================================
-- Migration 005: Multi-Tenant & Monetization
-- RAG Agent IA - Developer Platform
-- ============================================
--
-- Cette migration transforme le système en plateforme multi-tenant
-- avec système de monétisation (subscriptions + usage-based billing).
--
-- TABLES CRÉÉES:
--   - users: Utilisateurs OAuth (Google via NextAuth.js)
--   - plans: Plans d'abonnement (Free, Pro, Scale, Enterprise)
--   - subscriptions: Abonnements actifs des utilisateurs
--   - usage_records: Tracking de l'usage pour facturation
--
-- MODIFICATIONS:
--   - Ajout de user_id aux tables existantes
--   - RLS policies pour isolation tenant
--
-- EXÉCUTION:
--   1. Exécuter ce script dans Supabase SQL Editor
--   2. Migrer les données existantes vers user legacy
-- ============================================

-- ============================================
-- Table: users
-- Utilisateurs de la plateforme (OAuth)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Email unique (identifiant principal)
    email VARCHAR(255) UNIQUE NOT NULL,
    
    -- Nom d'affichage
    name VARCHAR(255),
    
    -- URL de l'avatar (Google profile picture)
    avatar_url TEXT,
    
    -- Provider OAuth (google, github, email)
    provider VARCHAR(50) NOT NULL DEFAULT 'email',
    
    -- ID unique du provider (subject claim)
    provider_id VARCHAR(255),
    
    -- Email vérifié
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Rôle utilisateur
    role VARCHAR(20) DEFAULT 'user' CHECK (
        role IN ('user', 'admin', 'superadmin')
    ),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Index sur email pour login rapide
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Index sur provider_id pour OAuth lookup
CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id);

-- Trigger updated_at
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Table: plans
-- Plans d'abonnement disponibles
-- ============================================
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identifiant unique du plan (free, pro, scale, enterprise)
    slug VARCHAR(50) UNIQUE NOT NULL,
    
    -- Nom d'affichage
    name VARCHAR(100) NOT NULL,
    
    -- Description du plan
    description TEXT,
    
    -- Prix mensuel en centimes (0 = gratuit)
    price_monthly_cents INT NOT NULL DEFAULT 0,
    
    -- Prix annuel en centimes (avec réduction)
    price_yearly_cents INT NOT NULL DEFAULT 0,
    
    -- Quotas inclus
    requests_per_month INT NOT NULL DEFAULT 100,
    api_keys_limit INT NOT NULL DEFAULT 1,
    documents_limit INT NOT NULL DEFAULT 10,
    
    -- Prix par requête au-delà du quota (en centimes, 0 = pas d'overage)
    overage_price_cents NUMERIC(10, 4) DEFAULT 0,
    
    -- Fonctionnalités incluses (JSON)
    features JSONB DEFAULT '[]'::jsonb,
    
    -- Ordre d'affichage
    display_order INT DEFAULT 0,
    
    -- Actif pour les nouveaux abonnements
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insérer les plans par défaut
INSERT INTO plans (slug, name, description, price_monthly_cents, price_yearly_cents, requests_per_month, api_keys_limit, documents_limit, overage_price_cents, features, display_order)
VALUES 
    (
        'free',
        'Free',
        'Parfait pour découvrir la plateforme',
        0,
        0,
        100,
        1,
        10,
        0,
        '["100 requêtes/mois", "1 clé API", "10 documents", "Support communauté"]'::jsonb,
        1
    ),
    (
        'pro',
        'Pro',
        'Pour les développeurs sérieux',
        2900,
        29000,
        5000,
        5,
        100,
        0.20,
        '["5 000 requêtes/mois", "5 clés API", "100 documents", "Support email", "Playground avancé"]'::jsonb,
        2
    ),
    (
        'scale',
        'Scale',
        'Pour les équipes en croissance',
        9900,
        99000,
        50000,
        -1,
        -1,
        0.15,
        '["50 000 requêtes/mois", "Clés illimitées", "Documents illimités", "Support prioritaire", "Analytics avancés", "Webhooks"]'::jsonb,
        3
    ),
    (
        'enterprise',
        'Enterprise',
        'Solution sur mesure',
        0,
        0,
        -1,
        -1,
        -1,
        0,
        '["Requêtes illimitées", "SSO/SAML", "SLA 99.9%", "Account Manager dédié", "Formation équipe"]'::jsonb,
        4
    )
ON CONFLICT (slug) DO NOTHING;

-- ============================================
-- Table: subscriptions
-- Abonnements actifs des utilisateurs
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Référence utilisateur
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Référence plan
    plan_id UUID NOT NULL REFERENCES plans(id),
    
    -- Statut de l'abonnement
    status VARCHAR(20) DEFAULT 'active' CHECK (
        status IN ('active', 'canceled', 'past_due', 'trialing', 'paused')
    ),
    
    -- Période de facturation
    billing_period VARCHAR(10) DEFAULT 'monthly' CHECK (
        billing_period IN ('monthly', 'yearly')
    ),
    
    -- ID Stripe (pour synchronisation)
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    
    -- Dates de la période courante
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 month',
    
    -- Date d'annulation (si applicable)
    canceled_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Un seul abonnement actif par utilisateur
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_user_active 
ON subscriptions(user_id) 
WHERE status = 'active';

-- Index Stripe pour webhooks
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe 
ON subscriptions(stripe_subscription_id);

-- Trigger updated_at
CREATE TRIGGER trigger_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Table: usage_records
-- Tracking de l'usage pour facturation
-- ============================================
CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Référence utilisateur
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Référence subscription (pour la période)
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Période (format YYYY-MM)
    period VARCHAR(7) NOT NULL,
    
    -- Compteurs d'usage
    requests_count INT DEFAULT 0,
    documents_count INT DEFAULT 0,
    api_keys_count INT DEFAULT 0,
    
    -- Overage (requêtes au-delà du quota)
    overage_requests INT DEFAULT 0,
    overage_amount_cents INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Un seul record par user/période
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_records_user_period 
ON usage_records(user_id, period);

-- Trigger updated_at
CREATE TRIGGER trigger_usage_records_updated_at
    BEFORE UPDATE ON usage_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Modification des tables existantes: Ajout user_id
-- ============================================

-- Ajouter user_id à api_keys
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Ajouter user_id à documents
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Ajouter user_id à conversations
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Index pour requêtes par user
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- ============================================
-- Créer l'utilisateur legacy pour migration
-- ============================================
INSERT INTO users (id, email, name, provider, role, email_verified)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'legacy@rag-platform.local',
    'Legacy User',
    'system',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Assigner le plan Free à l'utilisateur legacy
INSERT INTO subscriptions (user_id, plan_id, status, billing_period)
SELECT 
    '00000000-0000-0000-0000-000000000001',
    p.id,
    'active',
    'monthly'
FROM plans p 
WHERE p.slug = 'free'
ON CONFLICT DO NOTHING;

-- ============================================
-- Migrer les données existantes vers legacy user
-- ============================================
UPDATE api_keys 
SET user_id = '00000000-0000-0000-0000-000000000001' 
WHERE user_id IS NULL;

UPDATE documents 
SET user_id = '00000000-0000-0000-0000-000000000001' 
WHERE user_id IS NULL;

UPDATE conversations 
SET user_id = '00000000-0000-0000-0000-000000000001' 
WHERE user_id IS NULL;

-- ============================================
-- Row Level Security (RLS) Policies
-- ============================================

-- Users: chacun voit seulement son profil
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON users
    FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY users_update_own ON users
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Service role peut tout faire
CREATE POLICY users_service_role ON users
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- API Keys: isolation par user_id
CREATE POLICY api_keys_user_isolation ON api_keys
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Documents: isolation par user_id
CREATE POLICY documents_user_isolation ON documents
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Conversations: isolation par user_id
CREATE POLICY conversations_user_isolation ON conversations
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Subscriptions: voir seulement les siennes
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscriptions_user_isolation ON subscriptions
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY subscriptions_service_role ON subscriptions
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- Usage records: voir seulement les siennes
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_records_user_isolation ON usage_records
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY usage_records_service_role ON usage_records
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- Plans: lecture publique
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY plans_read_all ON plans
    FOR SELECT
    TO authenticated, anon
    USING (TRUE);

CREATE POLICY plans_service_role ON plans
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- ============================================
-- Fonctions utilitaires
-- ============================================

-- Fonction: get_user_usage
-- Récupère l'usage du mois en cours pour un utilisateur
CREATE OR REPLACE FUNCTION get_user_usage(p_user_id UUID)
RETURNS TABLE (
    requests_count INT,
    documents_count INT,
    api_keys_count INT,
    requests_limit INT,
    documents_limit INT,
    api_keys_limit INT,
    overage_requests INT,
    plan_slug VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_period VARCHAR(7);
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    RETURN QUERY
    SELECT 
        COALESCE(ur.requests_count, 0),
        COALESCE(ur.documents_count, 0),
        COALESCE(ur.api_keys_count, 0),
        p.requests_per_month,
        p.documents_limit,
        p.api_keys_limit,
        COALESCE(ur.overage_requests, 0),
        p.slug
    FROM users u
    JOIN subscriptions s ON s.user_id = u.id AND s.status = 'active'
    JOIN plans p ON p.id = s.plan_id
    LEFT JOIN usage_records ur ON ur.user_id = u.id AND ur.period = v_period
    WHERE u.id = p_user_id;
END;
$$;

-- Fonction: increment_user_requests
-- Incrémente le compteur de requêtes et calcule l'overage
CREATE OR REPLACE FUNCTION increment_user_requests(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_period VARCHAR(7);
    v_usage RECORD;
    v_plan RECORD;
    v_subscription_id UUID;
    v_plan_id UUID;
    v_is_over_quota BOOLEAN;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Récupérer le plan et subscription
    SELECT s.id, s.plan_id INTO v_subscription_id, v_plan_id
    FROM subscriptions s
    WHERE s.user_id = p_user_id AND s.status = 'active';
    
    IF v_subscription_id IS NULL THEN
        RETURN jsonb_build_object('error', 'no_active_subscription');
    END IF;

    SELECT * INTO v_plan FROM plans WHERE id = v_plan_id;
    
    -- Upsert usage record
    INSERT INTO usage_records (user_id, subscription_id, period, requests_count)
    VALUES (p_user_id, v_subscription_id, v_period, 1)
    ON CONFLICT (user_id, period) 
    DO UPDATE SET 
        requests_count = usage_records.requests_count + 1,
        updated_at = NOW()
    RETURNING * INTO v_usage;
    
    -- Vérifier si au-delà du quota (-1 = illimité)
    v_is_over_quota := v_plan.requests_per_month > 0 
        AND v_usage.requests_count > v_plan.requests_per_month;
    
    -- Calculer l'overage si applicable
    IF v_is_over_quota AND v_plan.overage_price_cents > 0 THEN
        UPDATE usage_records 
        SET 
            overage_requests = requests_count - v_plan.requests_per_month,
            overage_amount_cents = (requests_count - v_plan.requests_per_month) * v_plan.overage_price_cents
        WHERE id = v_usage.id;
    END IF;
    
    RETURN jsonb_build_object(
        'requests_count', v_usage.requests_count,
        'requests_limit', v_plan.requests_per_month,
        'is_over_quota', v_is_over_quota,
        'overage_price_cents', v_plan.overage_price_cents
    );
END;
$$;

-- Fonction: check_user_limits
-- Vérifie si l'utilisateur peut faire une action (requête, créer doc, créer clé)
CREATE OR REPLACE FUNCTION check_user_limits(
    p_user_id UUID,
    p_action VARCHAR(20) DEFAULT 'request'
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_usage RECORD;
    v_allowed BOOLEAN;
    v_reason VARCHAR(100);
BEGIN
    -- Récupérer l'usage et les limites
    SELECT * INTO v_usage FROM get_user_usage(p_user_id);
    
    IF v_usage IS NULL THEN
        RETURN jsonb_build_object('allowed', FALSE, 'reason', 'no_subscription');
    END IF;
    
    -- Vérifier selon l'action
    CASE p_action
        WHEN 'request' THEN
            -- -1 = illimité, sinon vérifier le quota + tolérance overage
            IF v_usage.requests_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_usage.plan_slug = 'free' AND v_usage.requests_count >= v_usage.requests_limit THEN
                -- Free plan: hard limit, pas d'overage
                v_allowed := FALSE;
                v_reason := 'quota_exceeded';
            ELSE
                -- Plans payants: overage autorisé
                v_allowed := TRUE;
            END IF;
            
        WHEN 'document' THEN
            IF v_usage.documents_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_usage.documents_count >= v_usage.documents_limit THEN
                v_allowed := FALSE;
                v_reason := 'documents_limit_reached';
            ELSE
                v_allowed := TRUE;
            END IF;
            
        WHEN 'api_key' THEN
            IF v_usage.api_keys_limit = -1 THEN
                v_allowed := TRUE;
            ELSIF v_usage.api_keys_count >= v_usage.api_keys_limit THEN
                v_allowed := FALSE;
                v_reason := 'api_keys_limit_reached';
            ELSE
                v_allowed := TRUE;
            END IF;
            
        ELSE
            v_allowed := FALSE;
            v_reason := 'unknown_action';
    END CASE;
    
    RETURN jsonb_build_object(
        'allowed', v_allowed,
        'reason', v_reason,
        'usage', jsonb_build_object(
            'requests', v_usage.requests_count,
            'documents', v_usage.documents_count,
            'api_keys', v_usage.api_keys_count
        ),
        'limits', jsonb_build_object(
            'requests', v_usage.requests_limit,
            'documents', v_usage.documents_limit,
            'api_keys', v_usage.api_keys_limit
        )
    );
END;
$$;

-- ============================================
-- Mettre à jour validate_api_key pour inclure user_id
-- ============================================
DROP FUNCTION IF EXISTS validate_api_key(VARCHAR, VARCHAR);

CREATE OR REPLACE FUNCTION validate_api_key(
    p_key_hash VARCHAR(64),
    p_client_ip VARCHAR(45) DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    name VARCHAR(100),
    scopes TEXT[],
    rate_limit_per_minute INT,
    is_valid BOOLEAN,
    rejection_reason VARCHAR(50),
    user_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_key RECORD;
    v_current_month VARCHAR(7);
    v_user_limits JSONB;
BEGIN
    v_current_month := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Rechercher la clé
    SELECT * INTO v_key
    FROM api_keys ak
    WHERE ak.key_hash = p_key_hash;
    
    -- Clé non trouvée
    IF v_key IS NULL THEN
        RETURN QUERY SELECT 
            NULL::UUID, NULL::VARCHAR, NULL::TEXT[], 0, FALSE, 'invalid_key'::VARCHAR, NULL::UUID;
        RETURN;
    END IF;
    
    -- Clé désactivée
    IF NOT v_key.is_active THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_revoked'::VARCHAR, v_key.user_id;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_expired'::VARCHAR, v_key.user_id;
        RETURN;
    END IF;
    
    -- Vérifier les limites utilisateur (si user_id existe)
    IF v_key.user_id IS NOT NULL THEN
        v_user_limits := check_user_limits(v_key.user_id, 'request');
        
        IF NOT (v_user_limits->>'allowed')::BOOLEAN THEN
            RETURN QUERY SELECT 
                v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
                FALSE, (v_user_limits->>'reason')::VARCHAR, v_key.user_id;
            RETURN;
        END IF;
        
        -- Incrémenter l'usage
        PERFORM increment_user_requests(v_key.user_id);
    END IF;
    
    -- Reset mensuel si nécessaire (pour rate limiting par clé)
    IF v_key.usage_reset_month IS NULL OR v_key.usage_reset_month != v_current_month THEN
        UPDATE api_keys SET 
            monthly_usage = 0,
            usage_reset_month = v_current_month
        WHERE api_keys.id = v_key.id;
    END IF;
    
    -- Mettre à jour l'utilisation
    UPDATE api_keys SET 
        last_used_at = NOW(),
        last_used_ip = p_client_ip,
        monthly_usage = monthly_usage + 1
    WHERE api_keys.id = v_key.id;
    
    -- Clé valide
    RETURN QUERY SELECT 
        v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
        TRUE, NULL::VARCHAR, v_key.user_id;
END;
$$;

-- ============================================
-- Commentaires
-- ============================================
COMMENT ON TABLE users IS 'Utilisateurs de la plateforme (OAuth Google/GitHub)';
COMMENT ON TABLE plans IS 'Plans d''abonnement disponibles (Free, Pro, Scale, Enterprise)';
COMMENT ON TABLE subscriptions IS 'Abonnements actifs des utilisateurs';
COMMENT ON TABLE usage_records IS 'Tracking de l''usage mensuel pour facturation';
COMMENT ON FUNCTION get_user_usage IS 'Récupère l''usage du mois en cours pour un utilisateur';
COMMENT ON FUNCTION increment_user_requests IS 'Incrémente le compteur de requêtes et calcule l''overage';
COMMENT ON FUNCTION check_user_limits IS 'Vérifie si l''utilisateur peut faire une action';
