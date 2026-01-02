"""
Metrics Module
==============

Exposition des métriques Prometheus pour monitoring et observabilité.

Métriques disponibles:
- api_requests_total: Nombre total de requêtes API
- api_request_duration_seconds: Latence des requêtes API
- llm_requests_total: Nombre de requêtes LLM par provider
- llm_request_duration_seconds: Latence des appels LLM
- llm_tokens_total: Tokens consommés par provider
- circuit_breaker_state: État des circuit breakers
- rag_searches_total: Nombre de recherches RAG
- documents_ingested_total: Documents ingérés
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ==============================================
# API Metrics
# ==============================================

api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

api_errors_total = Counter(
    "api_errors_total",
    "Total API errors",
    ["method", "endpoint", "error_type"],
)

# ==============================================
# LLM Provider Metrics
# ==============================================

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
)

llm_request_duration = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "type"],  # type: prompt, completion
)

llm_cost_total = Counter(
    "llm_cost_total",
    "Estimated LLM cost in USD (x1000 for precision)",
    ["provider", "model"],
)

# ==============================================
# Circuit Breaker Metrics
# ==============================================

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["provider"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["provider"],
)

# ==============================================
# RAG Metrics
# ==============================================

rag_searches_total = Counter(
    "rag_searches_total",
    "Total RAG vector searches",
    ["intent", "success"],
)

rag_search_duration = Histogram(
    "rag_search_duration_seconds",
    "RAG search latency in seconds",
    ["intent"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

rag_documents_retrieved = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per search",
    ["intent"],
    buckets=[0, 1, 2, 3, 5, 10, 20],
)

# ==============================================
# Document Ingestion Metrics
# ==============================================

documents_ingested_total = Counter(
    "documents_ingested_total",
    "Total documents ingested",
    ["source_type", "status"],  # github, pdf, text / success, error
)

ingestion_duration = Histogram(
    "ingestion_duration_seconds",
    "Document ingestion duration",
    ["source_type"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ==============================================
# Rate Limiting Metrics
# ==============================================

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["api_key_hash"],  # Hashed for privacy
)

# ==============================================
# Application Info
# ==============================================

app_info = Info(
    "rag_agent",
    "RAG Agent application information",
)


def set_app_info(version: str, environment: str) -> None:
    """Set application info metrics."""
    app_info.info(
        {
            "version": version,
            "environment": environment,
        }
    )


# ==============================================
# Helper Functions
# ==============================================


def record_api_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record an API request with metrics."""
    # Normalize endpoint to avoid high cardinality
    normalized_endpoint = _normalize_endpoint(endpoint)

    api_requests_total.labels(
        method=method,
        endpoint=normalized_endpoint,
        status_code=str(status_code),
    ).inc()

    api_request_duration.labels(
        method=method,
        endpoint=normalized_endpoint,
    ).observe(duration)


def record_llm_request(
    provider: str,
    model: str,
    status: str,
    duration: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """Record an LLM request with metrics."""
    llm_requests_total.labels(
        provider=provider,
        model=model,
        status=status,
    ).inc()

    llm_request_duration.labels(
        provider=provider,
        model=model,
    ).observe(duration)

    if prompt_tokens > 0:
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            type="prompt",
        ).inc(prompt_tokens)

    if completion_tokens > 0:
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            type="completion",
        ).inc(completion_tokens)


def record_circuit_breaker_state(provider: str, state: int) -> None:
    """Record circuit breaker state (0=closed, 1=half_open, 2=open)."""
    circuit_breaker_state.labels(provider=provider).set(state)


def record_rag_search(intent: str, success: bool, duration: float, docs_count: int) -> None:
    """Record a RAG search with metrics."""
    rag_searches_total.labels(
        intent=intent,
        success=str(success).lower(),
    ).inc()

    rag_search_duration.labels(intent=intent).observe(duration)
    rag_documents_retrieved.labels(intent=intent).observe(docs_count)


def _normalize_endpoint(endpoint: str) -> str:
    """Normalize endpoint to reduce cardinality.

    Replaces UUIDs and numeric IDs with placeholders.
    """
    import re

    # Replace UUIDs
    endpoint = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        endpoint,
        flags=re.IGNORECASE,
    )

    # Replace numeric IDs
    endpoint = re.sub(r"/\d+", "/{id}", endpoint)

    return endpoint
