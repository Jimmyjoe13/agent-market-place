# Architecture Decision Records (ADR)

Ce document contient les décisions architecturales importantes du projet RAG Agent IA.

---

## ADR-001: Choix de Mistral AI comme Provider LLM Principal

**Date**: 2024-01-15  
**Statut**: Accepté  
**Décideurs**: Équipe technique

### Contexte

Le système RAG nécessite un modèle de langage pour :

1. Générer des embeddings pour la recherche vectorielle
2. Produire des réponses contextualisées
3. Analyser l'intention des requêtes

### Options Considérées

1. **OpenAI (GPT-4)**: Leader du marché, excellente qualité
2. **Anthropic (Claude)**: Très performant, focus sécurité
3. **Mistral AI**: Modèles français, bon rapport qualité/prix
4. **Open Source (Llama)**: Gratuit mais nécessite infrastructure

### Décision

Nous avons choisi **Mistral AI** comme provider principal.

### Justification

- **Coût**: 2-5x moins cher qu'OpenAI pour des performances similaires
- **Performance**: mistral-large rivalise avec GPT-4 sur les benchmarks
- **Latence**: Faible latence grâce aux serveurs européens
- **Embeddings**: mistral-embed de qualité (dimension 1024)
- **RGPD**: Hébergement européen, conformité facilitée
- **API**: Compatible OpenAI, migration facile

### Conséquences

- ✅ Réduction des coûts d'exploitation
- ✅ Performances excellentes
- ⚠️ Moins de fonctionnalités (pas de vision, moins de modèles)
- ⚠️ Communauté plus petite

### Fallback

Pattern Strategy implémenté pour basculer sur OpenAI si nécessaire.

---

## ADR-002: Architecture RAG avec Supabase pgvector

**Date**: 2024-01-16  
**Statut**: Accepté

### Contexte

Le système nécessite un stockage vectoriel pour la recherche sémantique.

### Options Considérées

1. **Pinecone**: Leader des vector DB, managed
2. **Weaviate**: Open source, feature-rich
3. **Supabase pgvector**: PostgreSQL avec extension vectorielle
4. **ChromaDB**: Simple, in-memory

### Décision

Nous utilisons **Supabase avec pgvector**.

### Justification

- **All-in-one**: Auth + DB + Vectors + Storage en un service
- **SQL familier**: Pas de nouveau langage à apprendre
- **Coût**: Tier gratuit généreux, pricing prévisible
- **Performance**: Excellente pour notre volume (<1M vecteurs)
- **Real-time**: Subscriptions Postgres pour updates live

### Conséquences

- ✅ Stack simplifiée (un seul provider)
- ✅ Requêtes SQL hybrides (vecteur + metadata)
- ⚠️ Moins optimisé que Pinecone à très grande échelle
- ⚠️ Maintenance des indices HNSW/IVFFlat

---

## ADR-003: Next.js 16 avec React 19 pour le Frontend

**Date**: 2024-01-17  
**Statut**: Accepté

### Contexte

Besoin d'un framework frontend moderne pour le dashboard SaaS.

### Options Considérées

1. **Next.js 16**: React 19, RSC, Server Actions
2. **Remix**: Full-stack React
3. **Vite + React**: SPA classique
4. **Vue/Nuxt**: Alternative à React

### Décision

Nous utilisons **Next.js 16 avec React 19**.

### Justification

- **Server Components**: Réduction du JS client
- **React Compiler**: Optimisations automatiques
- **Streaming**: Suspense streaming pour UX fluide
- **Image Optimization**: next/image pour performance
- **Ecosystem**: Vaste communauté et plugins

### Conséquences

- ✅ Performance optimale out-of-the-box
- ✅ SEO excellent avec RSC
- ⚠️ Complexité accrue (client vs server)
- ⚠️ React 19 encore récent, possible instabilité

---

## ADR-004: Pattern Strategy pour Multi-Provider LLM

**Date**: 2024-01-18  
**Statut**: Accepté

### Contexte

L'API doit supporter plusieurs fournisseurs LLM (Mistral, OpenAI, Anthropic).

### Options Considérées

1. **Hardcoded switch/case**: Simple mais rigide
2. **Factory Pattern**: Création dynamique
3. **Strategy Pattern**: Interface commune + implémentations
4. **Dependency Injection**: Framework complet

### Décision

Nous implémentons le **Strategy Pattern**.

### Justification

```
┌──────────────────┐
│  BaseLLMProvider │ (interface)
└────────┬─────────┘
         │
    ┌────┼────┐
    │    │    │
┌───▼──┐ ┌▼───┐ ┌──▼──┐
│Mistral│ │OpenAI│ │Gemini│
└───────┘ └─────┘ └─────┘
```

