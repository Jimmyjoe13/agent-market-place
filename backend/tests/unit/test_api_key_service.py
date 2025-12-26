"""
Tests unitaires pour ApiKeyService.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from src.services.api_key_service import (
    ApiKeyService,
    QuotaExceededError,
    CreateKeyResult,
)
from src.models.api_key import ApiKeyInfo, ApiKeyScope


class TestApiKeyServiceCreation:
    """Tests pour la création de clés API."""
    
    @pytest.fixture
    def mock_key_repo(self):
        """Mock du repository API Keys."""
        repo = Mock()
        repo.create.return_value = {
            "id": uuid4(),
            "name": "Test Key",
            "key": "sk-proj-abc123def456",
            "prefix": "sk-proj-abc",
            "scopes": ["query"],
            "rate_limit_per_minute": 100,
            "monthly_quota": 0,
            "monthly_usage": 0,
            "is_active": True,
            "expires_at": None,
            "last_used_at": None,
            "created_at": datetime.utcnow(),
        }
        return repo
    
    @pytest.fixture
    def mock_sub_repo(self):
        """Mock du repository Subscriptions."""
        repo = Mock()
        repo.check_user_limits.return_value = {
            "allowed": True,
            "reason": None,
        }
        return repo
    
    @pytest.fixture
    def service(self, mock_key_repo, mock_sub_repo):
        """Service avec mocks injectés."""
        return ApiKeyService(
            key_repo=mock_key_repo,
            sub_repo=mock_sub_repo,
        )
    
    @pytest.mark.asyncio
    async def test_create_key_success(self, service, mock_key_repo, mock_sub_repo):
        """Test création de clé réussie."""
        user_id = str(uuid4())
        
        result = await service.create_user_key(
            user_id=user_id,
            name="Production Key",
            scopes=["query", "feedback"],
        )
        
        assert isinstance(result, CreateKeyResult)
        assert result.raw_key.startswith("sk-proj-")
        assert result.key_info.name == "Test Key"
        assert result.key_info.is_active is True
        
        # Vérifier que le repo a été appelé
        mock_sub_repo.check_user_limits.assert_called_once_with(user_id, "api_key")
        mock_key_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_key_quota_exceeded(self, service, mock_sub_repo):
        """Test création bloquée par quota."""
        mock_sub_repo.check_user_limits.return_value = {
            "allowed": False,
            "reason": "api_keys_limit_reached",
        }
        
        with pytest.raises(QuotaExceededError) as exc_info:
            await service.create_user_key(
                user_id=str(uuid4()),
                name="Test",
                scopes=["query"],
            )
        
        assert "limite" in exc_info.value.message.lower()
        assert exc_info.value.limits["reason"] == "api_keys_limit_reached"
    
    @pytest.mark.asyncio
    async def test_create_key_filters_admin_scope(self, service, mock_key_repo):
        """Test que le scope admin est filtré."""
        await service.create_user_key(
            user_id=str(uuid4()),
            name="Test",
            scopes=["query", "admin", "feedback"],
        )
        
        # Vérifier que admin a été retiré
        call_args = mock_key_repo.create.call_args[0][0]
        assert "admin" not in call_args["scopes"]
        assert "query" in call_args["scopes"]
        assert "feedback" in call_args["scopes"]
    
    @pytest.mark.asyncio
    async def test_create_key_fallback_to_query(self, service, mock_key_repo):
        """Test fallback sur query si tous les scopes sont interdits."""
        await service.create_user_key(
            user_id=str(uuid4()),
            name="Test",
            scopes=["admin"],  # Seul scope interdit
        )
        
        call_args = mock_key_repo.create.call_args[0][0]
        assert call_args["scopes"] == ["query"]


class TestApiKeyServiceList:
    """Tests pour le listing des clés."""
    
    @pytest.fixture
    def service(self):
        """Service avec mocks."""
        key_repo = Mock()
        key_repo.list_keys.return_value = (
            [
                ApiKeyInfo(
                    id=uuid4(),
                    name="Key 1",
                    prefix="sk-proj-1",
                    scopes=["query"],
                    rate_limit_per_minute=100,
                    is_active=True,
                ),
                ApiKeyInfo(
                    id=uuid4(),
                    name="Key 2",
                    prefix="sk-proj-2",
                    scopes=["query", "feedback"],
                    rate_limit_per_minute=200,
                    is_active=True,
                ),
            ],
            2,
        )
        return ApiKeyService(key_repo=key_repo, sub_repo=Mock())
    
    def test_list_keys_returns_tuple(self, service):
        """Test que list_user_keys retourne un tuple."""
        keys, total = service.list_user_keys(user_id=str(uuid4()))
        
        assert isinstance(keys, list)
        assert len(keys) == 2
        assert total == 2
    
    def test_list_keys_pagination(self, service):
        """Test pagination."""
        service.list_user_keys(
            user_id=str(uuid4()),
            page=2,
            per_page=10,
        )
        
        # Vérifier les arguments de pagination
        call_kwargs = service._key_repo.list_keys.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["per_page"] == 10


class TestApiKeyServiceRevoke:
    """Tests pour la révocation de clés."""
    
    @pytest.fixture
    def service(self):
        """Service avec mocks."""
        key_repo = Mock()
        key_repo.get_by_id.return_value = ApiKeyInfo(
            id=uuid4(),
            name="Test",
            prefix="sk-proj-x",
            scopes=["query"],
            rate_limit_per_minute=100,
            is_active=True,
        )
        key_repo.revoke.return_value = True
        return ApiKeyService(key_repo=key_repo, sub_repo=Mock())
    
    def test_revoke_success(self, service):
        """Test révocation réussie."""
        result = service.revoke_user_key(
            user_id=str(uuid4()),
            key_id=str(uuid4()),
        )
        
        assert result is True
        service._key_repo.revoke.assert_called_once()
    
    def test_revoke_key_not_found(self, service):
        """Test révocation clé inexistante."""
        service._key_repo.get_by_id.return_value = None
        
        result = service.revoke_user_key(
            user_id=str(uuid4()),
            key_id=str(uuid4()),
        )
        
        assert result is False
        service._key_repo.revoke.assert_not_called()


class TestApiKeyServiceValidation:
    """Tests pour la validation de clés."""
    
    @pytest.fixture
    def service(self):
        """Service avec mocks."""
        from src.models.api_key import ApiKeyValidation
        
        key_repo = Mock()
        key_repo.validate.return_value = ApiKeyValidation(
            id=uuid4(),
            user_id=uuid4(),
            scopes=["query", "feedback"],
            rate_limit=100,
            is_valid=True,
        )
        return ApiKeyService(key_repo=key_repo, sub_repo=Mock())
    
    def test_validate_key_success(self, service):
        """Test validation réussie."""
        result = service.validate_key(
            raw_key="sk-proj-abc123",
            client_ip="127.0.0.1",
        )
        
        assert result is not None
        assert result["is_valid"] is True
        assert "query" in result["scopes"]
    
    def test_validate_key_invalid(self, service):
        """Test validation échouée."""
        service._key_repo.validate.return_value = None
        
        result = service.validate_key(raw_key="invalid-key")
        
        assert result is None
