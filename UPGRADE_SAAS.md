# 🚀 Transformation SaaS - Changelog & Architecture

## Vue d'ensemble

Cette mise à jour majeure transforme le prototype en une plateforme SaaS de niveau production avec :

- **Orchestrateur Intelligent** : Routage automatique pour réduire la latence de 60-80%
- **Multi-Providers LLM** : Support Mistral, OpenAI, Gemini avec switching dynamique
- **Mode Réflexion** : Chain-of-Thought pour des réponses approfondies
- **Streaming SSE** : Feedback temps réel avec étapes de progression

---

## 📁 Nouveaux Fichiers Créés

### Backend

```
backend/src/providers/llm/
├── __init__.py          # Exports du module LLM
├── base_llm.py          # Classe abstraite BaseLLMProvider (Pattern Strategy)
├── mistral_provider.py  # Provider Mistral avec streaming
├── openai_provider.py   # Provider OpenAI (GPT-4o, GPT-3.5)
├── gemini_provider.py   # Provider Google Gemini
└── factory.py           # LLMProviderFactory avec cache et registry

backend/src/services/
└── orchestrator.py      # QueryOrchestrator - Routage intelligent
```

### Frontend

```
frontend/src/components/chat/
└── ProcessingSteps.tsx  # Composants UI pour les étapes de traitement
```

---

## 📝 Fichiers Modifiés

### Backend

| Fichier                  | Modifications                                                  |
| ------------------------ | -------------------------------------------------------------- |
| `services/rag_engine.py` | Refactorisation complète avec orchestrateur et multi-providers |
| `services/__init__.py`   | Exports de l'orchestrateur et du rate limiter                  |
| `providers/__init__.py`  | Exports des LLM providers                                      |
| `api/routes.py`          | Endpoint `/query/stream` SSE, nouvelles options query          |
| `api/schemas.py`         | Champs `enable_reflection`, `use_rag`, `routing`               |
| `config/settings.py`     | Clés API OpenAI, Gemini, DeepSeek                              |
| `.env.example`           | Variables pour les providers alternatifs                       |

### Frontend

| Fichier                       | Modifications                                       |
| ----------------------------- | --------------------------------------------------- |
| `stores/preferencesStore.ts`  | `forceRag`, `enableReflection`, `useStreaming`      |
| `types/api.ts`                | Types `RoutingInfo`, `StreamEvent`, `StreamingStep` |
| `hooks/useChat.ts`            | Support des nouvelles options et réponses enrichies |
| `app/(console)/chat/page.tsx` | Toggles Réflexion et Documents, nouveaux imports    |

---

## 🔧 Configuration Requise

### Variables d'environnement (optionnelles)

```env
# Alternative LLM Providers
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
DEEPSEEK_API_KEY=...
DEFAULT_LLM_PROVIDER=mistral
```

### Dépendances Python (optionnelles)

```bash
# Pour OpenAI
pip install openai

# Pour Gemini
pip install google-generativeai
```

---

## 🎯 Architecture de l'Orchestrateur

```
┌─────────────────────────────────────────────────────────────┐
│                    QueryOrchestrator                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Quick Detection (Patterns)                               │
│     ├── Greetings → Direct LLM                               │
│     ├── Document keywords → RAG                              │
│     └── Web keywords → Perplexity                           │
│                                                              │
│  2. Smart Routing (LLM-based)                               │
│     └── mistral-tiny classifie l'intent en JSON             │
│                                                              │
│  3. Intent Types                                             │
│     ├── GENERAL → LLM seul (latence minimale)               │
│     ├── DOCUMENTS → RAG + LLM                               │
│     ├── WEB_SEARCH → Perplexity + LLM                       │
│     ├── HYBRID → RAG + Perplexity + LLM                     │
│     └── GREETING → Réponse rapide                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 Pattern Strategy (Multi-Provider)

```python
# Utilisation basique
from src.providers.llm import get_llm_provider, LLMConfig

# Provider par défaut (Mistral)
provider = get_llm_provider()
response = await provider.generate(messages)

# Provider spécifique
config = LLMConfig(model="gpt-4o", temperature=0.5)
openai_provider = get_llm_provider("openai", config)

