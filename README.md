# 🤖 RAG Agent IA Augmenté

Un système RAG (Retrieval-Augmented Generation) personnalisé utilisant Mistral AI, Supabase et des sources de données externes.

## 🏗️ Architecture

```
agent-ia_augmenté/
├── src/
│   ├── config/          # Configuration & environnement
│   ├── models/          # Modèles Pydantic
│   ├── providers/       # Ingestion de données
│   ├── repositories/    # Accès base de données
│   ├── services/        # Logique métier (RAG Engine)
│   ├── agents/          # Agent de recherche web
│   └── api/             # Endpoints FastAPI
├── scripts/
│   └── migrations/      # Scripts SQL Supabase
├── tests/
│   ├── unit/
│   └── integration/
└── requirements.txt
```

## 🚀 Installation

### Prérequis

- Python 3.10+
- Compte Supabase avec pgvector activé
- Clés API: Mistral AI, Perplexity (optionnel), GitHub (optionnel)

### Setup

```bash
# Cloner et installer
cd agent-ia_augmenté
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# Exécuter les migrations SQL dans Supabase
# (Copier les scripts de scripts/migrations/ dans l'éditeur SQL Supabase)
```

## 📊 Configuration Supabase

1. Créer un projet sur [supabase.com](https://supabase.com)
2. Activer l'extension pgvector dans SQL Editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Exécuter les migrations dans l'ordre:
   - `001_create_documents_table.sql`
   - `002_create_similarity_function.sql`
   - `003_create_conversations_table.sql`

## 🔑 Variables d'Environnement

| Variable                    | Description            | Requis |
| --------------------------- | ---------------------- | ------ |
| `MISTRAL_API_KEY`           | Clé API Mistral AI     | ✅     |
| `SUPABASE_URL`              | URL du projet Supabase | ✅     |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé service Supabase   | ✅     |
| `PERPLEXITY_API_KEY`        | Clé API Perplexity     | ❌     |
| `GITHUB_ACCESS_TOKEN`       | Token GitHub           | ❌     |

## 📚 Composants

### Data Providers

- **GithubProvider**: Extraction de README et code source
- **PDFProvider**: Parsing de CVs et documents PDF

### Services

- **EmbeddingService**: Génération d'embeddings via Mistral
- **RAGEngine**: Orchestration du pipeline RAG complet

### Agents

- **PerplexityAgent**: Recherche web en temps réel

## 🧪 Tests

```bash
pytest tests/ -v --cov=src
```

## 📝 License

MIT
