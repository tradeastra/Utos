"""
Unit tests for core modules.

This module contains unit tests for core functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from core.context import TradingContext, KernelContext, ProcessMemory
from core.types import TradingInstanceStatus, OrderSide, OrderType
from core.exceptions import UTOSException, ValidationError, AuthenticationError
from core.security import password_manager, token_manager, security_utils


class TestTradingContext:
    """Test TradingContext class."""
    
    def test_trading_context_creation(self):
        """Test creating a trading context."""
        context = TradingContext(
            instance_id="test-instance",
            user_id="test-user",
            exchange_name="binance",
            exchange_account_id="test-account",
            symbol="BTCUSDT",
            strategy_type="smart_grid",
            strategy_params={"grid_count": 10},
            total_investment=Decimal("1000.0")
        )
        
        assert context.instance_id == "test-instance"
        assert context.user_id == "test-user"
        assert context.exchange_name == "binance"
        assert context.symbol == "BTCUSDT"
        assert context.strategy_type == "smart_grid"
        assert context.strategy_params == {"grid_count": 10}
    
    def test_trading_context_immutable(self):
        """Test that trading context is immutable."""
        context = TradingContext(
            instance_id="test-instance",
            user_id="test-user",
            exchange_name="binance",
            exchange_account_id="test-account",
            symbol="BTCUSDT",
            strategy_type="smart_grid",
            strategy_params={}
        )
        
        # Should not be able to modify frozen dataclass
        with pytest.raises(Exception):
            context.instance_id = "new-instance"


class TestProcessMemory:
    """Test ProcessMemory class."""
    
    def test_process_memory_creation(self):
        """Test creating process memory."""
        memory = ProcessMemory(
            instance_id="test-instance",
            status=TradingInstanceStatus.CREATED
        )
        
        assert memory.instance_id == "test-instance"
        assert memory.status == TradingInstanceStatus.CREATED
        assert memory.current_price is None
        assert memory.active_orders == {}
    
    def test_process_memory_serialization(self):
        """Test process memory serialization."""
        memory = ProcessMemory(
            instance_id="test-instance",
            status=TradingInstanceStatus.RUNNING,
            current_price=Decimal("50000.0"),
            total_cycles=5,
            total_profit=Decimal("100.0")
        )
        
        # Test to_dict
        memory_dict = memory.to_dict()
        assert memory_dict["instance_id"] == "test-instance"
        assert memory_dict["status"] == "running"
        assert memory_dict["current_price"] == 50000.0
        assert memory_dict["total_cycles"] == 5
        assert memory_dict["total_profit"] == 100.0
        
        # Test from_dict
        restored_memory = ProcessMemory.from_dict(memory_dict)
        assert restored_memory.instance_id == "test-instance"
        assert restored_memory.status == TradingInstanceStatus.RUNNING
        assert restored_memory.current_price == Decimal("50000.0")
        assert restored_memory.total_cycles == 5
        assert restored_memory.total_profit == Decimal("100.0")


class TestExceptions:
    """Test custom exceptions."""
    
    def test_utos_exception(self):
        """Test UTOS base exception."""
        exc = UTOSException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test error"
    
    def test_validation_error(self):
        """Test validation error."""
        exc = ValidationError("Invalid input")
        
        assert isinstance(exc, UTOSException)
        assert exc.message == "Invalid input"
    
    def test_authentication_error(self):
        """Test authentication error."""
        exc = AuthenticationError("Invalid credentials")
        
        assert isinstance(exc, UTOSException)
        assert exc.message == "Invalid credentials"


class TestSecurity:
    """Test security utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "TestPassword123!"
        
        # Hash password
        hashed = password_manager.hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")
        
        # Verify password
        assert password_manager.verify_password(password, hashed) is True
        assert password_manager.verify_password("wrongpassword", hashed) is False
    
    def test_password_generation(self):
        """Test password generation."""
        password = password_manager.generate_password(12)
        
        assert len(password) == 12
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*" for c in password)
    
    def test_jwt_token_creation(self):
        """Test JWT token creation and verification."""
        data = {"sub": "user123", "email": "test@example.com"}
        
        # Create token
        token = token_manager.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        payload = token_manager.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_jwt_token_expiration(self):
        """Test JWT token expiration."""
        from datetime import timedelta
        
        data = {"sub": "user123"}
        
        # Create expired token
        token = token_manager.create_access_token(
            data,
            expires_delta=timedelta(seconds=-1)
        )
        
        # Should raise exception for expired token
        with pytest.raises(AuthenticationError):
            token_manager.verify_token(token)
    
    def test_email_validation(self):
        """Test email validation."""
        assert security_utils.validate_email("test@example.com") is True
        assert security_utils.validate_email("invalid-email") is False
        assert security_utils.validate_email("test@") is False
        assert security_utils.validate_email("@example.com") is False
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Strong password
        result = security_utils.validate_password_strength("StrongP@ss123!")
        assert result["is_valid"] is True
        assert result["score"] == 5
        assert len(result["errors"]) == 0
        
        # Weak password
        result = security_utils.validate_password_strength("weak")
        assert result["is_valid"] is False
        assert result["score"] == 0
        assert len(result["errors"]) > 0
    
    def test_input_sanitization(self):
        """Test input sanitization."""
        dirty_input = "<script>alert('xss')</script>"
        clean_input = security_utils.sanitize_input(dirty_input)
        
        assert "<script>" not in clean_input
        assert "</script>" not in clean_input
        assert "alert" in clean_input


class TestKernelContext:
    """Test KernelContext class."""
    
    def test_kernel_context_creation(self):
        """Test creating a kernel context."""
        mock_logger = object()
        mock_event_bus = object()
        mock_cache = object()
        mock_storage = object()
        
        context = KernelContext(
            logger=mock_logger,
            event_bus=mock_event_bus,
            cache=mock_cache,
            storage=mock_storage,
            config={"test": "value"}
        )
        
        assert context.logger is mock_logger
        assert context.event_bus is mock_event_bus
        assert context.cache is mock_cache
        assert context.storage is mock_storage
        assert context.config == {"test": "value"}
        assert context.is_shutting_down is False
