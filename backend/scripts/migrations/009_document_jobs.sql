-- ============================================
-- Migration 009: Document Jobs & Processing Status
-- RAG Agent IA - Async Document Ingestion
-- ============================================
-- 
-- Cette migration ajoute le tracking des jobs d'ingestion de documents
-- pour permettre un traitement asynchrone avec statut de progression.
--
-- Features:
--   - Table document_jobs pour tracking des jobs
--   - Statuts: pending, processing, completed, failed
--   - Progress tracking (chunks traités/total)
--   - Support webhooks de notification
--
-- Breaking Changes: Aucun
-- ============================================

-- ============================================
-- 1. Table document_jobs pour tracking ingestion
-- ============================================

CREATE TABLE IF NOT EXISTS document_jobs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Référence au document
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Agent propriétaire
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Statut du job
    status VARCHAR(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Progression
    progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    chunks_total INT DEFAULT 0,
    chunks_processed INT DEFAULT 0,
    
    -- Métadonnées du fichier source
    source_filename VARCHAR(500),
    source_type VARCHAR(50), -- pdf, text, github, etc.
    source_size_bytes BIGINT,
    
    -- Erreurs
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    -- Webhook notification (optionnel)
    webhook_url TEXT,
    webhook_secret VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 2. Index pour performance
-- ============================================

-- Index pour recherche par agent
CREATE INDEX IF NOT EXISTS idx_document_jobs_api_key 
ON document_jobs(api_key_id);

-- Index pour recherche par user
CREATE INDEX IF NOT EXISTS idx_document_jobs_user 
ON document_jobs(user_id);

-- Index pour jobs en cours
CREATE INDEX IF NOT EXISTS idx_document_jobs_pending 
ON document_jobs(status) 
WHERE status IN ('pending', 'processing');

-- Index pour cleanup des jobs anciens
CREATE INDEX IF NOT EXISTS idx_document_jobs_created 
ON document_jobs(created_at);

-- ============================================
-- 3. Trigger pour updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_document_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_document_jobs_updated ON document_jobs;
CREATE TRIGGER trigger_document_jobs_updated
    BEFORE UPDATE ON document_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_document_jobs_updated_at();

-- ============================================
-- 4. Fonction pour créer un job d'ingestion
-- ============================================

CREATE OR REPLACE FUNCTION create_document_job(
    p_api_key_id UUID,
    p_user_id UUID,
    p_source_filename VARCHAR(500),
    p_source_type VARCHAR(50),
    p_source_size_bytes BIGINT DEFAULT NULL,
    p_webhook_url TEXT DEFAULT NULL,
    p_webhook_secret VARCHAR(100) DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_job_id UUID;
BEGIN
    INSERT INTO document_jobs (
        api_key_id,
        user_id,
        source_filename,
        source_type,
        source_size_bytes,
        webhook_url,
        webhook_secret,
        status
    ) VALUES (
        p_api_key_id,
        p_user_id,
        p_source_filename,
        p_source_type,
        p_source_size_bytes,
        p_webhook_url,
        p_webhook_secret,
        'pending'
    ) RETURNING id INTO v_job_id;
    
    RETURN v_job_id;
END;
$$;

-- ============================================
-- 5. Fonction pour mettre à jour la progression
-- ============================================

CREATE OR REPLACE FUNCTION update_job_progress(
    p_job_id UUID,
    p_chunks_processed INT,
    p_chunks_total INT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_progress INT;
BEGIN
    -- Calculer le pourcentage
    IF p_chunks_total IS NOT NULL AND p_chunks_total > 0 THEN
        v_progress := (p_chunks_processed::FLOAT / p_chunks_total::FLOAT * 100)::INT;
    ELSE
        v_progress := 0;
    END IF;
    
    UPDATE document_jobs SET
        chunks_processed = p_chunks_processed,
        chunks_total = COALESCE(p_chunks_total, chunks_total),
        progress = v_progress,
        status = CASE 
            WHEN status = 'pending' THEN 'processing'
            ELSE status
        END,
        started_at = CASE 
            WHEN started_at IS NULL THEN NOW()
            ELSE started_at
        END
    WHERE id = p_job_id;
END;
$$;

-- ============================================
-- 6. Fonction pour marquer un job comme terminé
-- ============================================

CREATE OR REPLACE FUNCTION complete_document_job(
    p_job_id UUID,
    p_document_id UUID,
    p_success BOOLEAN DEFAULT TRUE,
    p_error_message TEXT DEFAULT NULL,
    p_error_code VARCHAR(50) DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE document_jobs SET
        document_id = p_document_id,
        status = CASE WHEN p_success THEN 'completed' ELSE 'failed' END,
        progress = CASE WHEN p_success THEN 100 ELSE progress END,
        error_message = p_error_message,
        error_code = p_error_code,
        completed_at = NOW()
    WHERE id = p_job_id;
END;
$$;

-- ============================================
-- 7. Vue pour dashboard des jobs
-- ============================================

CREATE OR REPLACE VIEW document_jobs_dashboard AS
SELECT 
    dj.id,
    dj.status,
    dj.progress,
    dj.chunks_processed,
    dj.chunks_total,
    dj.source_filename,
    dj.source_type,
    dj.source_size_bytes,
    dj.error_message,
    dj.created_at,
    dj.started_at,
    dj.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(dj.completed_at, NOW()) - dj.started_at)) AS duration_seconds,
    ak.agent_name,
    ak.id as api_key_id
FROM document_jobs dj
LEFT JOIN api_keys ak ON dj.api_key_id = ak.id
ORDER BY dj.created_at DESC;

-- ============================================
-- 8. RLS Policies
-- ============================================

ALTER TABLE document_jobs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own jobs
CREATE POLICY document_jobs_select_policy ON document_jobs
    FOR SELECT
    USING (user_id = auth.uid());

-- Users can only insert jobs for themselves
CREATE POLICY document_jobs_insert_policy ON document_jobs
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can only update their own jobs
CREATE POLICY document_jobs_update_policy ON document_jobs
    FOR UPDATE
    USING (user_id = auth.uid());

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE document_jobs IS 'Tracking des jobs d''ingestion de documents asynchrones';
COMMENT ON COLUMN document_jobs.status IS 'Statut: pending, processing, completed, failed, cancelled';
COMMENT ON COLUMN document_jobs.progress IS 'Pourcentage de progression (0-100)';
COMMENT ON COLUMN document_jobs.webhook_url IS 'URL de notification à appeler quand le job termine';
COMMENT ON FUNCTION create_document_job IS 'Crée un nouveau job d''ingestion et retourne son ID';
COMMENT ON FUNCTION update_job_progress IS 'Met à jour la progression d''un job (chunks traités)';
COMMENT ON FUNCTION complete_document_job IS 'Marque un job comme terminé (succès ou échec)';
