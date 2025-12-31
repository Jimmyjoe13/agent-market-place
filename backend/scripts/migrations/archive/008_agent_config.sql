-- ============================================
-- Migration 008: Agent Configuration
-- RAG Agent IA - Agent-as-a-Service Model
-- ============================================
-- 
-- Cette migration transforme le modèle API Key en Agent configurable.
-- Chaque clé API représente désormais un agent avec :
--   - Modèle LLM personnalisable (Mistral, OpenAI, Deepseek)
--   - Prompt système customisé
--   - RAG activable/désactivable
--   - Documents isolés par agent
--
-- Breaking Changes: Aucun (valeurs par défaut appliquées)
-- ============================================

-- ============================================
-- 1. Extension table api_keys avec config agent
-- ============================================

-- Modèle LLM utilisé par l'agent
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS model_id VARCHAR(50) DEFAULT 'mistral-large-latest';

-- Prompt système personnalisé (NULL = prompt par défaut)
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS system_prompt TEXT;

-- Activation du RAG pour cet agent
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS rag_enabled BOOLEAN DEFAULT TRUE;

-- Nom de l'agent (affiché dans le dashboard)
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS agent_name VARCHAR(100);

-- Index pour filtrage par modèle (analytics)
CREATE INDEX IF NOT EXISTS idx_api_keys_model_id 
ON api_keys(model_id) 
WHERE is_active = TRUE;

-- ============================================
-- 2. Isolation des documents par agent
-- ============================================

-- Ajout FK vers api_keys avec suppression cascade
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE;

-- Index pour recherche vectorielle filtrée par agent
CREATE INDEX IF NOT EXISTS idx_documents_api_key_id 
ON documents(api_key_id) 
WHERE api_key_id IS NOT NULL;

-- ============================================
-- 3. Mise à jour fonction match_documents
-- ============================================

-- Suppression anciennes versions (toutes les signatures existantes)
-- Migration 002: signature avec jsonb
DROP FUNCTION IF EXISTS match_documents(vector(1024), float, int, varchar(50), jsonb);
-- Migration 006: signature avec user_id
DROP FUNCTION IF EXISTS match_documents(vector(1024), float, int, varchar, uuid);

-- Nouvelle version avec filtre api_key_id
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter_source_type text DEFAULT NULL,
    filter_user_id uuid DEFAULT NULL,
    filter_api_key_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content text,
    source_type text,
    source_id text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
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
    FROM documents d
    WHERE 
        1 - (d.embedding <=> query_embedding) > match_threshold
        AND (filter_source_type IS NULL OR d.source_type = filter_source_type)
        AND (filter_user_id IS NULL OR d.user_id = filter_user_id)
        AND (filter_api_key_id IS NULL OR d.api_key_id = filter_api_key_id)
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- 4. Mise à jour fonction validate_api_key
-- ============================================

-- Suppression ancienne version (signature Migration 004)
DROP FUNCTION IF EXISTS validate_api_key(VARCHAR(64), VARCHAR(45)) CASCADE;

-- Nouvelle version retournant aussi la config agent
CREATE OR REPLACE FUNCTION validate_api_key(
    p_key_hash VARCHAR(64),
    p_client_ip VARCHAR(45) DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    name VARCHAR(100),
    scopes TEXT[],
    rate_limit_per_minute INT,
    is_valid BOOLEAN,
    rejection_reason VARCHAR(50),
    -- Nouvelles colonnes agent config
    model_id VARCHAR(50),
    system_prompt TEXT,
    rag_enabled BOOLEAN,
    agent_name VARCHAR(100)
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
            NULL::UUID, NULL::UUID, NULL::VARCHAR, NULL::TEXT[], 0, FALSE, 'invalid_key'::VARCHAR,
            NULL::VARCHAR, NULL::TEXT, NULL::BOOLEAN, NULL::VARCHAR;
        RETURN;
    END IF;
    
    -- Clé désactivée
    IF NOT v_key.is_active THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.user_id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_revoked'::VARCHAR,
            v_key.model_id, v_key.system_prompt, v_key.rag_enabled, v_key.agent_name;
        RETURN;
    END IF;
    
    -- Clé expirée
    IF v_key.expires_at IS NOT NULL AND v_key.expires_at < NOW() THEN
        RETURN QUERY SELECT 
            v_key.id, v_key.user_id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'key_expired'::VARCHAR,
            v_key.model_id, v_key.system_prompt, v_key.rag_enabled, v_key.agent_name;
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
            v_key.id, v_key.user_id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
            FALSE, 'quota_exceeded'::VARCHAR,
            v_key.model_id, v_key.system_prompt, v_key.rag_enabled, v_key.agent_name;
        RETURN;
    END IF;
    
    -- Mettre à jour l'utilisation
    UPDATE api_keys SET 
        last_used_at = NOW(),
        last_used_ip = p_client_ip,
        monthly_usage = monthly_usage + 1
    WHERE api_keys.id = v_key.id;
    
    -- Clé valide avec config agent
    RETURN QUERY SELECT 
        v_key.id, v_key.user_id, v_key.name, v_key.scopes, v_key.rate_limit_per_minute, 
        TRUE, NULL::VARCHAR,
        v_key.model_id, v_key.system_prompt, v_key.rag_enabled, v_key.agent_name;
END;
$$;

-- ============================================
-- 5. Table usage_logs étendue (tokens tracking)
-- ============================================

-- Ajout colonnes pour tracking tokens
ALTER TABLE api_key_usage_logs
ADD COLUMN IF NOT EXISTS prompt_tokens INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS completion_tokens INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS model_used VARCHAR(50);

-- ============================================
-- Commentaires
-- ============================================
COMMENT ON COLUMN api_keys.model_id IS 'Identifiant du modèle LLM utilisé (ex: mistral-large-latest, gpt-4o, deepseek-chat)';
COMMENT ON COLUMN api_keys.system_prompt IS 'Prompt système personnalisé pour cet agent';
COMMENT ON COLUMN api_keys.rag_enabled IS 'Active la recherche dans les documents vectorisés';
COMMENT ON COLUMN api_keys.agent_name IS 'Nom affiché de l''agent dans le dashboard';
COMMENT ON COLUMN documents.api_key_id IS 'Agent propriétaire du document (isolation multi-agent)';
COMMENT ON FUNCTION match_documents IS 'Recherche vectorielle avec filtres user_id, source_type et api_key_id';
