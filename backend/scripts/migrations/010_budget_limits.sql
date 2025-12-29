-- ============================================
-- Migration 010: Budget Limits & Token Tracking
-- RAG Agent IA - Hard Limits pour Sécurité
-- ============================================
-- 
-- Cette migration ajoute les limites de budget/tokens par clé API
-- pour protéger contre les abus et maîtriser les coûts.
--
-- Features:
--   - max_monthly_tokens: Limite tokens/mois
--   - max_daily_requests: Limite requêtes/jour
--   - system_prompt_max_length: Limite taille prompt
--   - Tracking tokens utilisés
--
-- Breaking Changes: Aucun (valeurs par défaut généreuses)
-- ============================================

-- ============================================
-- 1. Extension api_keys avec budget limits
-- ============================================

-- Limite de tokens par mois (0 = illimité)
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS max_monthly_tokens BIGINT DEFAULT 0;

-- Limite de requêtes par jour (0 = illimité)
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS max_daily_requests INT DEFAULT 0;

-- Tokens utilisés ce mois
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS tokens_used_this_month BIGINT DEFAULT 0;

-- Requêtes aujourd'hui
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS requests_today INT DEFAULT 0;

-- Date du dernier reset quotidien
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS daily_reset_date DATE DEFAULT CURRENT_DATE;

-- Limite taille prompt système (défaut 4000 chars)
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS system_prompt_max_length INT DEFAULT 4000;

-- ============================================
-- 2. Fonction de vérification budget tokens
-- ============================================

