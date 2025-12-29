"""Services module - Business logic layer."""

from src.services.embedding_service import EmbeddingService
from src.services.vectorization_service import VectorizationService
from src.services.rag_engine import RAGEngine, RAGConfig, RAGResponse
from src.services.feedback_service import FeedbackService
from src.services.orchestrator import (
    QueryOrchestrator,
    RoutingDecision,
    QueryIntent,
    OrchestratorConfig,
    get_orchestrator,
)
from src.services.rate_limiter import RateLimiter, get_rate_limiter
from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    CircuitBreakerConfig,
    get_circuit_breaker,
    with_circuit_breaker,
)
from src.services.document_processor import (
    DocumentProcessor,
    ProcessingJob,
    JobStatus,
    ChunkingConfig,
    RecursiveTextSplitter,
    get_document_processor,
)

__all__ = [
    # Core services
    "EmbeddingService",
    "VectorizationService",
    "RAGEngine",
    "RAGConfig",
    "RAGResponse",
    "FeedbackService",
    # Orchestration
    "QueryOrchestrator",
    "RoutingDecision",
    "QueryIntent",
    "OrchestratorConfig",
    "get_orchestrator",
    # Rate limiting
    "RateLimiter",
    "get_rate_limiter",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "CircuitBreakerConfig",
    "get_circuit_breaker",
    "with_circuit_breaker",
    # Document Processing
    "DocumentProcessor",
    "ProcessingJob",
    "JobStatus",
    "ChunkingConfig",
    "RecursiveTextSplitter",
    "get_document_processor",
]

