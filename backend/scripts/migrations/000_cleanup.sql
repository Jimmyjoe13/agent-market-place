-- ============================================
-- NETTOYAGE - Exécuter AVANT 001_init_schema.sql
-- ============================================
-- 
-- Ce script supprime les anciennes tables et policies
-- pour permettre une migration propre.
--
-- ⚠️ ATTENTION: TOUTES LES DONNÉES SERONT PERDUES !
-- ============================================

-- Désactiver temporairement les triggers
SET session_replication_role = 'replica';

-- ============================================
-- 1. Supprimer les vues
-- ============================================
DROP VIEW IF EXISTS public.agent_dashboard CASCADE;
DROP VIEW IF EXISTS public.budget_monitoring CASCADE;
DROP VIEW IF EXISTS public.agent_logs_dashboard CASCADE;
DROP VIEW IF EXISTS public.agent_usage_summary CASCADE;

-- ============================================
-- 2. Supprimer les fonctions
-- ============================================
DROP FUNCTION IF EXISTS public.match_documents CASCADE;
DROP FUNCTION IF EXISTS public.validate_api_key CASCADE;
DROP FUNCTION IF EXISTS public.get_user_usage CASCADE;
DROP FUNCTION IF EXISTS public.increment_user_usage CASCADE;
DROP FUNCTION IF EXISTS public.get_api_key_stats CASCADE;
DROP FUNCTION IF EXISTS public.log_conversation CASCADE;
DROP FUNCTION IF EXISTS public.flag_for_training CASCADE;
DROP FUNCTION IF EXISTS public.get_conversation_analytics CASCADE;
DROP FUNCTION IF EXISTS public.create_document_job CASCADE;
DROP FUNCTION IF EXISTS public.update_job_progress CASCADE;
DROP FUNCTION IF EXISTS public.complete_job CASCADE;
DROP FUNCTION IF EXISTS public.check_token_budget CASCADE;
DROP FUNCTION IF EXISTS public.check_daily_request_limit CASCADE;
DROP FUNCTION IF EXISTS public.increment_token_usage CASCADE;
DROP FUNCTION IF EXISTS public.log_detailed_usage CASCADE;
DROP FUNCTION IF EXISTS public.get_agent_logs CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user CASCADE;
DROP FUNCTION IF EXISTS public.update_updated_at_column CASCADE;

-- ============================================
-- 3. Supprimer les tables (ordre inverse des FK)
-- ============================================
DROP TABLE IF EXISTS public.usage_records CASCADE;
DROP TABLE IF EXISTS public.conversations CASCADE;
DROP TABLE IF EXISTS public.document_jobs CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.api_keys CASCADE;
DROP TABLE IF EXISTS public.api_key_usage_logs CASCADE;
DROP TABLE IF EXISTS public.agents CASCADE;
DROP TABLE IF EXISTS public.subscriptions CASCADE;
DROP TABLE IF EXISTS public.plans CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;  -- Ancienne table si elle existe

-- ============================================
-- 4. Supprimer le trigger sur auth.users
-- ============================================
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Réactiver les triggers
SET session_replication_role = 'origin';

-- ============================================
-- TERMINÉ ! Vous pouvez maintenant exécuter 001_init_schema.sql
-- ============================================
SELECT 'Nettoyage terminé. Exécutez maintenant 001_init_schema.sql' AS message;
