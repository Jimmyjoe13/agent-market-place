-- ============================================
-- Migration 004: Relation 1 Clé API = 1 Agent
-- Date: 2026-01-03
-- ============================================
-- 
-- Cette migration inverse la relation entre api_keys et agents.
-- Avant: api_keys.agent_id -> agents.id (la clé dépend de l'agent)
-- Après: agents.api_key_id -> api_keys.id (l'agent dépend de la clé)
--
-- ATTENTION: Cette migration supprime les agents orphelins (sans clé).
-- ============================================

-- ============================================
-- Étape 1: Supprimer les vues dépendantes
-- ============================================
DROP VIEW IF EXISTS public.agent_dashboard CASCADE;

-- ============================================
-- Étape 2: Ajouter la nouvelle FK sur agents
-- ============================================
ALTER TABLE public.agents 
ADD COLUMN IF NOT EXISTS api_key_id UUID REFERENCES public.api_keys(id) ON DELETE CASCADE;

-- Créer un index unique (relation 1:1)
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_api_key_unique 
ON public.agents(api_key_id) WHERE api_key_id IS NOT NULL;

-- ============================================
-- Étape 3: Migrer les données existantes
-- ============================================
-- Pour chaque agent, récupérer sa première clé API et la lier
UPDATE public.agents a 
SET api_key_id = (
    SELECT k.id 
    FROM public.api_keys k 
    WHERE k.agent_id = a.id 
    ORDER BY k.created_at ASC 
    LIMIT 1
)
WHERE a.api_key_id IS NULL;

-- ============================================
-- Étape 4: Supprimer les agents sans clé
-- ============================================
-- Ces agents sont orphelins et ne peuvent plus être utilisés
DELETE FROM public.agents 
WHERE api_key_id IS NULL;

-- ============================================
-- Étape 5: Rendre api_key_id NOT NULL (si des agents existent)
-- ============================================
-- Note: On le garde nullable pour le moment car les nouveaux agents
-- sont créés APRÈS leur clé API, donc api_key_id sera défini
-- juste après la création de l'agent.
-- ALTER TABLE public.agents ALTER COLUMN api_key_id SET NOT NULL;

-- ============================================
-- Étape 6: Supprimer l'ancienne FK sur api_keys
-- ============================================
-- D'abord supprimer l'index
DROP INDEX IF EXISTS idx_api_keys_agent;

-- Supprimer la colonne agent_id (CASCADE pour supprimer les contraintes)
ALTER TABLE public.api_keys 
DROP COLUMN IF EXISTS agent_id CASCADE;

-- ============================================
-- Étape 7: Recréer la vue agent_dashboard
-- ============================================
-- La vue utilise maintenant agents.api_key_id au lieu de api_keys.agent_id
CREATE OR REPLACE VIEW public.agent_dashboard AS
SELECT 
    a.id,
    a.user_id,
    a.api_key_id,
    a.name,
    a.description,
    a.model_id,
    a.rag_enabled,
    a.is_active,
    a.tokens_used_this_month,
    a.requests_today,
    a.created_at,
    -- Dans la nouvelle archi, 1 agent = 1 clé, donc count = 1 ou 0
    CASE WHEN a.api_key_id IS NOT NULL THEN 1 ELSE 0 END AS api_keys_count,
    COUNT(DISTINCT d.id) AS documents_count,
    COUNT(DISTINCT c.id) AS conversations_count
FROM public.agents a
LEFT JOIN public.documents d ON d.agent_id = a.id
LEFT JOIN public.conversations c ON c.agent_id = a.id AND c.created_at > NOW() - INTERVAL '30 days'
GROUP BY a.id;

-- ============================================
-- Étape 8: Mettre à jour la fonction validate_api_key
-- ============================================
-- La fonction doit maintenant chercher l'agent via agents.api_key_id
CREATE OR REPLACE FUNCTION public.validate_api_key(p_key_hash TEXT)
RETURNS TABLE (
    is_valid BOOLEAN,
    key_id UUID,
    agent_id UUID,
    user_id UUID,
    scopes TEXT[],
    rate_limit INT,
    model_id TEXT,
    system_prompt TEXT,
    rag_enabled BOOLEAN,
    agent_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TRUE AS is_valid,
        k.id AS key_id,
        a.id AS agent_id,
        k.user_id,
        k.scopes,
        k.rate_limit_per_minute AS rate_limit,
        a.model_id,
        a.system_prompt,
        a.rag_enabled,
        a.name AS agent_name
    FROM public.api_keys k
    LEFT JOIN public.agents a ON a.api_key_id = k.id
    WHERE k.key_hash = p_key_hash
      AND k.is_active = TRUE
      AND (k.expires_at IS NULL OR k.expires_at > NOW());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Note: La limite agents_limit dans plans est maintenant
-- équivalente à api_keys_limit. On peut la conserver pour
-- cohérence ou la supprimer dans une future migration.
-- ============================================
