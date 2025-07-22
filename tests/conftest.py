"""Pytest configuration and fixtures for testing."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.domain.entities.user import User, SubscriptionType
from src.domain.entities.product import Product, ProductCategory, ProductStatus
from src.domain.entities.order import Order, OrderStatus, PaymentMethod
from src.domain.value_objects.money import Money
from src.domain.value_objects.user_profile import UserProfile
from src.domain.value_objects.product_info import DeliveryType
from src.infrastructure.database.models.base import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "telegram_id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en"
    }


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "name": "Premium Subscription",
        "description": "Premium access for 30 days",
        "category": ProductCategory.SUBSCRIPTION,
        "price": Money(amount=29.99, currency="USD"),
        "duration_days": 30,
        "delivery_type": DeliveryType.AUTOMATIC,
        "stock": -1
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "product_name": "Premium Subscription",
        "product_description": "Premium access for 30 days",
        "amount": Money(amount=29.99, currency="USD"),
        "quantity": 1,
        "payment_method": PaymentMethod.TELEGRAM_STARS
    }


@pytest.fixture
def sample_user(sample_user_data) -> User:
    """Create a sample user entity."""
    return User.create(
        telegram_id=sample_user_data["telegram_id"],
        first_name=sample_user_data["first_name"],
        last_name=sample_user_data["last_name"],
        username=sample_user_data["username"],
        language_code=sample_user_data["language_code"]
    )


@pytest.fixture
def sample_product(sample_product_data) -> Product:
    """Create a sample product entity."""
    return Product.create(
        name=sample_product_data["name"],
        description=sample_product_data["description"],
        category=sample_product_data["category"],
        price=sample_product_data["price"],
        duration_days=sample_product_data["duration_days"],
        delivery_type=sample_product_data["delivery_type"],
        stock=sample_product_data["stock"]
    )


@pytest.fixture
def sample_order(sample_user, sample_product, sample_order_data) -> Order:
    """Create a sample order entity."""
    return Order.create(
        user_id=sample_user.id,
        product_id=sample_product.id,
        product_name=sample_order_data["product_name"],
        product_description=sample_order_data["product_description"],
        amount=sample_order_data["amount"],
        quantity=sample_order_data["quantity"],
        payment_method=sample_order_data["payment_method"]
    )


@pytest.fixture
def premium_user(sample_user_data) -> User:
    """Create a user with premium subscription."""
    user = User.create(
        telegram_id=sample_user_data["telegram_id"] + 1,
        first_name="Premium",
        last_name="User",
        username="premiumuser",
        language_code="en"
    )
    
    # Grant premium subscription
    user.extend_subscription(30, SubscriptionType.PREMIUM)
    return user


@pytest.fixture
def trial_user(sample_user_data) -> User:
    """Create a user with trial subscription."""
    user = User.create(
        telegram_id=sample_user_data["telegram_id"] + 2,
        first_name="Trial",
        last_name="User",
        username="trialuser",
        language_code="en"
    )
    
    # Start trial
    user.start_trial(7, SubscriptionType.TRIAL)
    return user


@pytest.fixture
def expired_product(sample_product_data) -> Product:
    """Create an expired/inactive product."""
    product = Product.create(
        name="Expired Product",
        description="This product is no longer available",
        category=sample_product_data["category"],
        price=sample_product_data["price"],
        duration_days=sample_product_data["duration_days"],
        delivery_type=sample_product_data["delivery_type"],
        stock=0
    )
    
    # Deactivate the product
    product.deactivate("Product discontinued")
    return product


@pytest.fixture
def completed_order(sample_user, sample_product, sample_order_data) -> Order:
    """Create a completed order."""
    order = Order.create(
        user_id=sample_user.id,
        product_id=sample_product.id,
        product_name=sample_order_data["product_name"],
        product_description=sample_order_data["product_description"],
        amount=sample_order_data["amount"],
        quantity=sample_order_data["quantity"],
        payment_method=sample_order_data["payment_method"]
    )
    
    # Complete the order
    order.mark_as_paid("test_payment_id")
    order.mark_as_completed("Test completion")
    
    return order


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update for testing handlers."""
    from unittest.mock import Mock
    from aiogram.types import Update, Message, User as TelegramUser, Chat
    
    telegram_user = TelegramUser(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en"
    )
    
    chat = Chat(
        id=123456789,
        type="private"
    )
    
    message = Message(
        message_id=1,
        date=datetime.utcnow(),
        chat=chat,
        from_user=telegram_user,
        text="/start"
    )
    
    update = Update(
        update_id=1,
        message=message
    )
    
    return update


@pytest.fixture
def mock_payment_gateway():
    """Mock payment gateway for testing."""
    from unittest.mock import AsyncMock
    
    gateway = AsyncMock()
    gateway.is_available.return_value = True
    gateway.is_enabled = True
    gateway.gateway_name = "Mock Gateway"
    
    return gateway


# Async test helpers
@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run_async


# Database test helpers
@pytest_asyncio.fixture
async def populated_db(db_session, sample_user, sample_product):
    """Database session with sample data."""
    from src.infrastructure.database.repositories import (
        SqlAlchemyUserRepository,
        SqlAlchemyProductRepository
    )
    
    user_repo = SqlAlchemyUserRepository(db_session)
    product_repo = SqlAlchemyProductRepository(db_session)
    
    # Add sample data
    await user_repo.add(sample_user)
    await product_repo.add(sample_product)
    await db_session.commit()
    
    return db_session


# Test data generators
@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(telegram_id=None, **kwargs):
        data = {
            "telegram_id": telegram_id or 123456789,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en"
        }
        data.update(kwargs)
        
        return User.create(**data)
    
    return _create_user


@pytest.fixture
def product_factory():
    """Factory for creating test products."""
    def _create_product(name=None, **kwargs):
        data = {
            "name": name or "Test Product",
            "description": "Test product description",
            "category": ProductCategory.SUBSCRIPTION,
            "price": Money(amount=29.99, currency="USD"),
            "duration_days": 30,
            "delivery_type": DeliveryType.AUTOMATIC,
            "stock": -1
        }
        data.update(kwargs)
        
        return Product.create(**data)
    
    return _create_product


# Mock configurations
@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "database": {
            "url": "sqlite+aiosqlite:///:memory:"
        },
        "telegram": {
            "token": "test_token",
            "webhook_url": "https://example.com/webhook"
        },
        "payment_gateways": {
            "cryptomus": {
                "enabled": True,
                "api_key": "test_api_key",
                "merchant_id": "test_merchant"
            },
            "telegram_stars": {
                "enabled": True
            }
        }
    }