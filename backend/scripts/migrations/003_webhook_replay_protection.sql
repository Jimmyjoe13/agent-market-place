-- ============================================
-- Migration 003: Webhook Replay Protection
-- Date: 2025-12-31
-- ============================================
-- 
-- Protège contre les attaques par rejeu de webhooks Stripe.
-- Un event_id ne peut être traité qu'une seule fois.
--
-- IMPORTANT: Exécuter AVANT la modification de stripe_service.py
-- ============================================

-- Table pour tracker les webhooks déjà traités
CREATE TABLE IF NOT EXISTS public.processed_webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour le cleanup automatique (events > 7 jours)
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed_at 
ON public.processed_webhook_events(processed_at);

-- RLS : seul le service role peut accéder
ALTER TABLE public.processed_webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "webhook_events_service_only" ON public.processed_webhook_events
    FOR ALL TO service_role
    USING (TRUE) WITH CHECK (TRUE);

-- Fonction de cleanup automatique (à appeler via cron job ou pg_cron)
CREATE OR REPLACE FUNCTION public.cleanup_old_webhook_events()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.processed_webhook_events
    WHERE processed_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

COMMENT ON TABLE public.processed_webhook_events IS 'Stocke les event_id Stripe pour prévenir les attaques par rejeu';
COMMENT ON FUNCTION public.cleanup_old_webhook_events IS 'Supprime les events de plus de 7 jours. Appeler via cron quotidien.';
