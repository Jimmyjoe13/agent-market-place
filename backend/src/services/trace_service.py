"""
Trace Service
==============

Service pour le logging des traces d'exécution LLM.
Permet le monitoring, le debugging et l'analyse des coûts.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.config.logging_config import get_logger
from src.config.supabase import get_supabase_client

logger = get_logger(__name__)


@dataclass
class TraceData:
    """Données d'une trace LLM."""
    user_id: str
    model_used: str
    status: str  # 'success', 'error', 'timeout', 'rate_limited'
    
    # Optionnels
    agent_id: str | None = None
    api_key_id: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int | None = None
    query_preview: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    routing_decision: dict[str, Any] | None = None
    sources_count: int = 0


# Coûts par 1000 tokens en centimes (approximatifs)
MODEL_COSTS: dict[str, tuple[float, float]] = {
    # (input_cost_per_1k, output_cost_per_1k)
    "mistral-large-latest": (0.4, 1.2),
    "mistral-large": (0.4, 1.2),
    "mistral-medium": (0.27, 0.81),
    "mistral-small": (0.1, 0.3),
    "mistral-tiny": (0.025, 0.075),
    "gpt-4o": (0.5, 1.5),
    "gpt-4o-mini": (0.015, 0.06),
    "gpt-4-turbo": (1.0, 3.0),
    "gpt-3.5-turbo": (0.05, 0.15),
    "deepseek-chat": (0.014, 0.028),
    "deepseek-coder": (0.014, 0.028),
    "deepseek-reasoner": (0.055, 0.22),
    "gemini-1.5-pro": (0.125, 0.5),
    "gemini-1.5-flash": (0.0375, 0.15),
}


def estimate_cost_cents(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estime le coût d'une requête LLM en centimes.
    
    Args:
        model: Identifiant du modèle.
        prompt_tokens: Nombre de tokens en entrée.
        completion_tokens: Nombre de tokens en sortie.
        
    Returns:
        Coût estimé en centimes.
    """
    # Trouver le modèle correspondant
    model_lower = model.lower()
    costs = MODEL_COSTS.get(model_lower)
    
    if not costs:
        # Chercher par préfixe
        for key, value in MODEL_COSTS.items():
            if model_lower.startswith(key.split("-")[0]):
                costs = value
                break
        
        # Default si non trouvé
        if not costs:
            costs = (0.2, 0.6)
    
    input_cost, output_cost = costs
    return (prompt_tokens / 1000.0 * input_cost) + (completion_tokens / 1000.0 * output_cost)


class TraceService:
    """Service pour enregistrer les traces d'exécution LLM."""
    
    def __init__(self):
        self._client = get_supabase_client()
    
    def log_trace(self, trace: TraceData) -> str | None:
        """
        Enregistre une trace dans la base de données.
        
        Args:
            trace: Données de la trace.
            
        Returns:
            ID de la trace créée ou None en cas d'erreur.
        """
        try:
            # Calculer le coût
            cost_cents = estimate_cost_cents(
                trace.model_used,
                trace.prompt_tokens,
                trace.completion_tokens
            )
            
            # Préparer le query_preview (max 200 caractères)
            query_preview = trace.query_preview
            if query_preview and len(query_preview) > 200:
                query_preview = query_preview[:197] + "..."
            
            # Insérer la trace
            result = self._client.table("agent_traces").insert({
                "user_id": trace.user_id,
                "agent_id": trace.agent_id,
                "api_key_id": trace.api_key_id,
                "model_used": trace.model_used,
                "prompt_tokens": trace.prompt_tokens,
                "completion_tokens": trace.completion_tokens,
                "total_cost_cents": cost_cents,
                "latency_ms": trace.latency_ms,
                "query_preview": query_preview,
                "status": trace.status,
                "error_message": trace.error_message,
                "error_code": trace.error_code,
                "routing_decision": trace.routing_decision,
                "sources_count": trace.sources_count,
            }).execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
            
        except Exception as e:
            logger.error("Failed to log trace", error=str(e))
            return None
    
    def log_success(
        self,
        user_id: str,
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        query_preview: str | None = None,
        agent_id: str | None = None,
        api_key_id: str | None = None,
        routing_decision: dict | None = None,
        sources_count: int = 0,
    ) -> str | None:
        """Raccourci pour logger une trace de succès."""
        return self.log_trace(TraceData(
            user_id=user_id,
            model_used=model_used,
            status="success",
            agent_id=agent_id,
            api_key_id=api_key_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            query_preview=query_preview,
            routing_decision=routing_decision,
            sources_count=sources_count,
        ))
    
    def log_error(
        self,
        user_id: str,
        model_used: str,
        error_message: str,
        error_code: str | None = None,
        latency_ms: int | None = None,
        query_preview: str | None = None,
        agent_id: str | None = None,
        api_key_id: str | None = None,
    ) -> str | None:
        """Raccourci pour logger une trace d'erreur."""
        return self.log_trace(TraceData(
            user_id=user_id,
            model_used=model_used,
            status="error",
            agent_id=agent_id,
            api_key_id=api_key_id,
            latency_ms=latency_ms,
            query_preview=query_preview,
            error_message=error_message,
            error_code=error_code,
        ))
    
    def log_timeout(
        self,
        user_id: str,
        model_used: str,
        latency_ms: int,
        query_preview: str | None = None,
        agent_id: str | None = None,
        api_key_id: str | None = None,
    ) -> str | None:
        """Raccourci pour logger une trace de timeout."""
        return self.log_trace(TraceData(
            user_id=user_id,
            model_used=model_used,
            status="timeout",
            agent_id=agent_id,
            api_key_id=api_key_id,
            latency_ms=latency_ms,
            query_preview=query_preview,
            error_message="Request timed out",
        ))
    
    def log_rate_limited(
        self,
        user_id: str,
        model_used: str,
        query_preview: str | None = None,
        agent_id: str | None = None,
        api_key_id: str | None = None,
    ) -> str | None:
        """Raccourci pour logger une trace de rate limiting."""
        return self.log_trace(TraceData(
            user_id=user_id,
            model_used=model_used,
            status="rate_limited",
            agent_id=agent_id,
            api_key_id=api_key_id,
            query_preview=query_preview,
            error_message="Rate limit exceeded",
        ))


# Singleton
_trace_service: TraceService | None = None


def get_trace_service() -> TraceService:
    """Retourne l'instance singleton du service de traces."""
    global _trace_service
    if _trace_service is None:
        _trace_service = TraceService()
    return _trace_service
