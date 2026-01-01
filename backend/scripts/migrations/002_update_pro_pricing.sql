-- ============================================
-- Migration 002: Update Pro Pricing
-- Date: 2025-12-31
-- ============================================
-- 
-- Met à jour le pricing Pro :
-- - Mensuel: 39.99€ (3999 cents)
-- - Annuel: 429.88€ (42988 cents, ~10% économie)
-- ============================================

UPDATE public.plans 
SET 
    price_monthly_cents = 3999,
    price_yearly_cents = 42988,
    updated_at = NOW()
WHERE slug = 'pro';
