# Configuration Supabase Auth

## Variables d'environnement

### Frontend (.env.local)

```bash
# Supabase Configuration (Required)
NEXT_PUBLIC_SUPABASE_URL=https://yourproject.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Backend (.env)

```bash
# Supabase JWT Secret (pour validation des tokens)
# Trouvable dans: Supabase Dashboard > Settings > API > JWT Secret
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard
```

## Configuration Supabase Dashboard

### 1. Activer les providers OAuth

Allez dans **Authentication > Providers** et activez :

- **Google** : Configurer Client ID et Secret depuis Google Cloud Console
- **GitHub** : Configurer OAuth App depuis GitHub Settings > Developer settings
- **Azure (Microsoft)** : Configurer dans Azure Portal > App registrations

### 2. Configurer les URLs de redirection

Dans **Authentication > URL Configuration** :

- **Site URL** : `https://votre-frontend.netlify.app`
- **Redirect URLs** :
  - `http://localhost:3000/auth/callback` (dev)
  - `https://votre-frontend.netlify.app/auth/callback` (prod)

### 3. Récupérer le JWT Secret

Dans **Settings > API** :

- Copier le **JWT Secret** et l'ajouter dans le backend `.env`

## Architecture

```
Frontend (Next.js)
    │
    ├── useAuth() hook
    │   └── @supabase/ssr (browser client)
    │
    └── API calls avec Bearer token
            │
            ▼
Backend (FastAPI)
    │
    ├── deps.py: decode_supabase_jwt()
    │   └── Valide le JWT avec le secret
    │
    └── profiles table (lié à auth.users)
```

## Migration depuis NextAuth

| Avant (NextAuth)         | Après (Supabase)                  |
| ------------------------ | --------------------------------- |
| `useSession()`           | `useAuth()`                       |
| `signIn("google")`       | `supabase.auth.signInWithOAuth()` |
| `signOut()`              | `supabase.auth.signOut()`         |
| `session.user`           | `user` de useAuth                 |
| `[...nextauth]/route.ts` | `/auth/callback/route.ts`         |
