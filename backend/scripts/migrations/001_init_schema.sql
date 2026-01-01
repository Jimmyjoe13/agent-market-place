-- ============================================
-- Migration 001: Schema Consolidé - Agent Market Place
-- Date: 2025-12-31
-- Version: 2.0.0
-- ============================================
-- 
-- Cette migration crée le schéma complet de la base de données
-- en partant de zéro. Elle remplace les migrations 001-012.
--
-- ARCHITECTURE:
--   profiles    -> Extension de auth.users (trigger automatique)
--   plans       -> Plans d'abonnement (Free, Pro, Enterprise)
--   subscriptions -> Abonnements utilisateurs avec Stripe
--   agents      -> Configuration des agents IA (modèle, prompt, RAG)
--   api_keys    -> Authentification API (hash, scopes, limites)
--   documents   -> Documents vectorisés pour RAG
--   document_jobs -> Jobs d'ingestion asynchrones
--   conversations -> Historique des conversations
--   usage_records -> Tracking mensuel pour facturation
--
-- EXÉCUTION:
--   1. Supprimer toutes les tables existantes si migration
--   2. Exécuter ce script dans Supabase SQL Editor
--   3. Les triggers créeront automatiquement les profils
-- ============================================

-- ============================================
-- 0. Extensions requises
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================
-- 1. Table: profiles (Extension de auth.users)
-- ============================================
-- Liée directement à auth.users via FK cascade
-- Créée automatiquement par trigger lors de l'inscription
-- ============================================
CREATE TABLE IF NOT EXISTS public.profiles (
    -- ID identique à auth.users.id
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    
    -- Identité
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    
    -- Rôle et permissions
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'superadmin')),
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Stripe integration
    stripe_customer_id TEXT,
    plan_slug TEXT DEFAULT 'free',
    subscription_status TEXT DEFAULT 'inactive',
    
    -- BYOK (Bring Your Own Key) - Chiffré avec AES-256
    provider_keys_encrypted JSONB DEFAULT '{}',
    
    -- OAuth provider info
    provider TEXT DEFAULT 'email',
    provider_id TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Index pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_stripe ON public.profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select_own" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "profiles_service_role" ON public.profiles
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 2. Table: plans (Plans d'abonnement)
-- ============================================
CREATE TABLE IF NOT EXISTS public.plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identifiant unique
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Tarification (en centimes)
    price_monthly_cents INT NOT NULL DEFAULT 0,
    price_yearly_cents INT NOT NULL DEFAULT 0,
    
    -- Quotas
    requests_per_month INT NOT NULL DEFAULT 100,
    api_keys_limit INT NOT NULL DEFAULT 1,
    documents_limit INT NOT NULL DEFAULT 10,
    agents_limit INT NOT NULL DEFAULT 1,
    
    -- Overage
    overage_price_cents NUMERIC(10, 4) DEFAULT 0,
    
    -- Features JSON
    features JSONB DEFAULT '[]',
    
    -- Affichage
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Stripe Price IDs
    stripe_price_id_monthly TEXT,
    stripe_price_id_yearly TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS (lecture publique)
ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "plans_read_all" ON public.plans
    FOR SELECT TO authenticated, anon
    USING (TRUE);

CREATE POLICY "plans_admin_write" ON public.plans
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- Insertion des plans par défaut
INSERT INTO public.plans (slug, name, description, price_monthly_cents, price_yearly_cents, requests_per_month, api_keys_limit, documents_limit, agents_limit, features, display_order)
VALUES 
    ('free', 'Free', 'Parfait pour découvrir', 0, 0, 100, 1, 10, 1, 
     '["100 requêtes/mois", "1 agent", "10 documents", "Support communauté"]', 1),
    ('pro', 'Pro', 'Pour les développeurs', 3999, 42988, 5000, 5, 100, 5, 
     '["5000 requêtes/mois", "5 agents", "100 documents", "Support email", "BYOK"]', 2),
    ('enterprise', 'Enterprise', 'Solution sur mesure', 0, 0, -1, -1, -1, -1, 
     '["Requêtes illimitées", "Agents illimités", "SSO/SAML", "SLA 99.9%"]', 3)
ON CONFLICT (slug) DO NOTHING;

-- ============================================
-- 3. Table: subscriptions (Abonnements)
-- ============================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES public.plans(id),
    
    -- Statut
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'paused')),
    billing_period TEXT DEFAULT 'monthly' CHECK (billing_period IN ('monthly', 'yearly')),
    
    -- Stripe
    stripe_subscription_id TEXT,
    stripe_customer_id TEXT,
    
    -- Période
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 month',
    
    -- Annulation
    canceled_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index unique pour un seul abonnement actif par user
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_user_active 
ON public.subscriptions(user_id) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe 
ON public.subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;

