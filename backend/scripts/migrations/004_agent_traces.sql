-- ============================================
-- Migration 004: Agent Traces (Monitoring LLM)
-- Date: 2025-12-31
-- ============================================
-- 
-- Table de traces pour le monitoring des appels LLM.
-- Permet de diagnostiquer :
-- - Les erreurs et timeouts
-- - Les coûts par agent/utilisateur
-- - Les latences
-- - Les sources RAG utilisées
-- ============================================

-- Table de traces
CREATE TABLE IF NOT EXISTS public.agent_traces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    agent_id UUID REFERENCES public.agents(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES public.api_keys(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- LLM metrics
    model_used TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_cost_cents NUMERIC(10, 4) DEFAULT 0,
    latency_ms INTEGER,
    
    -- Request info
    query_preview TEXT, -- Premiers 200 caractères de la question
    
    -- Status
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'rate_limited')),
    error_message TEXT,
    error_code TEXT,
    
    -- Context
    routing_decision JSONB, -- Intent, use_rag, use_web, confidence
    sources_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_traces_agent ON public.agent_traces(agent_id);
CREATE INDEX IF NOT EXISTS idx_traces_user ON public.agent_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_traces_status ON public.agent_traces(status) WHERE status != 'success';
CREATE INDEX IF NOT EXISTS idx_traces_created ON public.agent_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_cost ON public.agent_traces(total_cost_cents DESC) WHERE total_cost_cents > 0;

-- RLS
ALTER TABLE public.agent_traces ENABLE ROW LEVEL SECURITY;

-- Utilisateur peut voir ses propres traces
CREATE POLICY "traces_user_own" ON public.agent_traces
    FOR SELECT USING (user_id = auth.uid());

-- Service role peut tout faire
CREATE POLICY "traces_service_role" ON public.agent_traces
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- ============================================
-- Fonction pour calculer le coût estimé
-- ============================================
CREATE OR REPLACE FUNCTION public.estimate_llm_cost(
    p_model TEXT,
    p_prompt_tokens INTEGER,
    p_completion_tokens INTEGER
)
RETURNS NUMERIC(10, 4)
LANGUAGE plpgsql
AS $$
DECLARE
    v_input_cost NUMERIC(10, 8);
    v_output_cost NUMERIC(10, 8);
BEGIN
    -- Coûts par 1000 tokens en centimes (approximatifs)
    CASE 
        WHEN p_model LIKE 'mistral-large%' THEN
            v_input_cost := 0.4;  -- $0.004/1K
            v_output_cost := 1.2; -- $0.012/1K
        WHEN p_model LIKE 'mistral-small%' THEN
            v_input_cost := 0.1;
            v_output_cost := 0.3;
        WHEN p_model LIKE 'gpt-4o%' THEN
            v_input_cost := 0.5;  -- $0.005/1K
            v_output_cost := 1.5; -- $0.015/1K
        WHEN p_model LIKE 'gpt-4o-mini%' THEN
            v_input_cost := 0.015;
            v_output_cost := 0.06;
        WHEN p_model LIKE 'deepseek%' THEN
            v_input_cost := 0.014; -- Très économique
            v_output_cost := 0.028;
        ELSE
            v_input_cost := 0.2;  -- Default
            v_output_cost := 0.6;
    END CASE;
    
    RETURN (p_prompt_tokens / 1000.0 * v_input_cost) + 
           (p_completion_tokens / 1000.0 * v_output_cost);
END;
$$;

-- ============================================
-- Vue agrégée pour le dashboard
-- ============================================
CREATE OR REPLACE VIEW public.agent_traces_summary AS
SELECT 
    user_id,
    agent_id,
    DATE_TRUNC('day', created_at) AS day,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_requests,
    COUNT(*) FILTER (WHERE status = 'error') AS failed_requests,
    AVG(latency_ms) FILTER (WHERE status = 'success') AS avg_latency_ms,
    SUM(prompt_tokens) AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens,
    SUM(total_cost_cents) AS total_cost_cents,
    AVG(sources_count) AS avg_sources_used
FROM public.agent_traces
GROUP BY user_id, agent_id, DATE_TRUNC('day', created_at);

COMMENT ON TABLE public.agent_traces IS 'Traces de monitoring pour chaque appel LLM';
COMMENT ON FUNCTION public.estimate_llm_cost IS 'Estime le coût en centimes d un appel LLM';
