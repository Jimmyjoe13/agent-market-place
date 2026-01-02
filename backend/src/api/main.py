"""
FastAPI Application
====================

Point d'entrée principal de l'API FastAPI pour le système RAG Agent IA.

Cette API fournit :
- Interrogation du système RAG avec contexte personnel et web
- Gestion des feedbacks pour amélioration continue
- Ingestion de données (GitHub, PDF, texte)
- Gestion des clés API pour l'authentification

Authentification:
    Tous les endpoints (sauf /health) nécessitent une clé API.
    Utilisez le header `X-API-Key` ou le query param `api_key`.

Example:
    curl -X POST http://localhost:8000/api/v1/query \\
        -H "X-API-Key: rag_votre_cle_ici" \\
        -H "Content-Type: application/json" \\
        -d '{"question": "Quelles sont mes compétences?"}'
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src import __version__
from src.api.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from src.api.routes import router
from src.api.routes_admin import admin_router
from src.api.routes_agent import router as agent_router
from src.api.routes_agent_config import router as agent_config_router
from src.api.routes_auth import router as auth_router
from src.api.routes_billing import router as billing_router
from src.api.routes_console import router as console_router
from src.api.routes_jobs import router as jobs_router
from src.api.routes_keys import router as keys_router
from src.api.schemas import HealthResponse
from src.config.logging_config import get_logger, setup_logging
from src.config.redis import close_redis, get_redis_client
from src.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    # Startup
    setup_logging()
    logger = get_logger("api")
    logger.info("API starting", version=__version__)

    # Préchauffer Redis (optionnel)
    await get_redis_client()

    yield

    # Shutdown
    logger.info("API shutting down")
    await close_redis()


def custom_openapi(app: FastAPI) -> dict:
    """
    Génère un schéma OpenAPI personnalisé avec authentification.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="RAG Agent IA API",
        version=__version__,
        description="""
## 🤖 Système RAG Personnalisé

API pour un système de Retrieval-Augmented Generation (RAG) utilisant :
- **Mistral AI** pour les embeddings et la génération de texte
- **Supabase + pgvector** pour le stockage vectoriel
- **Perplexity API** pour la recherche web en temps réel

---

### 🔐 Authentification

Tous les endpoints nécessitent une clé API valide.

**Méthodes d'authentification :**

1. **Header** (recommandé) :
   ```
   X-API-Key: rag_votre_cle_ici
   ```

2. **Query Parameter** :
   ```
   ?api_key=rag_votre_cle_ici
   ```

---

### 🎯 Scopes (Permissions)

Chaque clé API possède des scopes qui définissent ses permissions :

| Scope | Description |
|-------|-------------|
| `query` | Interroger le système RAG |
| `ingest` | Ingérer des documents |
| `feedback` | Soumettre des feedbacks |
| `admin` | Accès complet (gestion des clés) |

---

### 📊 Rate Limiting

Chaque clé a une limite de requêtes par minute (défaut: 100).
Les headers de réponse incluent :
- `X-RateLimit-Limit`: Limite par minute
- `X-RateLimit-Remaining`: Requêtes restantes
- `X-RateLimit-Reset`: Timestamp de reset

---

### 🚀 Démarrage Rapide

1. **Créer une clé API** (avec la master key) :
   ```bash
   curl -X POST http://localhost:8000/api/v1/keys \\
       -H "X-API-Key: VOTRE_MASTER_KEY" \\
       -H "Content-Type: application/json" \\
       -d '{"name": "Mon App", "scopes": ["query", "feedback"]}'
   ```

2. **Interroger le RAG** :
   ```bash
   curl -X POST http://localhost:8000/api/v1/query \\
       -H "X-API-Key: rag_cle_obtenue" \\
       -H "Content-Type: application/json" \\
       -d '{"question": "Quelles sont mes compétences?"}'
   ```
        """,
        routes=app.routes,
    )

    # Ajouter les schémas de sécurité
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Clé API dans le header",
        },
        "ApiKeyQuery": {
            "type": "apiKey",
            "in": "query",
            "name": "api_key",
            "description": "Clé API en query parameter",
        },
    }

    # Appliquer la sécurité globalement
    openapi_schema["security"] = [
        {"ApiKeyHeader": []},
        {"ApiKeyQuery": []},
    ]

    # Ajouter des tags avec descriptions
    openapi_schema["tags"] = [
        {
            "name": "RAG",
            "description": "Interrogation du système RAG avec contexte personnel et web",
        },
        {
            "name": "Feedback",
            "description": "Gestion des feedbacks pour amélioration continue",
        },
        {
            "name": "Ingestion",
            "description": "Ingestion de données (GitHub, PDF, texte)",
        },
        {
            "name": "Training",
            "description": "Ré-injection des bonnes réponses dans le Vector Store",
        },
        {
            "name": "API Keys Management",
            "description": "Gestion des clés API (création, révocation, statistiques)",
        },
        {
            "name": "Agent Configuration",
            "description": "Configuration de l'agent (modèle LLM, prompt système, RAG)",
        },
        {
            "name": "Health",
            "description": "État de santé de l'API",
        },
    ]

    # Ajouter les informations de contact
    openapi_schema["info"]["contact"] = {
        "name": "RAG Agent IA Support",
        "email": "support@example.com",
    }

    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    """
    Factory pour créer l'application FastAPI.

    Returns:
        Application FastAPI configurée avec authentification et documentation.
    """
    settings = get_settings()

    app = FastAPI(
        title="RAG Agent IA API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Schéma OpenAPI personnalisé
    app.openapi = lambda: custom_openapi(app)

    # ===== Error Handlers =====

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handler pour les erreurs HTTP levées explicitement."""
        content = {
            "error": "error",
            "message": str(exc.detail),
        }

        # Si detail est un dict, on extrait les infos
        if isinstance(exc.detail, dict):
            content["error"] = exc.detail.get("error", "error")
            content["message"] = exc.detail.get("message", str(exc.detail))
            if "details" in exc.detail:
                content["details"] = exc.detail["details"]

        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handler pour les erreurs de validation Pydantic."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "INVALID_REQUEST",
                "message": "Erreur de validation des paramètres.",
                "details": {"errors": exc.errors()},
            },
        )

    # CORS Middleware - Configurable origins
    # Note: En production, configurez CORS_ORIGINS avec l'URL du frontend
    cors_origins_str = settings.cors_origins or ""
    cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

    # URLs de production connues (toujours autorisées)
    production_origins = [
        "https://rag-agentia.netlify.app",
        "https://agent-ia-augment.onrender.com",
    ]

    # Ajouter les origines de production
    for origin in production_origins:
        if origin not in cors_origins:
            cors_origins.append(origin)

    # Ajouter les origines de développement
    if settings.is_development:
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ]
        for origin in dev_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)

    # Logging des origines CORS
    logger = get_logger("cors")
    logger.info("CORS origins configured", origins=cors_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Response-Time",
        ],
    )

    # Gateway Middlewares
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Inclure les routes principales
    app.include_router(router, prefix="/api/v1")

    # Inclure les routes admin
    app.include_router(admin_router, prefix="/api/v1")

    # Inclure les routes d'authentification (OAuth, session)
    app.include_router(auth_router, prefix="/api/v1")

    # Inclure les routes de la console (self-service)
    app.include_router(console_router, prefix="/api/v1")

    # Inclure les routes CRUD agents
    app.include_router(agent_router, prefix="/api/v1")

    # Inclure les routes de configuration agent (legacy /agent/config)
    app.include_router(agent_config_router, prefix="/api/v1")

    # Inclure les routes de gestion des clés
    app.include_router(keys_router, prefix="/api/v1")

    # Inclure les routes des jobs de documents
    app.include_router(jobs_router, prefix="/api/v1")

    # Inclure les routes de facturation
    app.include_router(billing_router, prefix="/api/v1")

    # Route de santé à la racine (non protégée)
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="État de santé",
        description="Vérifie l'état de santé de l'API et de ses dépendances.",
    )
    async def health_check() -> HealthResponse:
        """Vérifie l'état de santé de l'API."""
        redis_client = await get_redis_client()
        redis_status = False
        if redis_client:
            try:
                await redis_client.ping()
                redis_status = True
            except Exception:
                redis_status = False

        services = {
            "api": True,
            "mistral": bool(settings.mistral_api_key),
            "supabase": bool(settings.supabase_url),
            "perplexity": bool(settings.perplexity_api_key),
            "github": bool(settings.github_access_token),
            "redis": redis_status,
            "auth_enabled": settings.api_key_required,
        }

        return HealthResponse(
            status="healthy",
            version=__version__,
            services=services,
        )

    @app.api_route(
        "/",
        methods=["GET", "HEAD"],
        tags=["Health"],
        summary="Page d'accueil",
        description="Informations de base sur l'API.",
    )
    async def root() -> dict:
        """Page d'accueil de l'API."""
        return {
            "name": "RAG Agent IA API",
            "version": __version__,
            "description": "Système RAG personnalisé avec Mistral AI",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "auth_required": settings.api_key_required,
        }

    return app


# Instance de l'application
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
