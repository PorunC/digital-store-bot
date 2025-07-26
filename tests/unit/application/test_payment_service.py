"""Unit tests for PaymentApplicationService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import pytest
from pytest_mock import MockerFixture

from src.application.services.payment_service import PaymentApplicationService
from src.domain.entities.order import Order, OrderStatus, PaymentMethod
from src.domain.value_objects.money import Money
from src.infrastructure.external.payment_gateways.base import PaymentData, PaymentResult, PaymentStatus
from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory


class TestPaymentApplicationService:
    """Test cases for PaymentApplicationService."""

    @pytest.fixture
    def mock_gateway_factory(self) -> Mock:
        """Create mock payment gateway factory."""
        return Mock(spec=PaymentGatewayFactory)

    @pytest.fixture
    def mock_unit_of_work(self) -> Mock:
        """Create mock unit of work."""
        uow = Mock()
        uow.session = Mock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.fixture
    def mock_order_repository(self) -> Mock:
        """Create mock order repository."""
        return Mock()

    @pytest.fixture
    def payment_service(
        self, 
        mock_gateway_factory: Mock, 
        mock_unit_of_work: Mock,
        mock_order_repository: Mock
    ) -> PaymentApplicationService:
        """Create payment service instance."""
        order_repo_factory = Mock(return_value=mock_order_repository)
        return PaymentApplicationService(
            payment_gateway_factory=mock_gateway_factory,
            unit_of_work=mock_unit_of_work,
            order_repository_factory=order_repo_factory
        )

    @pytest.fixture
    def sample_order(self) -> Order:
        """Create sample order for testing."""
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        
        return Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=Money(amount=100.0, currency="USD"),
            quantity=1
        )

    @pytest.fixture
    def mock_payment_gateway(self) -> Mock:
        """Create mock payment gateway."""
        gateway = Mock()
        gateway.create_payment = AsyncMock()
        gateway.get_payment_status = AsyncMock()
        gateway.validate_webhook = AsyncMock()
        gateway.extract_payment_info = AsyncMock()
        gateway.refund_payment = AsyncMock()
        gateway.get_config = AsyncMock()
        gateway.validate_amount = AsyncMock()
        return gateway

    async def test_create_payment_success(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_payment_gateway: Mock,
        mock_gateway_factory: Mock,
        sample_order: Order,
        mocker: MockerFixture
    ):
        """Test successful payment creation."""
        # Arrange
        order_id = str(sample_order.id)
        payment_method = PaymentMethod.CRYPTOMUS
        
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_order_repository.update = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        
        expected_result = PaymentResult(
            success=True,
            payment_id="test_payment_123",
            payment_url="https://payment.example.com/pay/123",
            external_payment_id="ext_123"
        )
        mock_payment_gateway.create_payment.return_value = expected_result
        
        # Mock event publishing
        mocker.patch('src.shared.events.event_bus.publish', new_callable=AsyncMock)

        # Act
        result = await payment_service.create_payment(
            order_id=order_id,
            payment_method=payment_method,
            return_url="https://example.com/return",
            metadata={"telegram_user_id": 123456}
        )

        # Assert
        assert result.success is True
        assert result.payment_id == "test_payment_123"
        assert result.payment_url == "https://payment.example.com/pay/123"
        
        # Verify gateway was called with correct data
        mock_payment_gateway.create_payment.assert_called_once()
        call_args = mock_payment_gateway.create_payment.call_args[0][0]
        assert isinstance(call_args, PaymentData)
        assert call_args.order_id == order_id
        assert call_args.amount == 100.0
        assert call_args.currency == "USD"
        assert call_args.user_telegram_id == 123456
        
        # Verify order was updated
        mock_order_repository.update.assert_called_once()
        updated_order = mock_order_repository.update.call_args[0][0]
        assert updated_order.payment_method == payment_method
        assert updated_order.payment_id == "test_payment_123"

    async def test_create_payment_order_not_found(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
    ):
        """Test payment creation with non-existent order."""
        # Arrange
        order_id = str(uuid.uuid4())
        mock_order_repository.get_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Order with ID .* not found"):
            await payment_service.create_payment(
                order_id=order_id,
                payment_method=PaymentMethod.CRYPTOMUS
            )

    async def test_create_payment_invalid_order_status(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        sample_order: Order
    ):
        """Test payment creation with invalid order status."""
        # Arrange
        sample_order.status = OrderStatus.PAID  # Invalid status for payment creation
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot create payment for order .* - invalid status"):
            await payment_service.create_payment(
                order_id=str(sample_order.id),
                payment_method=PaymentMethod.CRYPTOMUS
            )

    async def test_create_payment_gateway_not_available(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        sample_order: Order
    ):
        """Test payment creation when gateway is not available."""
        # Arrange
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Payment gateway for .* is not available"):
            await payment_service.create_payment(
                order_id=str(sample_order.id),
                payment_method=PaymentMethod.CRYPTOMUS
            )

    async def test_create_payment_gateway_failure(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order
    ):
        """Test payment creation when gateway returns failure."""
        # Arrange
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        
        failed_result = PaymentResult(
            success=False,
            error_message="Payment gateway error"
        )
        mock_payment_gateway.create_payment.return_value = failed_result

        # Act
        result = await payment_service.create_payment(
            order_id=str(sample_order.id),
            payment_method=PaymentMethod.CRYPTOMUS
        )

        # Assert
        assert result.success is False
        assert result.error_message == "Payment gateway error"
        
        # Verify order was not updated on failure
        mock_order_repository.update.assert_not_called()

    async def test_process_webhook_success(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order,
        mocker: MockerFixture
    ):
        """Test successful webhook processing."""
        # Arrange
        webhook_data = {"payment_id": "test_123", "status": "paid"}
        signature = "test_signature"
        
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.validate_webhook.return_value = True
        mock_payment_gateway.extract_payment_info.return_value = {
            "order_id": str(sample_order.id),
            "status": "paid",
            "external_payment_id": "ext_123"
        }
        
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_order_repository.update = AsyncMock(return_value=sample_order)
        
        # Mock event publishing
        mocker.patch('src.shared.events.event_bus.publish', new_callable=AsyncMock)

        # Act
        result = await payment_service.process_webhook(
            payment_method=PaymentMethod.CRYPTOMUS,
            webhook_data=webhook_data,
            signature=signature
        )

        # Assert
        assert result == sample_order
        assert sample_order.status == OrderStatus.PAID
        assert sample_order.paid_at is not None
        
        # Verify webhook validation was called
        mock_payment_gateway.validate_webhook.assert_called_once_with(webhook_data, signature)
        mock_order_repository.update.assert_called_once()

    async def test_process_webhook_invalid_signature(
        self,
        payment_service: PaymentApplicationService,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock
    ):
        """Test webhook processing with invalid signature."""
        # Arrange
        webhook_data = {"payment_id": "test_123"}
        signature = "invalid_signature"
        
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.validate_webhook.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid webhook signature"):
            await payment_service.process_webhook(
                payment_method=PaymentMethod.CRYPTOMUS,
                webhook_data=webhook_data,
                signature=signature
            )

    async def test_process_webhook_failed_payment(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order,
        mocker: MockerFixture
    ):
        """Test webhook processing for failed payment."""
        # Arrange
        webhook_data = {"payment_id": "test_123", "status": "failed"}
        
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.validate_webhook.return_value = True
        mock_payment_gateway.extract_payment_info.return_value = {
            "order_id": str(sample_order.id),
            "status": "failed",
            "error_message": "Insufficient funds"
        }
        
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_order_repository.update = AsyncMock(return_value=sample_order)
        
        # Mock event publishing
        mocker.patch('src.shared.events.event_bus.publish', new_callable=AsyncMock)

        # Act
        result = await payment_service.process_webhook(
            payment_method=PaymentMethod.CRYPTOMUS,
            webhook_data=webhook_data
        )

        # Assert
        assert result == sample_order
        assert sample_order.status == OrderStatus.CANCELLED
        assert sample_order.cancelled_at is not None
        assert "Payment failed: Insufficient funds" in (sample_order.notes or "")

    async def test_check_payment_status(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order
    ):
        """Test payment status checking."""
        # Arrange
        sample_order.payment_method = PaymentMethod.CRYPTOMUS
        sample_order.payment_id = "test_payment_123"
        sample_order.external_payment_id = "ext_123"
        sample_order.payment_gateway = "cryptomus"
        
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.get_payment_status.return_value = {
            "status": "completed",
            "amount": 100.0,
            "currency": "USD"
        }

        # Act
        result = await payment_service.check_payment_status(str(sample_order.id))

        # Assert
        assert result["order_id"] == str(sample_order.id)
        assert result["payment_id"] == "test_payment_123"
        assert result["external_payment_id"] == "ext_123"
        assert result["status"] == "completed"
        assert result["amount"] == 100.0
        assert result["currency"] == "USD"
        assert result["gateway"] == "cryptomus"

    async def test_check_payment_status_no_payment_info(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        sample_order: Order
    ):
        """Test payment status check when no payment info exists."""
        # Arrange
        sample_order.payment_id = None
        sample_order.payment_method = None
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)

        # Act
        result = await payment_service.check_payment_status(str(sample_order.id))

        # Assert
        assert result["status"] == "no_payment"
        assert "No payment information found" in result["message"]

    async def test_refund_payment_success(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order,
        mocker: MockerFixture
    ):
        """Test successful payment refund."""
        # Arrange
        sample_order.status = OrderStatus.PAID
        sample_order.payment_method = PaymentMethod.CRYPTOMUS
        sample_order.payment_id = "test_payment_123"
        
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_order_repository.update = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.refund_payment.return_value = {
            "success": True,
            "refund_id": "refund_123",
            "amount": 100.0
        }
        
        # Mock event publishing
        mocker.patch('src.shared.events.event_bus.publish', new_callable=AsyncMock)

        # Act
        result = await payment_service.refund_payment(
            order_id=str(sample_order.id),
            amount=100.0,
            reason="Customer request"
        )

        # Assert
        assert result["success"] is True
        assert result["refund_id"] == "refund_123"
        assert sample_order.status == OrderStatus.CANCELLED
        assert "Refunded: Customer request" in (sample_order.notes or "")

    async def test_refund_payment_invalid_status(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        sample_order: Order
    ):
        """Test refund attempt on unpaid order."""
        # Arrange
        sample_order.status = OrderStatus.PENDING  # Invalid status for refund
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot refund order .* - not paid"):
            await payment_service.refund_payment(str(sample_order.id))

    async def test_get_supported_payment_methods(
        self,
        payment_service: PaymentApplicationService,
        mock_gateway_factory: Mock
    ):
        """Test getting supported payment methods."""
        # Arrange
        expected_methods = [PaymentMethod.CRYPTOMUS, PaymentMethod.TELEGRAM_STARS]
        mock_gateway_factory.get_supported_methods.return_value = expected_methods

        # Act
        result = await payment_service.get_supported_payment_methods()

        # Assert
        assert result == expected_methods
        mock_gateway_factory.get_supported_methods.assert_called_once()

    async def test_validate_payment_amount(
        self,
        payment_service: PaymentApplicationService,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock
    ):
        """Test payment amount validation."""
        # Arrange
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        mock_payment_gateway.validate_amount.return_value = {"valid": True, "min_amount": 1.0}

        # Act
        result = await payment_service.validate_payment_amount(
            payment_method=PaymentMethod.CRYPTOMUS,
            amount=100.0,
            currency="USD"
        )

        # Assert
        assert result["valid"] is True
        assert result["min_amount"] == 1.0
        mock_payment_gateway.validate_amount.assert_called_once_with(100.0, "USD")

    async def test_get_payment_statistics(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        sample_order: Order
    ):
        """Test payment statistics retrieval."""
        # Arrange
        sample_order.payment_method = PaymentMethod.CRYPTOMUS
        sample_order.status = OrderStatus.PAID
        
        mock_order_repository.get_revenue_stats = AsyncMock(return_value={
            "total_revenue": 1000.0,
            "currency": "USD"
        })
        mock_order_repository.get_order_stats = AsyncMock(return_value={
            "total_orders": 10,
            "paid_orders": 8
        })
        mock_order_repository.get_all = AsyncMock(return_value=[sample_order])
        mock_gateway_factory.get_supported_methods.return_value = [PaymentMethod.CRYPTOMUS]

        # Act
        result = await payment_service.get_payment_statistics()

        # Assert
        assert "revenue" in result
        assert "orders" in result
        assert "payment_methods" in result
        assert "supported_methods" in result
        
        assert result["revenue"]["total_revenue"] == 1000.0
        assert result["orders"]["total_orders"] == 10
        assert PaymentMethod.CRYPTOMUS in result["payment_methods"]
        assert result["payment_methods"][PaymentMethod.CRYPTOMUS]["count"] == 1
        assert result["payment_methods"][PaymentMethod.CRYPTOMUS]["revenue"] == 100.0

    async def test_payment_service_fallback_repository_creation(
        self,
        mock_gateway_factory: Mock,
        mock_unit_of_work: Mock
    ):
        """Test fallback repository creation when factory is not provided."""
        # Arrange
        service = PaymentApplicationService(
            payment_gateway_factory=mock_gateway_factory,
            unit_of_work=mock_unit_of_work,
            order_repository_factory=None  # No factory provided
        )

        # Act & Assert
        with patch('src.infrastructure.database.repositories.order_repository.SqlAlchemyOrderRepository') as mock_repo_class:
            mock_repo_instance = Mock()
            mock_repo_class.return_value = mock_repo_instance
            
            repo = service._get_order_repository()
            
            assert repo == mock_repo_instance
            mock_repo_class.assert_called_once_with(mock_unit_of_work.session)

    async def test_payment_service_no_session_error(
        self,
        mock_gateway_factory: Mock
    ):
        """Test error when unit of work has no session."""
        # Arrange
        uow_no_session = Mock()
        uow_no_session.session = None
        
        service = PaymentApplicationService(
            payment_gateway_factory=mock_gateway_factory,
            unit_of_work=uow_no_session,
            order_repository_factory=None
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Unit of work session not available"):
            service._get_order_repository()

    async def test_create_payment_with_empty_metadata(
        self,
        payment_service: PaymentApplicationService,
        mock_order_repository: Mock,
        mock_gateway_factory: Mock,
        mock_payment_gateway: Mock,
        sample_order: Order,
        mocker: MockerFixture
    ):
        """Test payment creation with empty metadata."""
        # Arrange
        mock_order_repository.get_by_id = AsyncMock(return_value=sample_order)
        mock_order_repository.update = AsyncMock(return_value=sample_order)
        mock_gateway_factory.get_gateway.return_value = mock_payment_gateway
        
        expected_result = PaymentResult(success=True, payment_id="test_123")
        mock_payment_gateway.create_payment.return_value = expected_result
        
        mocker.patch('src.shared.events.event_bus.publish', new_callable=AsyncMock)

        # Act
        result = await payment_service.create_payment(
            order_id=str(sample_order.id),
            payment_method=PaymentMethod.CRYPTOMUS,
            metadata=None  # Test with None metadata
        )

        # Assert
        assert result.success is True
        
        # Verify gateway was called with default telegram_user_id
        call_args = mock_payment_gateway.create_payment.call_args[0][0]
        assert call_args.user_telegram_id == 0
        assert call_args.metadata == {}