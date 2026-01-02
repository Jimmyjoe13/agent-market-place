# Changelog

Toutes les modifications notables du projet sont documentées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et le projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [Unreleased]

### Added

- Documentation API complète (`docs/API.md`)
- Architecture Decision Records (`docs/ADR.md`)
- Guide de contribution (`CONTRIBUTING.md`)
- Tests unitaires frontend avec Vitest (29 tests)
- Métriques Prometheus (`/metrics` endpoint)
- Intégration Sentry pour error tracking
- Queue asynchrone RQ pour jobs lourds
- Headers de sécurité HTTP (HSTS, X-Frame-Options, etc.)
- Pipeline CI/CD GitHub Actions
- Dependabot pour mises à jour de dépendances

### Changed

- Configuration ESLint assouplie pour React 19
- Amélioration robustesse client Supabase

### Fixed

- Erreurs de linting dans le backend
- Tests useApiHealth avec timeout correct

---

## [0.1.0] - 2024-01-15

### Added

#### Backend

- API FastAPI avec documentation OpenAPI
- Système RAG avec Mistral AI embeddings
- Multi-provider LLM (Mistral, OpenAI, Gemini)
- Query Orchestrator pour routage intelligent
- Circuit Breaker pour résilience
- Rate limiting par clé API
- Authentification par clés API avec scopes
- Ingestion de documents (PDF, GitHub, Texte)
- Jobs d'ingestion asynchrones
- Intégration Supabase pgvector
- Intégration Stripe pour monétisation

#### Frontend

- Dashboard Next.js 16 avec React 19
- Interface de chat avec streaming
- Playground pour tester l'API
- Gestion des clés API
- Page de documents
- Configuration agent (modèle, température)
- Authentification Supabase (Google OAuth)
- Abonnements Stripe
- Design responsive (mobile/desktop)
- Dark mode

#### Infrastructure

- Configuration Docker (développement)
- Scripts de migration Supabase
- Fichiers .env.example documentés

### Security

- Validation JWT Supabase
- Sanitisation des prompts
- Logs structurés (pas de secrets)

---

## Types de Changements

- **Added**: Nouvelles fonctionnalités
- **Changed**: Modifications de fonctionnalités existantes
- **Deprecated**: Fonctionnalités bientôt supprimées
- **Removed**: Fonctionnalités supprimées
- **Fixed**: Corrections de bugs
- **Security**: Corrections de vulnérabilités

---

## Liens

- [Comparer les versions](https://github.com/your-repo/compare)
- [Releases](https://github.com/your-repo/releases)

[Unreleased]: https://github.com/your-repo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-repo/releases/tag/v0.1.0