-- RLS
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "subscriptions_user_own" ON public.subscriptions
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "subscriptions_service_role" ON public.subscriptions
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 4. Table: agents (Configuration des agents IA)
-- ============================================
-- Séparé de api_keys pour clarté
-- Un agent = une configuration LLM + RAG
-- Peut avoir plusieurs api_keys
-- ============================================
CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Propriétaire
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- Identité
    name TEXT NOT NULL,
    description TEXT,
    
    -- Configuration LLM
    model_id TEXT NOT NULL DEFAULT 'mistral-large-latest',
    system_prompt TEXT,
    temperature NUMERIC(3, 2) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    
    -- RAG
    rag_enabled BOOLEAN DEFAULT TRUE,
    
    -- Budget & Limites
    max_monthly_tokens BIGINT DEFAULT 0, -- 0 = illimité
    max_daily_requests INT DEFAULT 0,    -- 0 = illimité
    tokens_used_this_month BIGINT DEFAULT 0,
    requests_today INT DEFAULT 0,
    usage_reset_month TEXT,
    daily_reset_date DATE DEFAULT CURRENT_DATE,
    
    -- Statut
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_user ON public.agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_active ON public.agents(user_id, is_active) WHERE is_active = TRUE;

-- RLS
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agents_user_own" ON public.agents
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "agents_service_role" ON public.agents
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 5. Table: api_keys (Authentification API)
-- ============================================
-- Simplifiée: uniquement auth, liée à un agent
-- ============================================
CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- Identité
    name TEXT NOT NULL,
    
    -- Authentification
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL, -- ex: "rag_a1b2c3d4"
    
    -- Permissions
    scopes TEXT[] DEFAULT ARRAY['query'],
    
    -- Rate limiting (par clé)
    rate_limit_per_minute INT DEFAULT 60,
    
    -- Statut
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    
    -- Tracking
    last_used_at TIMESTAMPTZ,
    last_used_ip TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON public.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_agent ON public.api_keys(agent_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON public.api_keys(is_active) WHERE is_active = TRUE;

-- RLS
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "api_keys_user_own" ON public.api_keys
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "api_keys_service_role" ON public.api_keys
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 6. Table: documents (Documents vectorisés)
-- ============================================
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    
    -- Contenu
    content TEXT NOT NULL,
    embedding VECTOR(1024), -- Mistral Embed dimensions
    
    -- Métadonnées
    metadata JSONB DEFAULT '{}',
    source_type TEXT NOT NULL, -- github, pdf, text, url
    source_id TEXT,
    content_hash TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index vectoriel HNSW pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_documents_embedding 
ON public.documents USING hnsw(embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_documents_user ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_agent ON public.documents(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_source ON public.documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON public.documents USING gin(metadata);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_hash ON public.documents(content_hash) WHERE content_hash IS NOT NULL;

-- RLS
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents_user_own" ON public.documents
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "documents_service_role" ON public.documents
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 7. Table: document_jobs (Jobs d'ingestion)
-- ============================================
CREATE TABLE IF NOT EXISTS public.document_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    document_id UUID REFERENCES public.documents(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- Statut
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Progression
    progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    chunks_total INT DEFAULT 0,
    chunks_processed INT DEFAULT 0,
    
    -- Source
    source_filename TEXT,
    source_type TEXT,
    source_size_bytes BIGINT,
    
    -- Erreurs
    error_message TEXT,
    error_code TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    -- Webhook
    webhook_url TEXT,
    webhook_secret TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_jobs_user ON public.document_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_document_jobs_agent ON public.document_jobs(agent_id);
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON public.document_jobs(status) WHERE status IN ('pending', 'processing');

-- RLS
ALTER TABLE public.document_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "document_jobs_user_own" ON public.document_jobs
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "document_jobs_service_role" ON public.document_jobs
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 8. Table: conversations (Historique chat)
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES public.agents(id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,
    
    -- Session
    session_id TEXT NOT NULL,
    
    -- Contenu
    user_query TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    
    -- Contexte RAG
    context_sources JSONB DEFAULT '[]',
    
    -- Métadonnées LLM
    metadata JSONB DEFAULT '{}',
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    model_used TEXT,
    latency_ms INT,
    
    -- Feedback
    feedback_score INT CHECK (feedback_score IS NULL OR (feedback_score >= 1 AND feedback_score <= 5)),
    feedback_comment TEXT,
    
    -- Training
    flagged_for_training BOOLEAN DEFAULT FALSE,
    training_processed_at TIMESTAMPTZ,
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON public.conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_agent ON public.conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON public.conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_feedback ON public.conversations(feedback_score) WHERE feedback_score IS NOT NULL;

-- RLS
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "conversations_user_own" ON public.conversations
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "conversations_service_role" ON public.conversations
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 9. Table: usage_records (Facturation mensuelle)
-- ============================================
CREATE TABLE IF NOT EXISTS public.usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE SET NULL,
    
    -- Période YYYY-MM
    period TEXT NOT NULL,
    
    -- Compteurs
    requests_count INT DEFAULT 0,
    documents_count INT DEFAULT 0,
    api_keys_count INT DEFAULT 0,
    agents_count INT DEFAULT 0,
    tokens_used BIGINT DEFAULT 0,
    
    -- Overage
    overage_requests INT DEFAULT 0,
    overage_amount_cents INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_records_user_period 
ON public.usage_records(user_id, period);

-- RLS
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "usage_records_user_own" ON public.usage_records
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY "usage_records_service_role" ON public.usage_records
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- 10. Triggers: Auto-création profile
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, provider)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_app_meta_data->>'provider', 'email')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Supprimer le trigger s'il existe déjà
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- 11. Triggers: Updated_at automatique
-- ============================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Appliquer à toutes les tables avec updated_at
CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_plans_updated_at
    BEFORE UPDATE ON public.plans
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_agents_updated_at
    BEFORE UPDATE ON public.agents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_api_keys_updated_at
    BEFORE UPDATE ON public.api_keys
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON public.documents
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_document_jobs_updated_at
    BEFORE UPDATE ON public.document_jobs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER trigger_usage_records_updated_at
    BEFORE UPDATE ON public.usage_records
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================
-- 12. Fonction: match_documents (Recherche RAG)
-- ============================================
CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding VECTOR(1024),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    filter_agent_id UUID DEFAULT NULL,
    filter_source_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    source_type TEXT,
    source_id TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.source_type,
        d.source_id,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM public.documents d
    WHERE 
        1 - (d.embedding <=> query_embedding) > match_threshold
        AND (filter_user_id IS NULL OR d.user_id = filter_user_id)
        AND (filter_agent_id IS NULL OR d.agent_id = filter_agent_id)
        AND (filter_source_type IS NULL OR d.source_type = filter_source_type)
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- 13. Fonction: validate_api_key
-- ============================================
CREATE OR REPLACE FUNCTION public.validate_api_key(
    p_key_hash TEXT,
    p_client_ip TEXT DEFAULT NULL
)
RETURNS TABLE (
    key_id UUID,
    agent_id UUID,
    user_id UUID,
    name TEXT,
    scopes TEXT[],
    rate_limit_per_minute INT,
    is_valid BOOLEAN,
    rejection_reason TEXT,
    -- Agent config
    model_id TEXT,
    system_prompt TEXT,
    rag_enabled BOOLEAN,
    agent_name TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_key RECORD;
    v_agent RECORD;
BEGIN
    -- Rechercher la clé
    SELECT * INTO v_key
    FROM public.api_keys ak
    WHERE ak.key_hash = p_key_hash;
    
    -- Clé non trouvée
    IF v_key IS NULL THEN
        RETURN QUERY SELECT 
            NULL::UUID, NULL::UUID, NULL::UUID, NULL::TEXT, 
            NULL::TEXT[], 0, FALSE, 'invalid_key'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Clé désactivée
    IF NOT v_key.is_active THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.agent_id, v_key.user_id, v_key.name,
            v_key.scopes, v_key.rate_limit_per_minute, FALSE, 'key_revoked'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.agent_id, v_key.user_id, v_key.name,
            v_key.scopes, v_key.rate_limit_per_minute, FALSE, 'key_expired'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Récupérer la config agent
    SELECT * INTO v_agent
    FROM public.agents a
    WHERE a.id = v_key.agent_id AND a.is_active = TRUE;
    
    IF v_agent IS NULL THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.agent_id, v_key.user_id, v_key.name,
            v_key.scopes, v_key.rate_limit_per_minute, FALSE, 'agent_inactive'::TEXT,
            NULL::TEXT, NULL::TEXT, NULL::BOOLEAN, NULL::TEXT;
        RETURN;
    END IF;
    
    -- Mettre à jour last_used
    UPDATE public.api_keys SET 
        last_used_at = NOW(),
        last_used_ip = p_client_ip
    WHERE api_keys.id = v_key.id;
    
    -- Clé valide
    RETURN QUERY SELECT 
        v_key.id, v_key.agent_id, v_key.user_id, v_key.name,
        v_key.scopes, v_key.rate_limit_per_minute, TRUE, NULL::TEXT,
        v_agent.model_id, v_agent.system_prompt, v_agent.rag_enabled, v_agent.name;
END;
$$;

-- ============================================
-- 14. Fonction: get_user_usage
-- ============================================
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
    plan_slug TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_period TEXT;
BEGIN
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    RETURN QUERY
    SELECT 
        COALESCE(ur.requests_count, 0)::INT,
        COALESCE(ur.documents_count, 0)::INT,
        COALESCE(ur.api_keys_count, 0)::INT,
        COALESCE(ur.agents_count, 0)::INT,
        p.requests_per_month,
        p.documents_limit,
        p.api_keys_limit,
        p.agents_limit,
        p.slug
    FROM public.profiles pr
    LEFT JOIN public.subscriptions s ON s.user_id = pr.id AND s.status = 'active'
    LEFT JOIN public.plans p ON p.id = s.plan_id
    LEFT JOIN public.usage_records ur ON ur.user_id = pr.id AND ur.period = v_period
    WHERE pr.id = p_user_id;
END;
$$;

-- ============================================
-- 15. Fonction: increment_usage
-- ============================================
CREATE OR REPLACE FUNCTION public.increment_user_usage(
    p_user_id UUID,
    p_requests INT DEFAULT 0,
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
-- 16. Vue: agent_dashboard (sécurisée)
-- ============================================
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
-- Commentaires
-- ============================================
COMMENT ON TABLE public.profiles IS 'Profils utilisateurs étendant auth.users';
COMMENT ON TABLE public.plans IS 'Plans d abonnement disponibles';
COMMENT ON TABLE public.subscriptions IS 'Abonnements actifs des utilisateurs';
COMMENT ON TABLE public.agents IS 'Configuration des agents IA';
COMMENT ON TABLE public.api_keys IS 'Clés API pour authentification';
COMMENT ON TABLE public.documents IS 'Documents vectorisés pour RAG';
COMMENT ON TABLE public.document_jobs IS 'Jobs d ingestion asynchrones';
COMMENT ON TABLE public.conversations IS 'Historique des conversations';
COMMENT ON TABLE public.usage_records IS 'Tracking mensuel pour facturation';

COMMENT ON FUNCTION public.match_documents IS 'Recherche vectorielle avec filtres';
COMMENT ON FUNCTION public.validate_api_key IS 'Valide une clé API et retourne la config agent';
COMMENT ON FUNCTION public.get_user_usage IS 'Récupère l usage du mois en cours';
COMMENT ON FUNCTION public.increment_user_usage IS 'Incrémente les compteurs d usage';
