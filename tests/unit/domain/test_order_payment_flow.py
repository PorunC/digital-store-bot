"""Unit tests for Order entity payment flow."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.domain.entities.order import Order, OrderStatus, PaymentMethod
from src.domain.value_objects.money import Money
from src.domain.events.order_events import OrderCreated, PaymentReceived, OrderCompleted, OrderCancelled, OrderRefunded


class TestOrderPaymentFlow:
    """Test cases for Order entity payment flow."""

    @pytest.fixture
    def user_id(self) -> uuid.UUID:
        """Create user ID for testing."""
        return uuid.uuid4()

    @pytest.fixture
    def product_id(self) -> uuid.UUID:
        """Create product ID for testing."""
        return uuid.uuid4()

    @pytest.fixture
    def money(self) -> Money:
        """Create money value object for testing."""
        return Money(amount=100.0, currency="USD")

    @pytest.fixture
    def basic_order(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money) -> Order:
        """Create basic order for testing."""
        return Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=money,
            quantity=1
        )

    def test_order_creation(self, basic_order: Order, user_id: uuid.UUID, product_id: uuid.UUID):
        """Test order creation with domain events."""
        # Assert order properties
        assert basic_order.user_id == user_id
        assert basic_order.product_id == product_id
        assert basic_order.product_name == "Test Product"
        assert basic_order.amount.amount == 100.0
        assert basic_order.amount.currency == "USD"
        assert basic_order.status == OrderStatus.PENDING
        assert basic_order.quantity == 1
        assert basic_order.is_trial is False

        # Assert domain events
        events = basic_order.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], OrderCreated)
        assert events[0].order_id == str(basic_order.id)
        assert events[0].user_id == str(user_id)
        assert events[0].amount == 100.0

    def test_order_creation_with_optional_fields(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test order creation with optional fields."""
        referrer_id = uuid.uuid4()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=money,
            quantity=2,
            referrer_id=referrer_id,
            promocode="DISCOUNT10",
            is_trial=True,
            is_extend=True,
            expires_at=expires_at
        )

        assert order.quantity == 2
        assert order.referrer_id == referrer_id
        assert order.promocode == "DISCOUNT10"
        assert order.is_trial is True
        assert order.is_extend is True
        assert order.expires_at == expires_at

    def test_set_payment_details(self, basic_order: Order):
        """Test setting payment details."""
        # Act
        basic_order.set_payment_details(
            payment_method=PaymentMethod.CRYPTOMUS,
            payment_gateway="cryptomus",
            payment_id="payment_123",
            external_payment_id="ext_123",
            payment_url="https://pay.example.com/123"
        )

        # Assert
        assert basic_order.payment_method == PaymentMethod.CRYPTOMUS
        assert basic_order.payment_gateway == "cryptomus"
        assert basic_order.payment_id == "payment_123"
        assert basic_order.external_payment_id == "ext_123"
        assert basic_order.payment_url == "https://pay.example.com/123"

    def test_set_payment_details_invalid_status(self, basic_order: Order):
        """Test setting payment details on non-pending order."""
        # Arrange
        basic_order.status = OrderStatus.PAID

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot set payment details for non-pending order"):
            basic_order.set_payment_details(
                payment_method=PaymentMethod.CRYPTOMUS,
                payment_gateway="cryptomus",
                payment_id="payment_123"
            )

    def test_mark_as_processing(self, basic_order: Order):
        """Test marking order as processing."""
        # Act
        basic_order.mark_as_processing()

        # Assert
        assert basic_order.status == OrderStatus.PROCESSING

    def test_mark_as_processing_invalid_status(self, basic_order: Order):
        """Test marking non-pending order as processing."""
        # Arrange
        basic_order.status = OrderStatus.PAID

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot mark order as processing from status"):
            basic_order.mark_as_processing()

    def test_mark_as_paid_from_pending(self, basic_order: Order):
        """Test marking pending order as paid."""
        # Act
        basic_order.mark_as_paid("external_payment_123")

        # Assert
        assert basic_order.status == OrderStatus.PAID
        assert basic_order.paid_at is not None
        assert basic_order.external_payment_id == "external_payment_123"
        
        # Check domain events
        events = basic_order.get_domain_events()
        payment_events = [e for e in events if isinstance(e, PaymentReceived)]
        assert len(payment_events) == 1
        assert payment_events[0].order_id == str(basic_order.id)
        assert payment_events[0].amount == 100.0

    def test_mark_as_paid_from_processing(self, basic_order: Order):
        """Test marking processing order as paid."""
        # Arrange
        basic_order.mark_as_processing()
        basic_order.clear_domain_events()  # Clear creation events

        # Act
        basic_order.mark_as_paid("external_payment_123")

        # Assert
        assert basic_order.status == OrderStatus.PAID
        assert basic_order.paid_at is not None

    def test_mark_as_paid_invalid_status(self, basic_order: Order):
        """Test marking non-pending/processing order as paid."""
        # Arrange
        basic_order.status = OrderStatus.COMPLETED

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot mark order as paid from status"):
            basic_order.mark_as_paid()

    def test_complete_order(self, basic_order: Order):
        """Test completing paid order."""
        # Arrange
        basic_order.mark_as_paid()
        basic_order.clear_domain_events()

        # Act
        basic_order.complete("Product delivered successfully")

        # Assert
        assert basic_order.status == OrderStatus.COMPLETED
        assert basic_order.completed_at is not None
        assert "Product delivered successfully" in basic_order.notes

        # Check domain events
        events = basic_order.get_domain_events()
        completion_events = [e for e in events if isinstance(e, OrderCompleted)]
        assert len(completion_events) == 1
        assert completion_events[0].order_id == str(basic_order.id)

    def test_complete_unpaid_order(self, basic_order: Order):
        """Test completing unpaid order."""
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot complete unpaid order"):
            basic_order.complete()

    def test_cancel_order(self, basic_order: Order):
        """Test cancelling order."""
        # Act
        basic_order.cancel("Customer request")

        # Assert
        assert basic_order.status == OrderStatus.CANCELLED
        assert basic_order.cancelled_at is not None
        assert "Customer request" in basic_order.notes

        # Check domain events
        events = basic_order.get_domain_events()
        cancellation_events = [e for e in events if isinstance(e, OrderCancelled)]
        assert len(cancellation_events) == 1
        assert cancellation_events[0].reason == "Customer request"

    def test_cancel_completed_order(self, basic_order: Order):
        """Test cancelling completed order."""
        # Arrange
        basic_order.mark_as_paid()
        basic_order.complete()

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot cancel order with status"):
            basic_order.cancel()

    def test_refund_order(self, basic_order: Order):
        """Test refunding paid order."""
        # Arrange
        basic_order.mark_as_paid()
        basic_order.clear_domain_events()

        # Act
        basic_order.refund("Product defective")

        # Assert
        assert basic_order.status == OrderStatus.REFUNDED
        assert "Product defective" in basic_order.notes

        # Check domain events
        events = basic_order.get_domain_events()
        refund_events = [e for e in events if isinstance(e, OrderRefunded)]
        assert len(refund_events) == 1
        assert refund_events[0].reason == "Product defective"
        assert refund_events[0].amount == 100.0

    def test_refund_completed_order(self, basic_order: Order):
        """Test refunding completed order."""
        # Arrange
        basic_order.mark_as_paid()
        basic_order.complete()
        basic_order.clear_domain_events()

        # Act
        basic_order.refund("Customer complaint")

        # Assert
        assert basic_order.status == OrderStatus.REFUNDED

    def test_refund_pending_order(self, basic_order: Order):
        """Test refunding pending order."""
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot refund order with status"):
            basic_order.refund()

    def test_expire_order(self, basic_order: Order):
        """Test expiring pending order."""
        # Act
        basic_order.expire()

        # Assert
        assert basic_order.status == OrderStatus.FAILED
        assert "expired at" in basic_order.notes

    def test_expire_non_pending_order(self, basic_order: Order):
        """Test expiring non-pending order."""
        # Arrange
        basic_order.mark_as_paid()

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot expire order with status"):
            basic_order.expire()

    def test_fail_order(self, basic_order: Order):
        """Test failing order."""
        # Act
        basic_order.fail("Payment gateway error")

        # Assert
        assert basic_order.status == OrderStatus.FAILED
        assert "Payment gateway error" in basic_order.notes

    def test_order_expiration_check(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test order expiration checking."""
        # Test with future expiration
        future_time = datetime.utcnow() + timedelta(hours=1)
        order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=money,
            expires_at=future_time
        )
        assert order.is_expired is False

        # Test with past expiration
        past_time = datetime.utcnow() - timedelta(hours=1)
        order.expires_at = past_time
        assert order.is_expired is True

        # Test with no expiration
        order.expires_at = None
        assert order.is_expired is False

    def test_order_payment_capabilities(self, basic_order: Order):
        """Test order payment capability checks."""
        # Test pending order
        assert basic_order.can_be_paid is True
        assert basic_order.can_be_cancelled is True
        assert basic_order.can_be_refunded is False

        # Test paid order
        basic_order.mark_as_paid()
        assert basic_order.can_be_paid is False
        assert basic_order.can_be_cancelled is True
        assert basic_order.can_be_refunded is True

        # Test completed order
        basic_order.complete()
        assert basic_order.can_be_paid is False
        assert basic_order.can_be_cancelled is False
        assert basic_order.can_be_refunded is True

        # Test cancelled order
        basic_order.status = OrderStatus.CANCELLED
        assert basic_order.can_be_paid is False
        assert basic_order.can_be_cancelled is False
        assert basic_order.can_be_refunded is False

    def test_expired_order_payment_capability(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test payment capability for expired order."""
        # Create expired order
        past_time = datetime.utcnow() - timedelta(hours=1)
        order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=money,
            expires_at=past_time
        )

        # Test that expired order cannot be paid
        assert order.can_be_paid is False

    def test_total_amount_calculation(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test total amount calculation with quantity."""
        # Create order with quantity > 1
        order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Test Product",
            product_description="Test Description",
            amount=money,
            quantity=3
        )

        # Test total amount calculation
        total = order.total_amount
        assert total.amount == 300.0  # 100.0 * 3
        assert total.currency == "USD"

    def test_set_expiration(self, basic_order: Order):
        """Test setting order expiration."""
        # Test setting expiration on pending order
        future_time = datetime.utcnow() + timedelta(hours=2)
        basic_order.set_expiration(future_time)
        assert basic_order.expires_at == future_time

    def test_set_expiration_non_pending_order(self, basic_order: Order):
        """Test setting expiration on non-pending order."""
        # Arrange
        basic_order.mark_as_paid()
        future_time = datetime.utcnow() + timedelta(hours=2)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot set expiration for order with status"):
            basic_order.set_expiration(future_time)

    def test_add_note(self, basic_order: Order):
        """Test adding notes to order."""
        # Test adding first note
        basic_order.add_note("First note")
        assert "First note" in basic_order.notes

        # Test adding second note
        basic_order.add_note("Second note")
        assert "First note" in basic_order.notes
        assert "Second note" in basic_order.notes

    def test_domain_events_management(self, basic_order: Order):
        """Test domain events management."""
        # Test initial events from creation
        events = basic_order.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], OrderCreated)

        # Test clearing events
        basic_order.clear_domain_events()
        events = basic_order.get_domain_events()
        assert len(events) == 0

        # Test new events after operations
        basic_order.mark_as_paid()
        events = basic_order.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], PaymentReceived)

    def test_order_state_transitions(self, basic_order: Order):
        """Test complete order state transition flow."""
        # Initial state
        assert basic_order.status == OrderStatus.PENDING

        # Set payment details
        basic_order.set_payment_details(
            payment_method=PaymentMethod.CRYPTOMUS,
            payment_gateway="cryptomus",
            payment_id="payment_123"
        )

        # Mark as processing
        basic_order.mark_as_processing()
        assert basic_order.status == OrderStatus.PROCESSING

        # Mark as paid
        basic_order.mark_as_paid("external_123")
        assert basic_order.status == OrderStatus.PAID
        assert basic_order.paid_at is not None

        # Complete order
        basic_order.complete("Delivered successfully")
        assert basic_order.status == OrderStatus.COMPLETED
        assert basic_order.completed_at is not None

    def test_order_cancellation_flow(self, basic_order: Order):
        """Test order cancellation at different stages."""
        # Cancel pending order
        pending_order = Order.create(
            user_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            product_name="Test Product",
            product_description="Test Description",
            amount=Money(amount=50.0, currency="USD")
        )
        pending_order.cancel("User cancelled")
        assert pending_order.status == OrderStatus.CANCELLED

        # Cancel paid order
        paid_order = Order.create(
            user_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            product_name="Test Product",
            product_description="Test Description",
            amount=Money(amount=75.0, currency="USD")
        )
        paid_order.mark_as_paid()
        paid_order.cancel("Admin cancelled")
        assert paid_order.status == OrderStatus.CANCELLED

    def test_multiple_quantity_order_flow(self, user_id: uuid.UUID, product_id: uuid.UUID):
        """Test order flow with multiple quantity."""
        money = Money(amount=25.0, currency="USD")
        order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Bulk Product",
            product_description="Bulk order test",
            amount=money,
            quantity=4
        )

        # Test properties
        assert order.quantity == 4
        assert order.total_amount.amount == 100.0  # 25.0 * 4
        
        # Test normal flow
        order.mark_as_paid()
        order.complete("Bulk delivery completed")
        assert order.status == OrderStatus.COMPLETED

    def test_trial_order_flow(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test trial order specific flow."""
        trial_order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Trial Product",
            product_description="Trial subscription",
            amount=money,
            is_trial=True
        )

        # Test trial properties
        assert trial_order.is_trial is True
        
        # Check domain event includes trial flag
        events = trial_order.get_domain_events()
        creation_event = events[0]
        assert isinstance(creation_event, OrderCreated)
        assert creation_event.is_trial is True

    def test_extend_order_flow(self, user_id: uuid.UUID, product_id: uuid.UUID, money: Money):
        """Test extend order specific flow."""
        extend_order = Order.create(
            user_id=user_id,
            product_id=product_id,
            product_name="Extend Product",
            product_description="Subscription extension",
            amount=money,
            is_extend=True
        )

        # Test extend properties
        assert extend_order.is_extend is True
        
        # Test normal payment flow still works
        extend_order.mark_as_paid()
        extend_order.complete("Extension applied")
        assert extend_order.status == OrderStatus.COMPLETED