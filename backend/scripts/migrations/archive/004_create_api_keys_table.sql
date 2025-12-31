-- ============================================
-- Migration 004: Create API Keys Table
-- RAG Agent IA - API Authentication System
-- ============================================
-- 
-- Cette migration crée le système d'authentification par clé API.
-- Les clés sont stockées sous forme de hash SHA-256 pour la sécurité.
-- Seul le préfixe (8 caractères) est visible après création.
--
-- Usage:
--   1. Exécuter ce script dans Supabase SQL Editor
--   2. Configurer API_MASTER_KEY dans .env
--   3. Créer des clés via POST /api/v1/keys
-- ============================================

-- ============================================
-- Table: api_keys
-- Stocke les clés API pour l'authentification
-- ============================================
CREATE TABLE IF NOT EXISTS api_keys (
    -- Identifiant unique
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Nom descriptif de la clé (ex: "Production App", "Test Key")
    name VARCHAR(100) NOT NULL,
    
    -- Hash SHA-256 de la clé complète (pour validation)
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Préfixe visible de la clé (ex: "rag_a1b2c3d4")
    -- Permet d'identifier la clé sans révéler le secret
    key_prefix VARCHAR(12) NOT NULL,
    
    -- Permissions accordées à cette clé
    -- Valeurs possibles: 'query', 'ingest', 'feedback', 'admin'
    scopes TEXT[] DEFAULT ARRAY['query']::TEXT[],
    
    -- Limite de requêtes par minute (0 = illimité)
    rate_limit_per_minute INT DEFAULT 100,
    
    -- Quota mensuel de requêtes (0 = illimité)
    monthly_quota INT DEFAULT 0,
    
    -- Compteur de requêtes du mois en cours
    monthly_usage INT DEFAULT 0,
    
    -- Mois du compteur (pour reset automatique)
    usage_reset_month VARCHAR(7),
    
    -- Statut de la clé
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Date d'expiration (NULL = jamais)
    expires_at TIMESTAMPTZ,
    
    -- Dernière utilisation
    last_used_at TIMESTAMPTZ,
    
    -- Adresse IP de la dernière requête
    last_used_ip VARCHAR(45),
    
    -- Métadonnées additionnelles (owner, team, etc.)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Table: api_key_usage_logs
-- Historique détaillé de l'utilisation des clés
-- ============================================
CREATE TABLE IF NOT EXISTS api_key_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Référence à la clé API
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    
    -- Endpoint appelé
    endpoint VARCHAR(200) NOT NULL,
    
    -- Méthode HTTP
    method VARCHAR(10) NOT NULL,
    
    -- Code de réponse HTTP
    status_code INT,
    
    -- Temps de réponse en millisecondes
    response_time_ms INT,
    
    -- Adresse IP du client
    client_ip VARCHAR(45),
    
    -- User-Agent du client
    user_agent VARCHAR(500),
    
    -- Timestamp de la requête
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Indexes pour optimiser les performances
-- ============================================

-- Index sur le hash pour validation rapide
CREATE INDEX IF NOT EXISTS idx_api_keys_hash 
ON api_keys(key_hash);

-- Index sur les clés actives non expirées
CREATE INDEX IF NOT EXISTS idx_api_keys_active 
ON api_keys(is_active, expires_at)
WHERE is_active = TRUE;

-- Index sur les logs par clé et date
CREATE INDEX IF NOT EXISTS idx_usage_logs_key_date 
ON api_key_usage_logs(api_key_id, created_at DESC);

-- Index pour nettoyage des vieux logs
CREATE INDEX IF NOT EXISTS idx_usage_logs_date 
ON api_key_usage_logs(created_at);

-- ============================================
-- Trigger pour mise à jour automatique
-- ============================================
CREATE TRIGGER trigger_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Fonction: validate_api_key
-- Valide une clé API et met à jour last_used_at
-- ============================================
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
    rejection_reason VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_key RECORD;
    v_current_month VARCHAR(7);
BEGIN
    v_current_month := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Rechercher la clé
    SELECT * INTO v_key
    FROM api_keys ak
    WHERE ak.key_hash = p_key_hash;
    
    -- Clé non trouvée
    IF v_key IS NULL THEN
        RETURN QUERY SELECT 
            NULL::UUID, NULL::VARCHAR, NULL::TEXT[], 0, FALSE, 'invalid_key'::VARCHAR;
        RETURN;
    END IF;
    
    -- Clé désactivée
    IF NOT v_key.is_active THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_revoked'::VARCHAR;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_expired'::VARCHAR;
        RETURN;
    END IF;
    
    -- Reset mensuel si nécessaire
    IF v_key.usage_reset_month IS NULL OR v_key.usage_reset_month != v_current_month THEN
        UPDATE api_keys SET 
            monthly_usage = 0,
            usage_reset_month = v_current_month
        WHERE api_keys.id = v_key.id;
    END IF;
    
    -- Vérifier quota mensuel
    IF v_key.monthly_quota > 0 AND v_key.monthly_usage >= v_key.monthly_quota THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'quota_exceeded'::VARCHAR;
        RETURN;
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
        TRUE, NULL::VARCHAR;
END;
$$;

-- ============================================
-- Fonction: get_api_key_stats
-- Statistiques d'utilisation d'une clé
-- ============================================
CREATE OR REPLACE FUNCTION get_api_key_stats(
    p_key_id UUID,
    p_days INT DEFAULT 30
)
RETURNS TABLE (
    total_requests BIGINT,
    avg_response_time NUMERIC,
    error_rate NUMERIC,
    requests_by_endpoint JSONB,
    requests_by_day JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT
            COUNT(*) AS total,
            ROUND(AVG(response_time_ms)::NUMERIC, 2) AS avg_time,
            ROUND(
                (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::NUMERIC / 
                NULLIF(COUNT(*), 0) * 100), 2
            ) AS errors
        FROM api_key_usage_logs
        WHERE api_key_id = p_key_id
        AND created_at >= NOW() - (p_days || ' days')::INTERVAL
    ),
    by_endpoint AS (
        SELECT jsonb_object_agg(endpoint, cnt) AS data
        FROM (
            SELECT endpoint, COUNT(*) AS cnt
            FROM api_key_usage_logs
            WHERE api_key_id = p_key_id
            AND created_at >= NOW() - (p_days || ' days')::INTERVAL
            GROUP BY endpoint
        ) sub
    ),
    by_day AS (
        SELECT jsonb_object_agg(day::TEXT, cnt) AS data
        FROM (
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM api_key_usage_logs
            WHERE api_key_id = p_key_id
            AND created_at >= NOW() - (p_days || ' days')::INTERVAL
            GROUP BY DATE(created_at)
        ) sub
    )
    SELECT 
        stats.total,
        stats.avg_time,
        stats.errors,
        COALESCE(by_endpoint.data, '{}'::jsonb),
        COALESCE(by_day.data, '{}'::jsonb)
    FROM stats, by_endpoint, by_day;
END;
$$;

-- ============================================
-- Politique RLS (Row Level Security)
-- ============================================
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_usage_logs ENABLE ROW LEVEL SECURITY;

-- Politique pour service role (accès complet)
CREATE POLICY service_role_api_keys ON api_keys
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY service_role_usage_logs ON api_key_usage_logs
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- ============================================
-- Commentaires
-- ============================================
COMMENT ON TABLE api_keys IS 'Clés API pour l''authentification du système RAG';
COMMENT ON TABLE api_key_usage_logs IS 'Logs détaillés d''utilisation des clés API';
COMMENT ON FUNCTION validate_api_key IS 'Valide une clé API et retourne ses permissions';
COMMENT ON FUNCTION get_api_key_stats IS 'Retourne les statistiques d''utilisation d''une clé';