CREATE OR REPLACE FUNCTION check_token_budget(
    p_api_key_id UUID,
    p_tokens_to_use INT
)
RETURNS TABLE (
    allowed BOOLEAN,
    current_usage BIGINT,
    max_limit BIGINT,
    remaining BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_key RECORD;
    v_current_month VARCHAR(7);
BEGIN
    v_current_month := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Récupérer la clé
    SELECT * INTO v_key FROM api_keys WHERE id = p_api_key_id;
    
    IF v_key IS NULL THEN
        RETURN QUERY SELECT FALSE, 0::BIGINT, 0::BIGINT, 0::BIGINT;
        RETURN;
    END IF;
    
    -- Reset mensuel si nécessaire
    IF v_key.usage_reset_month IS NULL OR v_key.usage_reset_month != v_current_month THEN
        UPDATE api_keys SET 
            tokens_used_this_month = 0,
            usage_reset_month = v_current_month
        WHERE id = p_api_key_id;
        
        v_key.tokens_used_this_month := 0;
    END IF;
    
    -- Si pas de limite, toujours autorisé
    IF v_key.max_monthly_tokens <= 0 THEN
        RETURN QUERY SELECT 
            TRUE, 
            v_key.tokens_used_this_month,
            0::BIGINT,
            9223372036854775807::BIGINT; -- Max BIGINT
        RETURN;
    END IF;
    
    -- Vérifier la limite
    IF v_key.tokens_used_this_month + p_tokens_to_use > v_key.max_monthly_tokens THEN
        RETURN QUERY SELECT 
            FALSE, 
            v_key.tokens_used_this_month,
            v_key.max_monthly_tokens,
            GREATEST(0, v_key.max_monthly_tokens - v_key.tokens_used_this_month);
        RETURN;
    END IF;
    
    RETURN QUERY SELECT 
        TRUE, 
        v_key.tokens_used_this_month,
        v_key.max_monthly_tokens,
        v_key.max_monthly_tokens - v_key.tokens_used_this_month - p_tokens_to_use;
END;
$$;

-- ============================================
-- 3. Fonction de vérification limite requêtes
-- ============================================

CREATE OR REPLACE FUNCTION check_daily_request_limit(
    p_api_key_id UUID
)
RETURNS TABLE (
    allowed BOOLEAN,
    current_count INT,
    max_limit INT,
    remaining INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_key RECORD;
    v_today DATE := CURRENT_DATE;
BEGIN
    -- Récupérer la clé
    SELECT * INTO v_key FROM api_keys WHERE id = p_api_key_id;
    
    IF v_key IS NULL THEN
        RETURN QUERY SELECT FALSE, 0, 0, 0;
        RETURN;
    END IF;
    
    -- Reset quotidien si nécessaire
    IF v_key.daily_reset_date IS NULL OR v_key.daily_reset_date != v_today THEN
        UPDATE api_keys SET 
            requests_today = 0,
            daily_reset_date = v_today
        WHERE id = p_api_key_id;
        
        v_key.requests_today := 0;
    END IF;
    
    -- Si pas de limite, toujours autorisé
    IF v_key.max_daily_requests <= 0 THEN
        RETURN QUERY SELECT 
            TRUE, 
            v_key.requests_today,
            0,
            2147483647; -- Max INT
        RETURN;
    END IF;
    
    -- Vérifier la limite
    IF v_key.requests_today >= v_key.max_daily_requests THEN
        RETURN QUERY SELECT 
            FALSE, 
            v_key.requests_today,
            v_key.max_daily_requests,
            0;
        RETURN;
    END IF;
    
    RETURN QUERY SELECT 
        TRUE, 
        v_key.requests_today,
        v_key.max_daily_requests,
        v_key.max_daily_requests - v_key.requests_today - 1;
END;
$$;

-- ============================================
-- 4. Fonction pour incrémenter l'usage
-- ============================================

CREATE OR REPLACE FUNCTION increment_token_usage(
    p_api_key_id UUID,
    p_prompt_tokens INT,
    p_completion_tokens INT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_tokens INT;
    v_current_month VARCHAR(7);
    v_today DATE := CURRENT_DATE;
BEGIN
    v_total_tokens := p_prompt_tokens + p_completion_tokens;
    v_current_month := TO_CHAR(NOW(), 'YYYY-MM');
    
    UPDATE api_keys SET
        tokens_used_this_month = CASE 
            WHEN usage_reset_month != v_current_month THEN v_total_tokens
            ELSE tokens_used_this_month + v_total_tokens
        END,
        requests_today = CASE
            WHEN daily_reset_date != v_today THEN 1
            ELSE requests_today + 1
        END,
        usage_reset_month = v_current_month,
        daily_reset_date = v_today
    WHERE id = p_api_key_id;
END;
$$;

-- ============================================
-- 5. Vue pour monitoring des budgets
-- ============================================

CREATE OR REPLACE VIEW budget_monitoring AS
SELECT 
    ak.id,
    ak.name,
    ak.agent_name,
    ak.tokens_used_this_month,
    ak.max_monthly_tokens,
    CASE 
        WHEN ak.max_monthly_tokens > 0 
        THEN ROUND((ak.tokens_used_this_month::NUMERIC / ak.max_monthly_tokens::NUMERIC) * 100, 2)
        ELSE 0
    END as token_usage_percent,
    ak.requests_today,
    ak.max_daily_requests,
    CASE 
        WHEN ak.max_daily_requests > 0 
        THEN ROUND((ak.requests_today::NUMERIC / ak.max_daily_requests::NUMERIC) * 100, 2)
        ELSE 0
    END as daily_request_percent,
    ak.usage_reset_month,
    ak.daily_reset_date
FROM api_keys ak
WHERE ak.is_active = TRUE
ORDER BY ak.tokens_used_this_month DESC;

-- ============================================
-- Comments
-- ============================================

COMMENT ON COLUMN api_keys.max_monthly_tokens IS 'Limite de tokens par mois (0 = illimité)';
COMMENT ON COLUMN api_keys.max_daily_requests IS 'Limite de requêtes par jour (0 = illimité)';
COMMENT ON COLUMN api_keys.tokens_used_this_month IS 'Tokens consommés ce mois-ci';
COMMENT ON COLUMN api_keys.requests_today IS 'Requêtes effectuées aujourd''hui';
COMMENT ON COLUMN api_keys.system_prompt_max_length IS 'Taille max du prompt système en caractères';
COMMENT ON FUNCTION check_token_budget IS 'Vérifie si une utilisation de tokens est dans le budget';
COMMENT ON FUNCTION check_daily_request_limit IS 'Vérifie si la limite quotidienne de requêtes est atteinte';
COMMENT ON FUNCTION increment_token_usage IS 'Incrémente les compteurs d''usage (tokens + requêtes)';
