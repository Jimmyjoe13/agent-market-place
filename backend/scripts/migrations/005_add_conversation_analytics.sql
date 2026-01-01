-- ============================================
-- Migration 005: Add Missing Analytics Functions
-- RAG Agent IA - Restore conversation analytics
-- ============================================
-- 
-- Cette migration restaure la fonction get_conversation_analytics
-- qui a été supprimée par 000_cleanup.sql mais est encore utilisée
-- par le code Python.
-- ============================================

-- ============================================
-- Fonction: get_conversation_analytics
-- Statistiques sur les conversations
-- ============================================
CREATE OR REPLACE FUNCTION public.get_conversation_analytics(
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_conversations BIGINT,
    avg_feedback_score NUMERIC,
    flagged_count BIGINT,
    feedback_distribution JSONB,
    daily_counts JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH date_range AS (
        SELECT NOW() - (p_days || ' days')::INTERVAL AS start_date
    ),
    daily AS (
        SELECT 
            DATE(created_at) AS day,
            COUNT(*) AS count
        FROM conversations, date_range
        WHERE created_at >= date_range.start_date
        GROUP BY DATE(created_at)
    ),
    feedback_dist AS (
        SELECT 
            feedback_score,
            COUNT(*) AS count
        FROM conversations
        WHERE feedback_score IS NOT NULL
        GROUP BY feedback_score
    )
    SELECT
        (SELECT COUNT(*) FROM conversations c, date_range dr WHERE c.created_at >= dr.start_date)::BIGINT,
        (SELECT ROUND(AVG(feedback_score)::NUMERIC, 2) FROM conversations WHERE feedback_score IS NOT NULL),
        (SELECT COUNT(*) FROM conversations WHERE flagged_for_training = TRUE)::BIGINT,
        COALESCE((SELECT jsonb_object_agg(feedback_score::TEXT, count) FROM feedback_dist), '{}'::jsonb),
        COALESCE((SELECT jsonb_object_agg(day::TEXT, count) FROM daily), '{}'::jsonb);
END;
$$;

-- Documentation
COMMENT ON FUNCTION public.get_conversation_analytics IS 
'Récupère les statistiques des conversations sur les N derniers jours.
Retourne: total, score moyen, nombre flaggé, distribution feedback, counts quotidiens.';

-- Grant access to authenticated users
GRANT EXECUTE ON FUNCTION public.get_conversation_analytics(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_conversation_analytics(INTEGER) TO service_role;