- **Extensibilité**: Ajouter un provider = 1 nouvelle classe
- **Testabilité**: Mocks faciles par interface
- **Lisibilité**: Séparation claire des responsabilités
- **Runtime switching**: Changement de provider dynamique

### Conséquences

- ✅ BYOK (Bring Your Own Key) facilité
- ✅ A/B testing de providers possible
- ⚠️ Plus de code boilerplate
- ⚠️ Nécessite abstractions cohérentes

---

## ADR-005: Redis Queue pour Jobs Asynchrones

**Date**: 2024-01-19  
**Statut**: Accepté

### Contexte

L'ingestion de documents peut prendre plusieurs minutes.
Les timeouts HTTP standard (30s) sont insuffisants.

### Options Considérées

1. **Celery**: Standard Python, feature-rich
2. **RQ (Redis Queue)**: Simple, léger
3. **Dramatiq**: Modern, batteries-included
4. **Background Tasks FastAPI**: Natif mais limité

### Décision

Nous utilisons **RQ (Redis Queue)**.

### Justification

- **Simplicité**: Redis déjà utilisé pour rate limiting
- **Légèreté**: Pas de broker séparé (comme Celery + RabbitMQ)
- **Monitoring**: Dashboard RQ Dashboard disponible
- **Debugging**: Jobs sérialisés en JSON, faciles à inspecter

### Pattern Implémenté

```
Client → FastAPI → Redis → Worker → Result
           │                         │
           └──── Poll /jobs/{id} ◄───┘
```

### Conséquences

- ✅ Jobs longs sans timeout
- ✅ Progression en temps réel
- ✅ Retry automatique sur échec
- ⚠️ Nécessite worker process séparé
- ⚠️ Redis devient point critique

---

## ADR-006: Circuit Breaker pour Résilience

**Date**: 2024-01-20  
**Statut**: Accepté

### Contexte

Les appels aux APIs externes (LLM, embeddings) peuvent échouer.
Sans protection, ces échecs cascadent et dégradent le service.

### Décision

Implémentation d'un **Circuit Breaker Pattern**.

### États

```
         success
    ┌───────────────┐
    │               ▼
┌───┴───┐   ┌───────────┐   timeout   ┌────────┐
│ CLOSED│───│ HALF_OPEN │◄────────────│  OPEN  │
└───────┘   └───────────┘             └────────┘
    │                                      ▲
    │        failure_threshold             │
    └──────────────────────────────────────┘
```

### Configuration

```python
CircuitBreakerConfig(
    failure_threshold=5,      # 5 échecs → ouverture
    success_threshold=2,      # 2 succès → fermeture
    timeout=30.0,             # 30s avant retry
    half_open_max_calls=3     # 3 appels en half_open
)
```

### Conséquences

- ✅ Isolation des pannes
- ✅ Fallback automatique vers backup provider
- ✅ Récupération gracieuse
- ⚠️ Complexité de configuration
- ⚠️ Faux positifs possibles

---

## ADR-007: Supabase Auth pour l'Authentification

**Date**: 2024-01-21  
**Statut**: Accepté

### Contexte

Le SaaS nécessite une authentification utilisateur sécurisée.

### Options Considérées

1. **Auth0**: Complet mais coûteux
2. **Firebase Auth**: Google-centric
3. **Supabase Auth**: Intégré avec notre DB
4. **Custom JWT**: Contrôle total mais risques

### Décision

Nous utilisons **Supabase Auth**.

### Justification

- **Intégration native**: Même session pour DB et Auth
- **OAuth providers**: Google, GitHub, etc. préconfigurés
- **Row Level Security**: Policies basées sur auth.uid()
- **Coût**: Inclus dans Supabase (pas de frais Auth0)

### Conséquences

- ✅ Stack unifiée
- ✅ RLS pour sécurité fine
- ⚠️ Vendor lock-in Supabase
- ⚠️ Moins flexible que Auth0

---

## Template ADR

```markdown
## ADR-XXX: [Titre]

**Date**: YYYY-MM-DD  
**Statut**: Proposé | Accepté | Déprécié | Remplacé  
**Décideurs**: [Noms]

### Contexte

[Quel est le problème à résoudre?]

### Options Considérées

1. Option A
2. Option B
3. Option C

### Décision

Nous choisissons [option].

### Justification

[Pourquoi cette option?]

### Conséquences

- ✅ Avantage 1
- ✅ Avantage 2
- ⚠️ Inconvénient 1
```
