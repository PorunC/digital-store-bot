"""Integration tests for payment flow."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

from src.application.services import (
    UserApplicationService,
    ProductApplicationService,
    OrderApplicationService,
    PaymentApplicationService
)
from src.domain.entities.order import OrderStatus, PaymentMethod
from src.domain.entities.product import ProductStatus
from src.infrastructure.external.payment_gateways.base import PaymentResult


class TestPaymentFlow:
    """Test complete payment flow integration."""
    
    @pytest.fixture
    async def services(self, db_session):
        """Create services with real database."""
        from src.infrastructure.database.repositories import (
            SqlAlchemyUserRepository,
            SqlAlchemyProductRepository,
            SqlAlchemyOrderRepository
        )
        from unittest.mock import Mock
        
        # Real repositories
        user_repo = SqlAlchemyUserRepository(db_session)
        product_repo = SqlAlchemyProductRepository(db_session)
        order_repo = SqlAlchemyOrderRepository(db_session)
        
        # Mock unit of work
        uow = Mock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        uow.commit = AsyncMock()
        
        # Mock payment gateway factory
        gateway_factory = Mock()
        
        # Create services
        user_service = UserApplicationService(user_repo, uow)
        product_service = ProductApplicationService(product_repo, uow)
        order_service = OrderApplicationService(order_repo, product_repo, user_repo, uow)
        payment_service = PaymentApplicationService(order_repo, gateway_factory, uow)
        
        return {
            "user": user_service,
            "product": product_service,
            "order": order_service,
            "payment": payment_service,
            "gateway_factory": gateway_factory
        }
    
    @pytest.mark.asyncio
    async def test_complete_payment_flow(
        self,
        services,
        sample_user_data,
        sample_product_data,
        db_session
    ):
        """Test complete payment flow from user registration to order completion."""
        
        # 1. Register user
        user = await services["user"].register_user(
            telegram_id=sample_user_data["telegram_id"],
            first_name=sample_user_data["first_name"],
            username=sample_user_data["username"],
            language_code=sample_user_data["language_code"]
        )
        
        assert user is not None
        assert user.telegram_id == sample_user_data["telegram_id"]
        await db_session.commit()
        
        # 2. Create product
        product = await services["product"].create_product(
            name=sample_product_data["name"],
            description=sample_product_data["description"],
            category=sample_product_data["category"],
            price_amount=sample_product_data["price"].amount,
            price_currency=sample_product_data["price"].currency,
            duration_days=sample_product_data["duration_days"],
            delivery_type=sample_product_data["delivery_type"],
            stock=sample_product_data["stock"]
        )
        
        assert product is not None
        assert product.name == sample_product_data["name"]
        assert product.status == ProductStatus.ACTIVE
        await db_session.commit()
        
        # 3. Create order
        order = await services["order"].create_order(
            user_id=str(user.id),
            product_id=str(product.id),
            quantity=1,
            payment_method=PaymentMethod.TELEGRAM_STARS
        )
        
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert order.user_id == user.id
        assert order.product_id == product.id
        await db_session.commit()
        
        # 4. Mock payment gateway
        mock_gateway = AsyncMock()
        mock_gateway.is_available.return_value = True
        mock_gateway.create_payment.return_value = PaymentResult(
            success=True,
            payment_id="test_payment_123",
            payment_url="https://example.com/pay",
            metadata={"order_id": str(order.id)}
        )
        services["gateway_factory"].get_gateway.return_value = mock_gateway
        
        # 5. Create payment
        payment_result = await services["payment"].create_payment(
            order_id=str(order.id),
            payment_method=PaymentMethod.TELEGRAM_STARS
        )
        
        assert payment_result.success
        assert payment_result.payment_id == "test_payment_123"
        assert payment_result.payment_url == "https://example.com/pay"
        
        # 6. Verify order was updated with payment info
        updated_order = await services["order"].get_order_by_id(str(order.id))
        assert updated_order.payment_id == "test_payment_123"
        assert updated_order.payment_url == "https://example.com/pay"
        assert updated_order.payment_method == PaymentMethod.TELEGRAM_STARS
        
        # 7. Mark order as paid
        paid_order = await services["order"].mark_as_paid(
            order_id=str(order.id),
            external_payment_id="external_123"
        )
        
        assert paid_order.status == OrderStatus.PAID
        assert paid_order.external_payment_id == "external_123"
        assert paid_order.paid_at is not None
        
        # 8. Complete the order
        completed_order = await services["order"].mark_as_completed(str(order.id))
        
        assert completed_order.status == OrderStatus.COMPLETED
        assert completed_order.completed_at is not None
        
        # 9. Verify user subscription was extended
        updated_user = await services["user"].get_user_by_id(str(user.id))
        assert updated_user.has_active_subscription()
        assert updated_user.total_spent > 0
    
    @pytest.mark.asyncio
    async def test_payment_failure_flow(
        self,
        services,
        sample_user_data,
        sample_product_data,
        db_session
    ):
        """Test payment failure flow."""
        
        # Setup user and product
        user = await services["user"].register_user(**sample_user_data)
        await db_session.commit()
        
        product = await services["product"].create_product(
            name="Test Product",
            description="Test",
            category=sample_product_data["category"],
            price_amount=29.99,
            price_currency="USD",
            duration_days=30,
            delivery_type=sample_product_data["delivery_type"]
        )
        await db_session.commit()
        
        # Create order
        order = await services["order"].create_order(
            user_id=str(user.id),
            product_id=str(product.id),
            quantity=1
        )
        await db_session.commit()
        
        # Mock failed payment
        mock_gateway = AsyncMock()
        mock_gateway.is_available.return_value = True
        mock_gateway.create_payment.return_value = PaymentResult(
            success=False,
            error_message="Payment gateway error"
        )
        services["gateway_factory"].get_gateway.return_value = mock_gateway
        
        # Attempt payment
        payment_result = await services["payment"].create_payment(
            order_id=str(order.id),
            payment_method=PaymentMethod.CRYPTOMUS
        )
        
        assert not payment_result.success
        assert "error" in payment_result.error_message.lower()
        
        # Order should still be pending
        updated_order = await services["order"].get_order_by_id(str(order.id))
        assert updated_order.status == OrderStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_order_expiration_flow(
        self,
        services,
        sample_user_data,
        sample_product_data,
        db_session
    ):
        """Test order expiration flow."""
        
        # Setup user and product
        user = await services["user"].register_user(**sample_user_data)
        product = await services["product"].create_product(
            name="Expiring Product",
            description="Test",
            category=sample_product_data["category"],
            price_amount=19.99,
            price_currency="USD",
            duration_days=30,
            delivery_type=sample_product_data["delivery_type"],
            stock=5  # Limited stock
        )
        await db_session.commit()
        
        # Create order
        order = await services["order"].create_order(
            user_id=str(user.id),
            product_id=str(product.id),
            quantity=1
        )
        await db_session.commit()
        
        # Verify stock was reduced
        updated_product = await services["product"].get_product_by_id(str(product.id))
        assert updated_product.stock == 4  # Should be reduced by 1
        
        # Expire the order
        expired_order = await services["order"].expire_order(str(order.id))
        
        assert expired_order.status == OrderStatus.CANCELLED
        assert expired_order.cancelled_at is not None
        
        # Verify stock was restored
        restored_product = await services["product"].get_product_by_id(str(product.id))
        assert restored_product.stock == 5  # Should be restored
    
    @pytest.mark.asyncio
    async def test_insufficient_stock_flow(
        self,
        services,
        sample_user_data,
        sample_product_data,
        db_session
    ):
        """Test order creation with insufficient stock."""
        
        # Setup user and low-stock product
        user = await services["user"].register_user(**sample_user_data)
        product = await services["product"].create_product(
            name="Low Stock Product",
            description="Test",
            category=sample_product_data["category"],
            price_amount=39.99,
            price_currency="USD",
            duration_days=30,
            delivery_type=sample_product_data["delivery_type"],
            stock=1  # Only 1 in stock
        )
        await db_session.commit()
        
        # First order should succeed
        order1 = await services["order"].create_order(
            user_id=str(user.id),
            product_id=str(product.id),
            quantity=1
        )
        assert order1.status == OrderStatus.PENDING
        
        # Second order should fail due to insufficient stock
        with pytest.raises(ValueError, match="Insufficient stock"):
            await services["order"].create_order(
                user_id=str(user.id),
                product_id=str(product.id),
                quantity=1
            )