-- =============================================
-- Migration 014: Correction de l'ambiguïté de la fonction get_agent_memory
-- =============================================
-- 
-- Problème: La fonction get_agent_memory retourne une colonne 'id' qui entre
-- en conflit avec des références internes, causant l'erreur:
-- "column reference 'id' is ambiguous"
--
-- Solution: Renommer les colonnes retournées pour éviter l'ambiguïté
-- =============================================

-- Supprimer l'ancienne fonction
DROP FUNCTION IF EXISTS get_agent_memory(UUID, INTEGER);

-- Recréer la fonction avec des noms de colonnes explicites
CREATE OR REPLACE FUNCTION get_agent_memory(
    p_agent_id UUID,
    p_limit INTEGER DEFAULT NULL
) RETURNS TABLE (
    memory_id UUID,
    memory_role TEXT,
    memory_content TEXT,
    memory_created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_memory_limit INTEGER;
BEGIN
    -- Récupérer la limite de l'agent si p_limit non spécifié
    IF p_limit IS NULL THEN
        SELECT COALESCE(agents.memory_limit, 20) INTO v_memory_limit
        FROM public.agents
        WHERE agents.id = p_agent_id;
    ELSE
        v_memory_limit := p_limit;
    END IF;
    
    RETURN QUERY
    SELECT am.id AS memory_id, 
           am.role AS memory_role, 
           am.content AS memory_content, 
           am.created_at AS memory_created_at
    FROM public.agent_memory am
    WHERE am.agent_id = p_agent_id
    ORDER BY am.created_at ASC
    LIMIT v_memory_limit;
END;
$$ LANGUAGE plpgsql;

-- Ajouter un commentaire pour documenter le changement
COMMENT ON FUNCTION get_agent_memory(UUID, INTEGER) IS 
'Récupère les messages de mémoire d''un agent. 
Les colonnes retournées sont préfixées avec "memory_" pour éviter les conflits d''ambiguïté.
Migration 014 (janvier 2026).';
