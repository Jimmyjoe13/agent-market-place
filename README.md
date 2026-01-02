# 🤖 RAG Agent IA

[![CI Pipeline](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml/badge.svg)](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml)
[![Security](https://img.shields.io/badge/security-dependabot-green)](https://github.com/Jimmyjoe13/agent-market-place/security)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plateforme SaaS de **Retrieval-Augmented Generation (RAG)** avec une API multi-providers et une interface moderne.

## ✨ Features

- 🔍 **RAG Intelligent** - Recherche sémantique + génération contextuelle
- 🤖 **Multi-Provider LLM** - Mistral, OpenAI, Gemini (BYOK)
- 📊 **Dashboard Analytics** - Suivi d'utilisation en temps réel
- 🔐 **API Sécurisée** - Clés API, rate limiting, scopes
- 💳 **Monétisation** - Intégration Stripe (Free/Pro)
- 📄 **Ingestion Documents** - PDF, GitHub repos, texte
- ⚡ **Streaming** - Réponses en temps réel (SSE)
- 🛡️ **Résilience** - Circuit breaker, fallback providers

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Supabase      │
│   Next.js 16    │     │   FastAPI       │     │   pgvector      │
│   React 19      │     │   Python 3.10+  │     │   PostgreSQL    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │ Mistral │  │ OpenAI  │  │ Gemini  │
              └─────────┘  └─────────┘  └─────────┘
```

## 📁 Structure du Projet

```
agent-market-place/
├── backend/              # API FastAPI (Python)
│   ├── src/
│   │   ├── api/          # Routes & middlewares
│   │   ├── providers/    # LLM providers (Strategy Pattern)
│   │   ├── services/     # Business logic
│   │   ├── workers/      # Jobs asynchrones (RQ)
│   │   └── utils/        # Métriques, encryption
│   └── tests/            # Tests unitaires
│
├── frontend/             # UI Next.js (React)
│   ├── src/
│   │   ├── app/          # Pages (App Router)
│   │   ├── components/   # Composants UI
│   │   ├── hooks/        # React hooks
│   │   └── __tests__/    # Tests Vitest
│   └── e2e/              # Tests Playwright
│
├── docs/                 # Documentation
│   ├── API.md            # Référence API
│   └── ADR.md            # Architecture decisions
│
└── .github/workflows/    # CI/CD
```

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.10+
- Node.js 20+
- Compte [Supabase](https://supabase.com)
- Clé API [Mistral](https://console.mistral.ai)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Configurer les variables
python -m uvicorn src.api.main:app --reload
```

API disponible sur http://localhost:8000

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

App disponible sur http://localhost:3000

## 🧪 Tests

### Backend

```bash
cd backend
pytest                           # Tous les tests
pytest --cov=src                # Avec couverture
ruff check src/                 # Linting
```

### Frontend

```bash
cd frontend
npm run test:unit:run           # Tests Vitest (29 tests)
npm run test                    # Tests E2E Playwright
npm run lint                    # ESLint
```

## 🌐 Déploiement

### Production URLs

- **Frontend**: https://rag-agentia.netlify.app
- **Backend**: https://agent-ia-augment.onrender.com

### Backend sur Render

1. Connecter le repo GitHub
2. Configurer avec `render.yaml`
3. Ajouter les variables d'environnement

### Frontend sur Netlify

1. Connecter le repo GitHub
2. Configurer avec `netlify.toml`
3. Définir `NEXT_PUBLIC_API_URL`

## 📖 Documentation

| Document                              | Description               |
| ------------------------------------- | ------------------------- |
| [API Reference](docs/API.md)          | Endpoints, auth, exemples |
| [Architecture Decisions](docs/ADR.md) | Choix techniques (ADR)    |
| [Contributing](CONTRIBUTING.md)       | Guide de contribution     |
| [Changelog](CHANGELOG.md)             | Historique des versions   |

## 🔧 Configuration

### Variables Backend Essentielles

```env
# Required
MISTRAL_API_KEY=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Optional
OPENAI_API_KEY=xxx
SENTRY_DSN=https://xxx@sentry.io/xxx
REDIS_URL=redis://xxx
```

### Variables Frontend

```env
NEXT_PUBLIC_API_URL=https://agent-ia-augment.onrender.com/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
```

## 📊 Monitoring

- **Métriques Prometheus**: `/metrics`
- **Health Check**: `/health`
- **Error Tracking**: Sentry (optionnel)

## 🤝 Contributing

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## 📜 License

MIT License - Voir [LICENSE](LICENSE)

---

<div align="center">
  Made with ❤️ by the RAG Agent Team
</div>
