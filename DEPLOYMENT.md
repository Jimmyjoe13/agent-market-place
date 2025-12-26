# 🚀 Guide de Déploiement Production

## Prérequis

- Compte [Render](https://render.com) (backend)
- Compte [Netlify](https://netlify.com) (frontend)
- Compte [Redis Cloud](https://redis.com/try-free/) (rate limiting)
- Compte [Supabase](https://supabase.com) (database)
- Google Cloud Console (OAuth)

---

## 1. Configurer Redis Cloud

### 1.1 Créer un compte gratuit

1. Aller sur https://redis.com/try-free/
2. Créer un compte (tier gratuit = 30MB)

### 1.2 Créer une database

1. Dashboard → **New Database**
2. Choisir **Fixed** (gratuit) ou **Flexible**
3. Région : `eu-west-1` (proche de Render/Netlify EU)
4. Cliquer **Create**

### 1.3 Récupérer l'URL de connexion

1. Cliquer sur votre database
2. Section **Connect** → **Redis CLI**
3. Copier le format :

```
redis://default:PASSWORD@HOST:PORT
```

Exemple :

```
redis://default:abc123xyz@redis-12345.c1.eu-west-1-1.ec2.cloud.redislabs.com:12345
```

---

## 2. Déployer le Backend (Render)

### 2.1 Connecter le repo

1. Render Dashboard → **New Web Service**
2. Connecter votre repo GitHub
3. Sélectionner le dossier `backend`

### 2.2 Configuration

```
Name: rag-agent-api
Region: Frankfurt (EU Central)
Branch: main
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

### 2.3 Variables d'environnement (Render)

Ajouter dans **Environment** :

| Variable                    | Valeur                             |
| --------------------------- | ---------------------------------- |
| `MISTRAL_API_KEY`           | votre clé Mistral                  |
| `SUPABASE_URL`              | https://xxx.supabase.co            |
| `SUPABASE_ANON_KEY`         | votre anon key                     |
| `SUPABASE_SERVICE_ROLE_KEY` | votre service role key             |
| `REDIS_URL`                 | redis://default:xxx@host:port      |
| `PERPLEXITY_API_KEY`        | votre clé Perplexity               |
| `APP_ENV`                   | production                         |
| `APP_DEBUG`                 | false                              |
| `LOG_LEVEL`                 | INFO                               |
| `API_MASTER_KEY`            | (générer: `openssl rand -hex 32`)  |
| `CORS_ORIGINS`              | https://votre-frontend.netlify.app |
| `GOOGLE_CLIENT_ID`          | votre client ID                    |
| `GOOGLE_CLIENT_SECRET`      | votre client secret                |

---

## 3. Déployer le Frontend (Netlify)

### 3.1 Connecter le repo

1. Netlify Dashboard → **Add new site** → **Import from Git**
2. Sélectionner votre repo

### 3.2 Configuration build

```
Base directory: frontend
Build command: npm run build
Publish directory: frontend/.next
```

### 3.3 Variables d'environnement (Netlify)

Site Settings → **Environment Variables** :

| Variable               | Valeur                                    |
| ---------------------- | ----------------------------------------- |
| `NEXT_PUBLIC_API_URL`  | https://rag-agent-api.onrender.com/api/v1 |
| `GOOGLE_CLIENT_ID`     | votre client ID                           |
| `GOOGLE_CLIENT_SECRET` | votre client secret                       |
| `AUTH_SECRET`          | (générer: `openssl rand -base64 32`)      |

---

## 4. Configurer Google OAuth

### 4.1 Google Cloud Console

1. https://console.cloud.google.com
2. **APIs & Services** → **Credentials**
3. **Create Credentials** → **OAuth client ID**
4. Type: **Web application**

### 4.2 URLs autorisées

**Authorized JavaScript origins:**

```
https://votre-frontend.netlify.app
http://localhost:3000
```

**Authorized redirect URIs:**

```
https://votre-frontend.netlify.app/api/auth/callback/google
http://localhost:3000/api/auth/callback/google
```

---

## 5. Migrations Supabase

Exécuter les migrations dans SQL Editor de Supabase :

```sql
-- Exécuter dans l'ordre :
-- scripts/migrations/001_*.sql
-- scripts/migrations/002_*.sql
-- ...
-- scripts/migrations/005_multi_tenant_monetization.sql
```

---

## 6. Vérification

### Endpoints à tester

```bash
# Health check backend
curl https://votre-backend.onrender.com/health

# API docs
open https://votre-backend.onrender.com/docs

# Frontend
open https://votre-frontend.netlify.app
```

### Checklist finale

- [ ] Backend répond sur /health
- [ ] Redis connecté (vérifier logs Render)
- [ ] OAuth Google fonctionne
- [ ] Routes console protégées (redirect /login)
- [ ] Création de clé API fonctionne
- [ ] Query RAG fonctionne

---

## Troubleshooting

### Redis ne se connecte pas

```
# Vérifier format URL
redis://default:PASSWORD@HOST:PORT

# Vérifier firewall Redis Cloud
Dashboard → Database → Security → Ajouter 0.0.0.0/0 (temporaire)
```

### OAuth échoue

```
# Vérifier redirect URI exacte
https://votre-site.netlify.app/api/auth/callback/google
```

### CORS errors

```
# Ajouter l'origine exacte dans CORS_ORIGINS
CORS_ORIGINS=https://votre-site.netlify.app
```
