"""
Configuration Settings Module
==============================

Gestion centralisée des variables d'environnement avec validation Pydantic.
Toutes les clés API et configurations sensibles sont chargées depuis .env.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration principale de l'application.
    
    Toutes les variables sont chargées depuis le fichier .env.
    Utilise le pattern Singleton via lru_cache.
    
    Attributes:
        mistral_api_key: Clé API Mistral AI pour embeddings et LLM.
        supabase_url: URL du projet Supabase.
        supabase_anon_key: Clé anonyme Supabase (accès limité).
        supabase_service_role_key: Clé service Supabase (accès complet).
        perplexity_api_key: Clé API Perplexity pour recherche web.
        github_access_token: Token d'accès GitHub pour l'API.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===== API Keys =====
    mistral_api_key: str = Field(
        ...,
        description="Clé API Mistral AI",
        min_length=1,
    )
    supabase_url: str = Field(
        ...,
        description="URL du projet Supabase",
    )
    supabase_anon_key: str = Field(
        ...,
        description="Clé anonyme Supabase",
    )
    supabase_service_role_key: str = Field(
        ...,
        description="Clé service role Supabase",
    )
    perplexity_api_key: str = Field(
        default="",
        description="Clé API Perplexity (optionnelle)",
    )
    github_access_token: str = Field(
        default="",
        description="Token d'accès GitHub (optionnel)",
    )
    
    # ===== Alternative LLM Providers =====
    openai_api_key: str = Field(
        default="",
        description="Clé API OpenAI (optionnelle, pour GPT-4)",
    )
    gemini_api_key: str = Field(
        default="",
        description="Clé API Google Gemini (optionnelle)",
    )
    deepseek_api_key: str = Field(
        default="",
        description="Clé API DeepSeek (optionnelle)",
    )
    default_llm_provider: str = Field(
        default="mistral",
        description="Provider LLM par défaut (mistral, openai, gemini)",
    )
    
    # ===== OAuth Settings =====
    google_client_id: str = Field(
        default="",
        description="Google OAuth Client ID",
    )
    google_client_secret: str = Field(
        default="",
        description="Google OAuth Client Secret",
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="URL du frontend (pour les redirections OAuth)",
    )
    supabase_jwt_secret: str = Field(
        default="",
        description="Secret JWT Supabase pour validation des tokens",
    )
    
    # ===== Stripe Settings (Monetization) =====
    stripe_secret_key: str = Field(
        default="",
        description="Clé secrète Stripe",
    )
    stripe_publishable_key: str = Field(
        default="",
        description="Clé publique Stripe",
    )
    stripe_webhook_secret: str = Field(
        default="",
        description="Secret pour les webhooks Stripe",
    )
    stripe_price_pro_monthly: str = Field(
        default="price_1Sk2CNLKvNPDgJAhMhOXiwt4",
        description="Price ID du Plan Pro Mensuel",
    )
    stripe_price_pro_yearly: str = Field(
        default="price_1Sk2EqLKvNPDgJAhxuheJZFc",
        description="Price ID du Plan Pro Annuel",
    )
    
    # ===== Redis Settings (Rate Limiting) =====
    redis_url: str = Field(
        default="",
        description="URL Redis pour le rate limiting (ex: redis://localhost:6379)",
    )
    
    # ===== Application Settings =====
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environnement d'exécution",
    )
    app_debug: bool = Field(
        default=True,
        description="Mode debug activé",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Niveau de logging",
    )
    
    # ===== Vector Store Settings =====
    embedding_model: str = Field(
        default="mistral-embed",
        description="Modèle d'embedding Mistral",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Dimension des vecteurs d'embedding",
        ge=1,
        le=4096,
    )
    similarity_threshold: float = Field(
        default=0.7,
        description="Seuil de similarité pour la recherche",
        ge=0.0,
        le=1.0,
    )
    max_results: int = Field(
        default=10,
        description="Nombre maximum de résultats par recherche",
        ge=1,
        le=100,
    )
    
    # ===== LLM Settings =====
    llm_model: str = Field(
        default="mistral-large-latest",
        description="Modèle LLM Mistral pour la génération",
    )
    llm_temperature: float = Field(
        default=0.7,
        description="Température du LLM (créativité)",
        ge=0.0,
        le=2.0,
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="Nombre maximum de tokens en sortie",
        ge=1,
        le=32768,
    )
    
    # ===== API Settings =====
    api_host: str = Field(
        default="0.0.0.0",
        description="Host de l'API FastAPI",
    )
    api_port: int = Field(
        default=8000,
        description="Port de l'API FastAPI",
        ge=1,
        le=65535,
    )
    api_reload: bool = Field(
        default=True,
        description="Auto-reload en développement",
    )
    
    # ===== API Authentication =====
    api_key_required: bool = Field(
        default=True,
        description="Exiger une clé API pour les endpoints protégés",
    )
    api_master_key: str = Field(
        default="",
        description="Master key pour créer les premières clés API",
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Activer le rate limiting par clé",
    )
    rate_limit_requests: int = Field(
        default=100,
        description="Nombre de requêtes par minute (défaut)",
        ge=0,
        le=10000,
    )
    
    # ===== CORS Settings =====
    cors_origins: str = Field(
        default="http://localhost:3000,https://rag-agentia.netlify.app",
        description="Origines CORS autorisées (séparées par des virgules)",
    )
    
    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Valide que l'URL Supabase est correcte."""
        if not v.startswith("https://") or "supabase" not in v:
            raise ValueError(
                "supabase_url doit être une URL Supabase valide "
                "(ex: https://xxx.supabase.co)"
            )
        return v.rstrip("/")
    
    @property
    def is_development(self) -> bool:
        """Vérifie si on est en environnement de développement."""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """Vérifie si on est en environnement de production."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Retourne l'instance singleton des settings.
    
    Utilise lru_cache pour garantir qu'une seule instance
    est créée durant le cycle de vie de l'application.
    
    Returns:
        Settings: Instance configurée des paramètres.
        
    Raises:
        ValidationError: Si des variables d'environnement requises sont manquantes.
        
    Example:
        >>> settings = get_settings()
        >>> print(settings.llm_model)
        'mistral-large-latest'
    """
    return Settings()
