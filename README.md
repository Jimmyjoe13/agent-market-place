# 🤖 RAG Agent IA

[![CI Pipeline](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml/badge.svg)](https://github.com/Jimmyjoe13/agent-market-place/actions/workflows/ci.yml)
[![Security](https://img.shields.io/badge/security-dependabot-green)](https://github.com/Jimmyjoe13/agent-market-place/security)

Système de **Retrieval-Augmented Generation (RAG)** avec interface moderne.

## 📁 Structure du Projet

```
agent-ia_augmenté/
├── backend/          # API FastAPI (Python)
│   ├── src/          # Code source
│   ├── scripts/      # Migrations SQL
│   ├── tests/        # Tests unitaires
│   └── requirements.txt
│
├── frontend/         # UI Next.js (React)
│   ├── src/
│   │   ├── app/      # Pages (App Router)
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/      # API client
│   │   └── types/
│   └── package.json
│
├── render.yaml       # Config backend (Render)
└── netlify.toml      # Config frontend (Netlify)
```

## 🚀 Démarrage Rapide

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configurer les variables
python -m uvicorn src.api.main:app --reload
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Ouvrir http://localhost:3000

## 🌐 Déploiement

### Backend sur Render

1. Connecter le repo GitHub à Render
2. Le fichier `render.yaml` configure automatiquement le service
3. Ajouter les variables d'environnement dans le dashboard Render

### Frontend sur Netlify

1. Connecter le repo GitHub à Netlify
2. Le fichier `netlify.toml` configure automatiquement le build
3. Définir `NEXT_PUBLIC_API_URL` vers l'URL Render

## 🔐 Configuration

### Variables Backend (.env)

```env
MISTRAL_API_KEY=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx
API_MASTER_KEY=master_xxx
CORS_ORIGINS=https://votre-app.netlify.app
```

### Variables Frontend

```env
NEXT_PUBLIC_API_URL=https://rag-agent-api.onrender.com/api/v1
```

## 📖 Documentation API

- Swagger UI: `https://votre-api.onrender.com/docs`
- OpenAPI JSON: `https://votre-api.onrender.com/openapi.json`

## 📜 License

MIT License
