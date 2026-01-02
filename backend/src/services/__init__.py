"""Services module - Business logic layer."""

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
    with_circuit_breaker,
)
from src.services.document_processor import (
    ChunkingConfig,
    DocumentProcessor,
    JobStatus,
    ProcessingJob,
    RecursiveTextSplitter,
    get_document_processor,
)
from src.services.embedding_service import EmbeddingService
from src.services.feedback_service import FeedbackService
from src.services.orchestrator import (
    OrchestratorConfig,
    QueryIntent,
    QueryOrchestrator,
    RoutingDecision,
    get_orchestrator,
)
from src.services.rag_engine import RAGConfig, RAGEngine, RAGResponse
from src.services.rate_limiter import RateLimiter, get_rate_limiter
from src.services.trace_service import (
    TraceData,
    TraceService,
    estimate_cost_cents,
    get_trace_service,
)
from src.services.vectorization_service import VectorizationService

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
    # Trace Service
    "TraceService",
    "TraceData",
    "get_trace_service",
    "estimate_cost_cents",
]