# Mode réflexion
response = await provider.generate_with_reflection(messages)
print(response.thought_process)  # Pensées internes
print(response.content)          # Réponse finale
```

---

## 📡 API Endpoints

### POST /api/v1/query

Requête standard avec routage intelligent.

```json
{
  "question": "Quels sont mes projets Python ?",
  "use_rag": true,
  "use_web_search": false,
  "enable_reflection": true
}
```

Réponse enrichie :

```json
{
  "answer": "D'après tes projets...",
  "sources": [...],
  "thought_process": "L'utilisateur demande ses projets...",
  "routing": {
    "intent": "documents",
    "use_rag": true,
    "use_web": false,
    "confidence": 0.92,
    "latency_ms": 45
  }
}
```

### POST /api/v1/query/stream

Streaming SSE pour feedback temps réel.

Events émis :

- `routing` : Décision de routage
- `search_start` / `search_complete` : Progression des recherches
- `generation_start` : Début de génération
- `chunk` : Morceaux de réponse
- `thought` : Pensées internes (mode réflexion)
- `complete` : Fin avec métadonnées

---

## 🎨 Nouvelles Options UI

### Barre d'options du chat

| Option           | Description      | Effet                     |
| ---------------- | ---------------- | ------------------------- |
| 🌐 Recherche web | Force Perplexity | `use_web_search: true`    |
| 📄 Mes documents | Force le RAG     | `use_rag: true`           |
| 🧠 Réflexion     | Chain-of-Thought | `enable_reflection: true` |

---

## 📈 Gains de Performance Attendus

| Scénario           | Avant | Après    | Gain       |
| ------------------ | ----- | -------- | ---------- |
| Question générale  | 3-5s  | 0.5-1s   | **70-80%** |
| Salutation         | 3-5s  | 0.2-0.5s | **85-90%** |
| Question documents | 3-5s  | 2-3s     | **30-40%** |
| Question hybride   | 5-8s  | 4-6s     | **20-25%** |

---

## 🔜 Prochaines Étapes

1. **Tests** : Écrire des tests unitaires pour l'orchestrateur
2. **Migration DB** : Ajouter `reflection_data` aux logs de conversation
3. **Frontend Streaming** : Implémenter la consommation des SSE
4. **Rate Limiting Mode Réflexion** : Limiter les tokens pour CoT
5. **BYOK (Bring Your Own Key)** : Permettre aux utilisateurs d'utiliser leurs propres clés API

---

## 🛡️ Points de Vigilance

- **Hallucinations du Routeur** : Le bouton "Mes documents" permet de forcer le RAG
- **Coût Mode Réflexion** : Consomme ~2x plus de tokens
- **Feedback Loop** : Le logging est asynchrone (Background Task prévu)

---

## 🤖 Agent Marketplace v1 (Nouvelle fonctionnalité)

### Concept

Chaque clé API devient un **agent configurable** avec :

- **Modèle LLM** personnalisé (Mistral, OpenAI, Deepseek)
- **Prompt système** dédié
- **Documents RAG** isolés

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       API Key = Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Configuration Agent (stockée en DB) :                       │
│  ├── model_id: "deepseek-chat" | "gpt-4o" | "mistral-large" │
│  ├── system_prompt: "Tu es un expert en..."                 │
│  ├── rag_enabled: true/false                                │
│  └── agent_name: "Mon Assistant"                            │
│                                                              │
│  Isolation Documents :                                       │
│  └── documents.api_key_id → FK vers api_keys.id             │
│      (ON DELETE CASCADE)                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Nouveaux Fichiers

#### Backend

```
backend/scripts/migrations/
└── 008_agent_config.sql        # Extension schema api_keys + documents

backend/src/providers/llm/
└── deepseek_provider.py        # Provider Deepseek (API OpenAI-compatible)

backend/src/api/
└── routes_agent.py             # GET/PATCH /api/v1/agent/config
```

#### Frontend

```
frontend/src/hooks/
└── useAgentConfig.ts           # Hooks React Query

frontend/src/components/
├── playground/
│   └── AgentConfigPanel.tsx    # Panneau de configuration
└── onboarding/
    └── OnboardingTour.tsx      # Tour interactif react-joyride
```

### Nouveaux Endpoints API

| Endpoint                         | Méthode | Description                        |
| -------------------------------- | ------- | ---------------------------------- |
| `/api/v1/agent/config`           | GET     | Récupérer la config de l'agent     |
| `/api/v1/agent/config`           | PATCH   | Mettre à jour (model, prompt, rag) |
| `/api/v1/agent/available-models` | GET     | Liste des modèles disponibles      |

### Migration Database

```sql
-- Extension api_keys
ALTER TABLE api_keys ADD COLUMN model_id VARCHAR(100) DEFAULT 'mistral-large-latest';
ALTER TABLE api_keys ADD COLUMN system_prompt TEXT;
ALTER TABLE api_keys ADD COLUMN rag_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE api_keys ADD COLUMN agent_name VARCHAR(200);

-- Isolation documents par agent
ALTER TABLE documents ADD COLUMN api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE;
CREATE INDEX idx_documents_api_key ON documents(api_key_id);

-- validate_api_key retourne maintenant la config agent
```

### Flow Complet

```
1. Utilisateur crée une clé API (avec agent_config optionnel)
   → POST /api/v1/console/keys { agent_config: { model_id: "deepseek-chat" } }
   → Clé + config stockées en DB

2. Playground charge la config
   → GET /api/v1/agent/config (auth via Bearer token)
   → Affiche dans AgentConfigPanel

3. Utilisateur modifie la config
   → PATCH /api/v1/agent/config { model_id: "gpt-4o" }
   → Sauvegarde en DB

4. Appel API externe
   → POST /api/v1/query avec X-API-Key
   → Middleware injecte agent_config dans request.state
   → RAG Engine utilise model_id + system_prompt + api_key_id
```

### Onboarding Interactif

- **Démarrage automatique** au premier login (localStorage)
- **6 étapes** guidées :
  1. Bienvenue
  2. Gestion des clés API
  3. Création d'agent
  4. Playground
  5. Documentation
  6. Conclusion
- **Persistance** : `localStorage.rag_onboarding_completed`

### Modèles LLM Supportés

| Provider     | Modèles                                             | Notes                 |
| ------------ | --------------------------------------------------- | --------------------- |
| **Mistral**  | mistral-large-latest, mistral-medium, mistral-small | Par défaut            |
| **OpenAI**   | gpt-4o, gpt-4o-mini, gpt-4-turbo                    | Nécessite clé         |
| **Deepseek** | deepseek-chat, deepseek-coder, deepseek-reasoner    | API OpenAI-compatible |

---

## 🚀 Déploiement

### 1. Appliquer la migration

```bash
# Via Supabase CLI
supabase migration apply --local

# Ou directement sur Supabase Studio
# Coller le contenu de 008_agent_config.sql
```

### 2. Variables d'environnement

```env
# Nouveau provider
DEEPSEEK_API_KEY=sk-...

# Existants (rappel)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
```

### 3. Frontend

```bash
cd frontend
npm install react-joyride @radix-ui/react-switch --legacy-peer-deps
npm run build
```
