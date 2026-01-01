"""
Tests unitaires pour TraceService
==================================

Vérifie le logging des traces LLM et le calcul des coûts.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestEstimateCost:
    """Tests pour le calcul des coûts LLM."""

    def test_mistral_large_cost(self):
        """Test coût Mistral Large."""
        from src.services.trace_service import estimate_cost_cents
        
        # 1000 tokens input + 1000 tokens output
        cost = estimate_cost_cents("mistral-large-latest", 1000, 1000)
        
        # 0.4 + 1.2 = 1.6 centimes pour 1K tokens chaque
        assert cost == pytest.approx(1.6, rel=0.01)

    def test_gpt4o_mini_cost(self):
        """Test coût GPT-4o-mini (économique)."""
        from src.services.trace_service import estimate_cost_cents
        
        cost = estimate_cost_cents("gpt-4o-mini", 10000, 5000)
        
        # 10K * 0.015/1K + 5K * 0.06/1K = 0.15 + 0.3 = 0.45 centimes
        assert cost == pytest.approx(0.45, rel=0.01)

    def test_deepseek_cost(self):
        """Test coût DeepSeek (très économique)."""
        from src.services.trace_service import estimate_cost_cents
        
        cost = estimate_cost_cents("deepseek-chat", 10000, 10000)
        
        # 10K * 0.014/1K + 10K * 0.028/1K = 0.14 + 0.28 = 0.42 centimes
        assert cost == pytest.approx(0.42, rel=0.01)

    def test_unknown_model_uses_default(self):
        """Test qu'un modèle inconnu utilise les coûts par défaut."""
        from src.services.trace_service import estimate_cost_cents
        
        cost = estimate_cost_cents("unknown-model-xyz", 1000, 1000)
        
        # Default: 0.2 + 0.6 = 0.8 centimes
        assert cost == pytest.approx(0.8, rel=0.01)

    def test_zero_tokens_returns_zero(self):
        """Test avec 0 tokens."""
        from src.services.trace_service import estimate_cost_cents
        
        cost = estimate_cost_cents("mistral-large-latest", 0, 0)
        assert cost == 0


class TestTraceData:
    """Tests pour le dataclass TraceData."""

    def test_trace_data_required_fields(self):
        """Test création avec champs requis."""
        from src.services.trace_service import TraceData
        
        trace = TraceData(
            user_id="user_123",
            model_used="mistral-large-latest",
            status="success"
        )
        
        assert trace.user_id == "user_123"
        assert trace.model_used == "mistral-large-latest"
        assert trace.status == "success"
        assert trace.prompt_tokens == 0  # Default
        assert trace.agent_id is None  # Optional

    def test_trace_data_all_fields(self):
        """Test création avec tous les champs."""
        from src.services.trace_service import TraceData
        
        trace = TraceData(
            user_id="user_123",
            model_used="gpt-4o",
            status="error",
            agent_id="agent_456",
            api_key_id="key_789",
            prompt_tokens=500,
            completion_tokens=100,
            latency_ms=1500,
            query_preview="Test question?",
            error_message="Rate limit exceeded",
            error_code="rate_limited",
            routing_decision={"intent": "documents"},
            sources_count=3
        )
        
        assert trace.agent_id == "agent_456"
        assert trace.prompt_tokens == 500
        assert trace.error_message == "Rate limit exceeded"
        assert trace.sources_count == 3


class TestTraceService:
    """Tests pour le service de traces."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock du client Supabase."""
        with patch("src.services.trace_service.get_supabase_client") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    def test_log_trace_success(self, mock_supabase):
        """Test logging d'une trace avec succès."""
        from src.services.trace_service import TraceService, TraceData
        
        # Mock la réponse Supabase
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "trace_id_123"}
        ]
        
        service = TraceService()
        trace = TraceData(
            user_id="user_123",
            model_used="mistral-large-latest",
            status="success",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500
        )
        
        result = service.log_trace(trace)
        
        assert result == "trace_id_123"
        mock_supabase.table.assert_called_with("agent_traces")
        mock_supabase.table.return_value.insert.assert_called_once()

    def test_log_trace_handles_db_error(self, mock_supabase):
        """Test que les erreurs DB sont gérées gracieusement."""
        from src.services.trace_service import TraceService, TraceData
        
        mock_supabase.table.side_effect = Exception("DB Error")
        
        service = TraceService()
        trace = TraceData(
            user_id="user_123",
            model_used="mistral-large-latest",
            status="success"
        )
        
        result = service.log_trace(trace)
        
        assert result is None  # Ne lève pas d'exception

    def test_log_success_shortcut(self, mock_supabase):
        """Test le raccourci log_success."""
        from src.services.trace_service import TraceService
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "trace_123"}
        ]
        
        service = TraceService()
        result = service.log_success(
            user_id="user_123",
            model_used="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=800,
            sources_count=3
        )
        
        assert result == "trace_123"
        
        # Vérifier les données insérées
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args["status"] == "success"
        assert call_args["sources_count"] == 3

    def test_log_error_shortcut(self, mock_supabase):
        """Test le raccourci log_error."""
        from src.services.trace_service import TraceService
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "trace_456"}
        ]
        
        service = TraceService()
        result = service.log_error(
            user_id="user_123",
            model_used="gpt-4o",
            error_message="API timeout",
            error_code="timeout"
        )
        
        assert result == "trace_456"
        
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args["status"] == "error"
        assert call_args["error_message"] == "API timeout"
        assert call_args["error_code"] == "timeout"

    def test_query_preview_truncation(self, mock_supabase):
        """Test que query_preview est tronqué à 200 caractères."""
        from src.services.trace_service import TraceService, TraceData
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "trace_123"}
        ]
        
        service = TraceService()
        long_query = "A" * 300  # 300 caractères
        
        trace = TraceData(
            user_id="user_123",
            model_used="mistral-large-latest",
            status="success",
            query_preview=long_query
        )
        
        service.log_trace(trace)
        
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert len(call_args["query_preview"]) == 200
        assert call_args["query_preview"].endswith("...")


class TestTraceServiceSingleton:
    """Tests pour le singleton get_trace_service."""

    def test_singleton_returns_same_instance(self):
        """Test que get_trace_service retourne toujours la même instance."""
        with patch("src.services.trace_service.get_supabase_client"):
            # Reset le singleton
            import src.services.trace_service as module
            module._trace_service = None
            
            from src.services.trace_service import get_trace_service
            
            service1 = get_trace_service()
            service2 = get_trace_service()
            
            assert service1 is service2
