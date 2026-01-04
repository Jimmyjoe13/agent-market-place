-- ============================================
-- Migration 009: Add stripe_subscription_id to profiles
-- Date: 2026-01-04
-- ============================================
-- 
-- PROBLÈME: Le webhook Stripe échoue car la colonne
-- stripe_subscription_id n'existe pas dans profiles.
-- Le service stripe_service.py l'utilise ligne 200.
--
-- SOLUTION: Ajouter la colonne manquante.
-- ============================================

-- Ajouter la colonne stripe_subscription_id à profiles
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;

-- Index pour recherche par subscription ID (utilisé dans les webhooks)
CREATE INDEX IF NOT EXISTS idx_profiles_stripe_subscription 
ON public.profiles(stripe_subscription_id) 
WHERE stripe_subscription_id IS NOT NULL;

-- ============================================
-- VÉRIFICATION POST-MIGRATION:
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'profiles' 
--   AND column_name = 'stripe_subscription_id';
-- ============================================
