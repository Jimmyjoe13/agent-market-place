# Migrations SQL - Agent Market Place

## Structure

```
migrations/
├── 001_init_schema.sql     # Schéma consolidé v2.0.0
├── archive/                 # Anciennes migrations (001-012)
└── README.md               # Ce fichier
```

## Version 2.0.0 (2025-12-31)

### Breaking Changes

Cette version repart de zéro avec un schéma restructuré :

1. **`profiles` remplace `users`**

   - Lié directement à `auth.users` via FK cascade
   - Création automatique par trigger lors de l'inscription

2. **`agents` séparé de `api_keys`**

   - `agents` : configuration LLM (modèle, prompt, RAG, budget)
   - `api_keys` : authentification pure (hash, scopes, rate limit)
   - Relation 1-N : un agent peut avoir plusieurs clés API

3. **RLS complète**
   - Toutes les tables ont des policies
   - Utilise `auth.uid()` qui correspond maintenant à `profiles.id`

### Tables

| Table           | Description                                      |
| --------------- | ------------------------------------------------ |
| `profiles`      | Extension de auth.users (identité, Stripe, BYOK) |
| `plans`         | Plans d'abonnement (Free, Pro, Enterprise)       |
| `subscriptions` | Abonnements avec intégration Stripe              |
| `agents`        | Configuration des agents IA                      |
| `api_keys`      | Clés API liées aux agents                        |
| `documents`     | Documents vectorisés pour RAG                    |
| `document_jobs` | Jobs d'ingestion asynchrones                     |
| `conversations` | Historique des conversations                     |
| `usage_records` | Tracking mensuel pour facturation                |

### Fonctions

| Fonction                 | Description                            |
| ------------------------ | -------------------------------------- |
| `match_documents()`      | Recherche vectorielle avec filtres     |
| `validate_api_key()`     | Validation + récupération config agent |
| `get_user_usage()`       | Usage mensuel avec limites du plan     |
| `increment_user_usage()` | Incrémente les compteurs               |

## Exécution

### Nouvelle installation

```sql
-- Dans Supabase SQL Editor
-- Exécuter 001_init_schema.sql
```

### Migration depuis v1

> ⚠️ **ATTENTION** : Cette migration ne préserve pas les données existantes.

1. Exporter les données critiques (users, api_keys)
2. Supprimer toutes les tables existantes
3. Exécuter `001_init_schema.sql`
4. Réimporter les données avec le nouveau schéma

## Relations

```
auth.users (Supabase Auth)
    │
    ├── profiles (1:1)
    │       │
    │       ├── subscriptions (1:N)
    │       │       └── plans (N:1)
    │       │
    │       ├── agents (1:N)
    │       │       │
    │       │       ├── api_keys (1:N)
    │       │       ├── documents (1:N)
    │       │       └── conversations (1:N)
    │       │
    │       ├── usage_records (1:N)
    │       └── document_jobs (1:N)
```
