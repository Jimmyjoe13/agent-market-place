"""
Test Metrics Module
====================

Tests unitaires pour le module de métriques Prometheus.
"""

import pytest

from src.utils.metrics import (
    record_api_request,
    record_llm_request,
    record_circuit_breaker_state,
    record_rag_search,
    _normalize_endpoint,
)


class TestMetricsRecording:
    """Tests pour l'enregistrement des métriques."""

    def test_record_api_request(self):
        """Test l'enregistrement d'une requête API."""
        # Doit s'exécuter sans erreur
        record_api_request("GET", "/api/v1/query", 200, 0.5)
        record_api_request("POST", "/api/v1/query", 500, 1.2)

    def test_record_llm_request_success(self):
        """Test l'enregistrement d'une requête LLM réussie."""
        record_llm_request(
            provider="mistral",
            model="mistral-large-latest",
            status="success",
            duration=2.5,
            prompt_tokens=100,
            completion_tokens=200,
        )

    def test_record_llm_request_error(self):
        """Test l'enregistrement d'une requête LLM en erreur."""
        record_llm_request(
            provider="openai",
            model="gpt-4o",
            status="error",
            duration=0.1,
        )

    def test_record_circuit_breaker_state(self):
        """Test l'enregistrement de l'état du circuit breaker."""
        record_circuit_breaker_state("mistral", 0)  # CLOSED
        record_circuit_breaker_state("openai", 2)  # OPEN

    def test_record_rag_search(self):
        """Test l'enregistrement d'une recherche RAG."""
        record_rag_search(
            intent="documents",
            success=True,
            duration=0.5,
            docs_count=5,
        )


class TestEndpointNormalization:
    """Tests pour la normalisation des endpoints."""

    def test_normalize_uuid(self):
        """Test la normalisation des UUIDs."""
        endpoint = "/api/v1/keys/550e8400-e29b-41d4-a716-446655440000"
        normalized = _normalize_endpoint(endpoint)
        assert normalized == "/api/v1/keys/{id}"

    def test_normalize_numeric_id(self):
        """Test la normalisation des IDs numériques."""
        endpoint = "/api/v1/documents/12345"
        normalized = _normalize_endpoint(endpoint)
        assert normalized == "/api/v1/documents/{id}"

    def test_normalize_no_id(self):
        """Test qu'un endpoint sans ID reste inchangé."""
        endpoint = "/api/v1/query"
        normalized = _normalize_endpoint(endpoint)
        assert normalized == "/api/v1/query"

    def test_normalize_health(self):
        """Test que /health reste inchangé."""
        endpoint = "/health"
        normalized = _normalize_endpoint(endpoint)
        assert normalized == "/health"
