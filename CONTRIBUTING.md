# Guide de Contribution

Merci de votre intérêt pour contribuer au projet RAG Agent IA ! 🎉

## Table des Matières

1. [Code de Conduite](#code-de-conduite)
2. [Comment Contribuer](#comment-contribuer)
3. [Setup Développement](#setup-développement)
4. [Standards de Code](#standards-de-code)
5. [Process de Review](#process-de-review)
6. [Release Process](#release-process)

---

## Code de Conduite

Ce projet adhère au [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).
En participant, vous vous engagez à respecter ce code.

---

## Comment Contribuer

### 🐛 Reporter un Bug

1. Vérifiez que le bug n'est pas déjà reporté dans les [Issues](https://github.com/your-repo/issues)
2. Créez une nouvelle issue avec le template "Bug Report"
3. Incluez:
   - Description claire du problème
   - Étapes pour reproduire
   - Comportement attendu vs observé
   - Screenshots si applicable
   - Version du navigateur/OS

### 💡 Proposer une Feature

1. Discutez d'abord dans les [Discussions](https://github.com/your-repo/discussions)
2. Si approuvé, créez une issue avec le template "Feature Request"
3. Attendez la validation avant de commencer le développement

### 🔧 Soumettre un Pull Request

1. Fork le repo
2. Créez une branche: `git checkout -b feature/ma-feature`
3. Faites vos modifications
4. Committez: `git commit -m "feat: description"`
5. Push: `git push origin feature/ma-feature`
6. Ouvrez un Pull Request

---

## Setup Développement

### Prérequis

- Python 3.10+
- Node.js 20+
- Redis (optionnel, pour rate limiting)
- Git

### Installation Backend

```bash
cd backend

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Copier la config
cp .env.example .env
# Éditer .env avec vos clés API

# Lancer le serveur
python -m uvicorn src.api.main:app --reload
```

### Installation Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Copier la config
cp .env.example .env.local
# Éditer .env.local

# Lancer le dev server
npm run dev
```

### Tests

```bash
# Backend
cd backend
pytest                          # Tous les tests
pytest tests/unit/              # Tests unitaires
pytest --cov=src               # Avec couverture

# Frontend
cd frontend
npm run test:unit              # Tests unitaires Vitest
npm run test                   # Tests E2E Playwright
```

---

## Standards de Code

### Python (Backend)

**Formatting**: Black + Ruff

```bash
ruff format src/
ruff check src/ --fix
```

**Style Guide**:

- PEP 8 avec modifications Black
- Docstrings Google style
- Type hints obligatoires
- Max 100 caractères par ligne

**Exemple**:

```python
def process_document(
    content: str,
    options: ProcessOptions | None = None,
) -> ProcessResult:
    """
    Traite un document pour extraction et embedding.

    Args:
        content: Contenu brut du document.
        options: Options de traitement optionnelles.

    Returns:
        ProcessResult avec le contenu traité.

    Raises:
        ValueError: Si le contenu est vide.
    """
    if not content.strip():
        raise ValueError("Content cannot be empty")

    # ... implementation
```

### TypeScript (Frontend)

**Formatting**: Prettier + ESLint

```bash
npm run lint
```

**Style Guide**:

- TypeScript strict mode
- Functional components avec hooks
- Prefer named exports
- CSS-in-JS avec Tailwind

**Exemple**:

```typescript
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
}

export function Button({ label, onClick, variant = "primary" }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 rounded-lg",
        variant === "primary" ? "bg-primary" : "bg-secondary"
      )}
    >
      {label}
    </button>
  );
}
```

### Commit Messages

Suivez [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:

- `feat`: Nouvelle feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Ajout de tests
- `chore`: Maintenance

**Exemples**:

```
feat(api): add streaming response endpoint
fix(auth): handle expired JWT tokens
docs(readme): update installation steps
test(hooks): add useApiHealth tests
```

---

## Process de Review

### Checklist PR

- [ ] Code formatté (Black/Prettier)
- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] Pas de secrets dans le code
- [ ] Types complets (no `any`)
- [ ] Messages de commit conventionnels

### Review Timeline

- PRs reviewées sous 48h
- Au moins 1 approval requis
- CI doit passer (tests + lint)
- Pas de merge sans review

### Labels PR

- `WIP`: Work in progress, pas prêt pour review
- `ready-for-review`: Prêt à être reviewé
- `needs-changes`: Modifications demandées
- `approved`: Approuvé, peut être mergé

---

## Release Process

### Versioning

Nous suivons [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: Nouvelles features (backward compatible)
- **PATCH**: Bug fixes

### Release Steps

1. Créer une branche `release/vX.Y.Z`
2. Mettre à jour `version` dans:
   - `backend/pyproject.toml`
   - `frontend/package.json`
3. Mettre à jour `CHANGELOG.md`
4. PR vers `main`
5. Après merge, créer un tag Git
6. GitHub Actions déploie automatiquement

---

## Questions?

- 📧 Email: support@rag-agent.ia
- 💬 Discord: [Lien Discord]
- 📚 Docs: [https://docs.rag-agent.ia]

Merci de contribuer ! 🙏
