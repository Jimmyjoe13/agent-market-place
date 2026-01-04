-- =============================================
-- Migration 013: Mémoire Persistante des Agents + Archivage Conversations
-- =============================================
-- 
-- Fonctionnalités:
-- 1. Table agent_memory avec limite configurable par agent
-- 2. Table conversations_archive pour l'archivage automatique
-- 3. Fonction d'archivage des conversations > 15 jours
-- =============================================

-- ====================
-- 1. MÉMOIRE DES AGENTS
-- ====================

-- Ajouter la colonne memory_limit à la table agents
ALTER TABLE public.agents 
ADD COLUMN IF NOT EXISTS memory_limit INTEGER DEFAULT 20 
CHECK (memory_limit >= 0 AND memory_limit <= 100);

COMMENT ON COLUMN public.agents.memory_limit IS 'Limite de messages en mémoire (0 = désactivé, max 100)';

-- Table de mémoire conversationnelle par agent
CREATE TABLE IF NOT EXISTS public.agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Contrainte d'unicité: 1 seul message par index par agent
    UNIQUE(agent_id, message_index)
);

-- Index pour récupération rapide
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON public.agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_created ON public.agent_memory(agent_id, created_at DESC);

-- Fonction pour ajouter un message avec rotation FIFO
-- Utilise la limite configurable de l'agent
CREATE OR REPLACE FUNCTION add_agent_memory(
    p_agent_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_metadata JSONB DEFAULT '{}'
) RETURNS VOID AS $$
DECLARE
    v_next_index INTEGER;
    v_memory_limit INTEGER;
BEGIN
    -- Récupérer la limite de mémoire de l'agent
    SELECT COALESCE(memory_limit, 20) INTO v_memory_limit
    FROM public.agents 
    WHERE id = p_agent_id;
    
    -- Si mémoire désactivée, ne rien faire
    IF v_memory_limit = 0 THEN
        RETURN;
    END IF;
    
    -- Récupérer le prochain index (rotation circulaire)
    SELECT COALESCE(
        (SELECT (MAX(message_index) + 1) % v_memory_limit 
         FROM public.agent_memory 
         WHERE agent_id = p_agent_id),
        0
    ) INTO v_next_index;
    
    -- Insérer ou remplacer (UPSERT)
    INSERT INTO public.agent_memory (agent_id, role, content, message_index, metadata)
    VALUES (p_agent_id, p_role, p_content, v_next_index, p_metadata)
    ON CONFLICT (agent_id, message_index) 
    DO UPDATE SET 
        role = EXCLUDED.role,
        content = EXCLUDED.content,
        metadata = EXCLUDED.metadata,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Fonction pour récupérer les messages ordonnés chronologiquement
