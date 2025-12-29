"""API module - FastAPI endpoints and authentication."""

from src.api.main import app, create_app
from src.api.routes import router
from src.api.routes_admin import admin_router
from src.api.routes_keys import router as keys_router
from src.api.routes_jobs import router as jobs_router
from src.api.auth import (
    get_api_key,
    require_api_key,
    require_scope,
    require_any_scope,
    require_master_key,
)
from src.api.schemas import (
    QueryRequest,
    QueryResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestResponse,
    AnalyticsResponse,
    HealthResponse,
)

__all__ = [
    # Application
    "app",
    "create_app",
    # Routers
    "router",
    "admin_router",
    "keys_router",
    "jobs_router",
    # Authentication
    "get_api_key",
    "require_api_key",
    "require_scope",
    "require_any_scope",
    "require_master_key",
    # Schemas
    "QueryRequest",
    "QueryResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "IngestResponse",
    "AnalyticsResponse",
    "HealthResponse",
]

