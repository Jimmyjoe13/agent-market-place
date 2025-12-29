# 📦 Database Migrations

Ce répertoire contient les migrations SQL pour Supabase/PostgreSQL.

## Migrations Disponibles

| Fichier                   | Description                        | Dépendances |
| ------------------------- | ---------------------------------- | ----------- |
| `001_initial.sql`         | Schema initial (documents, users)  | -           |
| `002_match_documents.sql` | Fonction RPC recherche vectorielle | pgvector    |
| `003_api_keys.sql`        | Table api_keys + validation        | 001         |
| `004_conversations.sql`   | Logging des conversations          | 001, 003    |
| `005_feedback.sql`        | Système de feedback                | 004         |
| `006_usage_logs.sql`      | Logs d'utilisation API             | 003         |
| `007_subscriptions.sql`   | Gestion abonnements Stripe         | 001         |
| **008_agent_config.sql**  | **Agent Marketplace v1**           | 003, 002    |

## Migration 008: Agent Marketplace

### Changements

1. **Extension `api_keys`** : Nouveaux champs agent config

   - `model_id` : Modèle LLM (varchar, défaut: mistral-large-latest)
   - `system_prompt` : Prompt système personnalisé (text)
   - `rag_enabled` : Activer/désactiver RAG (boolean, défaut: true)
   - `agent_name` : Nom affiché de l'agent (varchar)

2. **Extension `documents`** : Isolation par agent

   - `api_key_id` : FK vers api_keys avec CASCADE delete

3. **Mise à jour `match_documents`** : Filtre par api_key_id

4. **Mise à jour `validate_api_key`** : Retourne la config agent

### Application

#### Option 1: Supabase CLI (Recommandé)

```bash
# Depuis la racine du projet
supabase db push

# Ou migration spécifique
supabase migration apply --local
```

#### Option 2: Supabase Studio

1. Aller sur https://app.supabase.com/project/[PROJECT_ID]/sql
2. Copier-coller le contenu de `008_agent_config.sql`
3. Exécuter

#### Option 3: psql

```bash
psql $DATABASE_URL < backend/scripts/migrations/008_agent_config.sql
```

### Rollback

En cas de problème, exécuter:

```sql
-- Supprimer les nouvelles colonnes api_keys
ALTER TABLE api_keys DROP COLUMN IF EXISTS model_id;
ALTER TABLE api_keys DROP COLUMN IF EXISTS system_prompt;
ALTER TABLE api_keys DROP COLUMN IF EXISTS rag_enabled;
ALTER TABLE api_keys DROP COLUMN IF EXISTS agent_name;

-- Supprimer la FK documents
ALTER TABLE documents DROP COLUMN IF EXISTS api_key_id;

-- Note: Les fonctions RPC seront restaurées par la dernière version fonctionnelle
```

## Bonnes Pratiques

1. **Toujours sauvegarder** avant d'appliquer une migration en production
2. **Tester en local** avec `supabase start` avant prod
3. **Vérifier les index** après migration pour les performances
4. **Documenter** les changements breaking dans CHANGELOG

## Structure Recommandée

```
backend/scripts/migrations/
├── README.md              # Ce fichier
├── 001_initial.sql
├── 002_match_documents.sql
├── ...
└── 008_agent_config.sql   # Dernière migration
```
