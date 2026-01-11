# 🤖 RAG Agent IA

[![CI Pipeline](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml/badge.svg)](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml)
[![Security](https://img.shields.io/badge/security-hardened-green)](https://github.com/Jimmyjoe13/agent-market-place/security)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plateforme SaaS de **Retrieval-Augmented Generation (RAG)** avec une API multi-providers et une interface moderne.

## ✨ Features

- 🔍 **RAG Intelligent** - Recherche sémantique + génération contextuelle
- 🤖 **Multi-Provider LLM** - Mistral, OpenAI, Gemini, DeepSeek (BYOK)
- 📊 **Dashboard Analytics** - Suivi d'utilisation en temps réel
- 🔐 **API Sécurisée** - Clés API, rate limiting, scopes, chiffrement BYOK
- 💳 **Monétisation** - Intégration Stripe (Free/Pro)
- 📄 **Ingestion Documents** - PDF, GitHub repos, texte
- ⚡ **Streaming** - Réponses en temps réel (SSE)
- 🛡️ **Résilience** - Circuit breaker, fallback providers
- 🧠 **Mémoire Agent** - Historique conversationnel persistant

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Supabase      │
│   Next.js 15    │     │   FastAPI       │     │   pgvector      │
│   React 19      │     │   Python 3.11+  │     │   PostgreSQL    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
              │ Mistral │  │ OpenAI  │  │ Gemini  │  │ DeepSeek │
              └─────────┘  └─────────┘  └─────────┘  └──────────┘
```

## 📁 Structure du Projet

```
agent-market-place/
├── backend/              # API FastAPI (Python)
│   ├── src/
│   │   ├── api/          # Routes & middlewares
│   │   ├── providers/    # LLM providers (Strategy Pattern)
│   │   │   └── llm/      # Multi-provider abstraction
│   │   ├── services/     # Business logic
│   │   │   └── rag/      # 🆕 RAG Engine modulaire
│   │   │       ├── config.py     # Configuration
│   │   │       ├── retriever.py  # Recherche (Vector + Web)
│   │   │       ├── generator.py  # Génération LLM
│   │   │       └── engine.py     # Orchestration
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
│   ├── ADR.md            # Architecture decisions
│   └── SECURITY_IMPROVEMENTS_PROGRESS.md  # 🆕 Audit sécurité
│
└── .github/workflows/    # CI/CD
```

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.11+ (recommandé, 3.14 non supporté par certaines dépendances)
- Node.js 20+
- Compte [Supabase](https://supabase.com)
- Clé API [Mistral](https://console.mistral.ai)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env   # Configurer les variables
python -m uvicorn src.api.main:app --reload
```

> ⚠️ **Important** : Configurez `ENCRYPTION_KEY` pour le chiffrement BYOK (voir section Configuration).

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
npm run test:unit:run           # Tests Vitest
npm run test                    # Tests E2E Playwright
npm run lint                    # ESLint
```

## 🌐 Déploiement

### Production URLs

- **Frontend**: https://rag-agentia.netlify.app
- **Backend**: https://agent-ia-augment.onrender.com

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour le guide complet.

## 📖 Documentation

| Document                                                 | Description               |
| -------------------------------------------------------- | ------------------------- |
| [API Reference](docs/API.md)                             | Endpoints, auth, exemples |
| [Architecture Decisions](docs/ADR.md)                    | Choix techniques (ADR)    |
| [Security Audit](docs/SECURITY_IMPROVEMENTS_PROGRESS.md) | Améliorations sécurité    |
| [Contributing](CONTRIBUTING.md)                          | Guide de contribution     |
| [Changelog](CHANGELOG.md)                                | Historique des versions   |
| [Deployment](DEPLOYMENT.md)                              | Guide de déploiement      |

## 🔧 Configuration

### Variables Backend Essentielles

```env
# ===== OBLIGATOIRES =====
MISTRAL_API_KEY=your_mistral_key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Encryption (pour BYOK - Clés API utilisateur)
# Générer avec: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_fernet_key_here

# ===== OPTIONNELS =====
OPENAI_API_KEY=xxx           # Pour BYOK multi-provider
PERPLEXITY_API_KEY=xxx       # Recherche web
REDIS_URL=redis://xxx        # Rate limiting
SENTRY_DSN=https://xxx       # Error tracking
```

### Variables Frontend

```env
NEXT_PUBLIC_API_URL=https://agent-ia-augment.onrender.com/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
GOOGLE_CLIENT_ID=xxx         # OAuth
GOOGLE_CLIENT_SECRET=xxx
AUTH_SECRET=xxx              # NextAuth secret
```

## � Sécurité

Ce projet suit les bonnes pratiques de sécurité :

- ✅ **Chiffrement BYOK** - Les clés API utilisateur sont chiffrées avec Fernet (AES-128)
- ✅ **Fail-fast** - L'application refuse de démarrer sans les secrets obligatoires
- ✅ **Pas de secrets hardcodés** - Tous les credentials sont dans les variables d'environnement
- ✅ **Rate limiting** - Protection contre les abus via Redis
- ✅ **Scopes API** - Permissions granulaires par clé API

> 📖 Voir [SECURITY_IMPROVEMENTS_PROGRESS.md](docs/SECURITY_IMPROVEMENTS_PROGRESS.md) pour l'audit de sécurité complet.

## �📊 Monitoring

- **Métriques Prometheus**: `/metrics`
- **Health Check**: `/health`
- **Error Tracking**: Sentry (optionnel)
- **Tracing**: LangSmith (optionnel)

## 🆕 Architecture RAG Modulaire

Le moteur RAG a été refactorisé en architecture modulaire (janvier 2026) :

```python
# Nouvel import recommandé
from src.services.rag import RAGEngine, RAGConfig, RAGRetriever, RAGGenerator

# Import legacy (rétro-compatible)
from src.services.rag_engine import RAGEngine, RAGConfig, RAGResponse
```

| Module             | Responsabilité                |
| ------------------ | ----------------------------- |
| `rag/config.py`    | Configuration et dataclasses  |
| `rag/retriever.py` | Recherche vectorielle + web   |
| `rag/generator.py` | Génération LLM multi-provider |
| `rag/engine.py`    | Orchestration principale      |

## 🤝 Contributing

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## 📜 License

MIT License - Voir [LICENSE](LICENSE)

---

<div align="center">
  Made with ❤️ by the RAG Agent Team
</div>