CREATE OR REPLACE FUNCTION get_agent_memory(
    p_agent_id UUID,
    p_limit INTEGER DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    role TEXT,
    content TEXT,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_memory_limit INTEGER;
BEGIN
    -- Récupérer la limite de l'agent si p_limit non spécifié
    IF p_limit IS NULL THEN
        SELECT COALESCE(memory_limit, 20) INTO v_memory_limit
        FROM public.agents 
        WHERE id = p_agent_id;
    ELSE
        v_memory_limit := p_limit;
    END IF;
    
    RETURN QUERY
    SELECT am.id, am.role, am.content, am.created_at
    FROM public.agent_memory am
    WHERE am.agent_id = p_agent_id
    ORDER BY am.created_at ASC
    LIMIT v_memory_limit;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour effacer la mémoire d'un agent
CREATE OR REPLACE FUNCTION clear_agent_memory(p_agent_id UUID) 
RETURNS VOID AS $$
BEGIN
    DELETE FROM public.agent_memory WHERE agent_id = p_agent_id;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- 2. ARCHIVAGE DES CONVERSATIONS
-- ====================

-- Table d'archive pour les conversations anciennes
CREATE TABLE IF NOT EXISTS public.conversations_archive (
    id UUID PRIMARY KEY,
    user_id UUID,
    agent_id UUID,
    api_key_id UUID,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context_sources JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    model_used TEXT,
    latency_ms INTEGER,
    feedback_score INTEGER,
    feedback_comment TEXT,
    flagged_for_training BOOLEAN DEFAULT false,
    training_processed_at TIMESTAMPTZ,
    llm_provider VARCHAR DEFAULT 'mistral',
    thought_process JSONB,
    routing_info JSONB,
    reflection_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche dans les archives
CREATE INDEX IF NOT EXISTS idx_conversations_archive_user_id ON public.conversations_archive(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_archive_agent_id ON public.conversations_archive(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_archive_created_at ON public.conversations_archive(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_archive_archived_at ON public.conversations_archive(archived_at);

-- Fonction pour archiver les conversations de plus de 15 jours
CREATE OR REPLACE FUNCTION archive_old_conversations(
    p_days_threshold INTEGER DEFAULT 15
) RETURNS TABLE (
    archived_count INTEGER,
    deleted_count INTEGER
) AS $$
DECLARE
    v_cutoff_date TIMESTAMPTZ;
    v_archived INTEGER := 0;
    v_deleted INTEGER := 0;
BEGIN
    -- Calculer la date limite
    v_cutoff_date := NOW() - (p_days_threshold || ' days')::INTERVAL;
    
    -- Insérer les anciennes conversations dans l'archive
    INSERT INTO public.conversations_archive (
        id, user_id, agent_id, api_key_id, session_id,
        user_query, ai_response, context_sources, metadata,
        prompt_tokens, completion_tokens, model_used, latency_ms,
        feedback_score, feedback_comment, flagged_for_training,
        training_processed_at, llm_provider, thought_process,
        routing_info, reflection_enabled, created_at
    )
    SELECT 
        id, user_id, agent_id, api_key_id, session_id,
        user_query, ai_response, context_sources, metadata,
        prompt_tokens, completion_tokens, model_used, latency_ms,
        feedback_score, feedback_comment, flagged_for_training,
        training_processed_at, llm_provider, thought_process,
        routing_info, reflection_enabled, created_at
    FROM public.conversations
    WHERE created_at < v_cutoff_date
    ON CONFLICT (id) DO NOTHING;
    
    GET DIAGNOSTICS v_archived = ROW_COUNT;
    
    -- Supprimer les conversations archivées de la table principale
    DELETE FROM public.conversations
    WHERE created_at < v_cutoff_date
    AND id IN (SELECT id FROM public.conversations_archive);
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT v_archived, v_deleted;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour récupérer les conversations archivées d'un utilisateur
CREATE OR REPLACE FUNCTION get_archived_conversations(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
) RETURNS TABLE (
    id UUID,
    agent_id UUID,
    session_id TEXT,
    user_query TEXT,
    ai_response TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ca.id, ca.agent_id, ca.session_id,
        ca.user_query, ca.ai_response, ca.model_used,
        ca.created_at, ca.archived_at
    FROM public.conversations_archive ca
    WHERE ca.user_id = p_user_id
    ORDER BY ca.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- 3. RLS (Row Level Security)
-- ====================

-- RLS pour agent_memory
ALTER TABLE public.agent_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their agent memory" ON public.agent_memory;
CREATE POLICY "Users can manage their agent memory"
ON public.agent_memory
FOR ALL
USING (
    agent_id IN (
        SELECT id FROM public.agents WHERE user_id = auth.uid()
    )
);

-- RLS pour conversations_archive
ALTER TABLE public.conversations_archive ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their archived conversations" ON public.conversations_archive;
CREATE POLICY "Users can view their archived conversations"
ON public.conversations_archive
FOR SELECT
USING (user_id = auth.uid());

-- ====================
-- 4. COMMENTS
-- ====================

COMMENT ON TABLE public.agent_memory IS 'Mémoire conversationnelle persistante par agent (limite configurable, rotation FIFO)';
COMMENT ON TABLE public.conversations_archive IS 'Archive des conversations de plus de 15 jours';
COMMENT ON FUNCTION archive_old_conversations IS 'Déplace les conversations anciennes vers l''archive (appelé par cron ou manuellement)';
