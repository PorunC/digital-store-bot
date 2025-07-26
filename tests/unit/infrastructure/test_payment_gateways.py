"""Unit tests for payment gateways."""

import uuid
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import pytest
from pytest_mock import MockerFixture

from src.infrastructure.external.payment_gateways.base import (
    PaymentGateway, PaymentData, PaymentResult, PaymentStatus, WebhookData
)
from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
from src.infrastructure.external.payment_gateways.cryptomus import CryptomusGateway
from src.infrastructure.external.payment_gateways.telegram_stars import TelegramStarsGateway
from src.domain.entities.order import PaymentMethod


class TestPaymentGatewayBase:
    """Test cases for base PaymentGateway class."""

    @pytest.fixture
    def base_gateway_config(self) -> Dict[str, Any]:
        """Create base gateway configuration."""
        return {
            "enabled": True,
            "api_key": "test_key",
            "merchant_id": "test_merchant"
        }

    def test_base_gateway_initialization(self, base_gateway_config: Dict[str, Any]):
        """Test base gateway initialization."""
        # Create a concrete implementation for testing
        class TestGateway(PaymentGateway):
            @property
            def gateway_name(self) -> str:
                return "test_gateway"
            
            @property
            def payment_method(self) -> PaymentMethod:
                return PaymentMethod.MANUAL
            
            async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
                return PaymentResult(success=True)
            
            async def get_payment_status(self, payment_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, webhook_data: dict) -> WebhookData:
                return None

        gateway = TestGateway(base_gateway_config)
        
        assert gateway.config == base_gateway_config
        assert gateway.is_enabled is True
        assert gateway.is_available() is True
        assert gateway.gateway_name == "test_gateway"
        assert gateway.payment_method == PaymentMethod.MANUAL

    def test_base_gateway_disabled(self):
        """Test base gateway when disabled."""
        config = {"enabled": False}
        
        class TestGateway(PaymentGateway):
            @property
            def gateway_name(self) -> str:
                return "test_gateway"
            
            @property
            def payment_method(self) -> PaymentMethod:
                return PaymentMethod.MANUAL
            
            async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
                return PaymentResult(success=True)
            
            async def get_payment_status(self, payment_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, webhook_data: dict) -> WebhookData:
                return None

        gateway = TestGateway(config)
        
        assert gateway.is_enabled is False
        assert gateway.is_available() is False

    async def test_base_gateway_optional_methods(self, base_gateway_config: Dict[str, Any]):
        """Test base gateway optional method implementations."""
        class TestGateway(PaymentGateway):
            @property
            def gateway_name(self) -> str:
                return "test_gateway"
            
            @property
            def payment_method(self) -> PaymentMethod:
                return PaymentMethod.MANUAL
            
            async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
                return PaymentResult(success=True)
            
            async def get_payment_status(self, payment_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, webhook_data: dict) -> WebhookData:
                return None

        gateway = TestGateway(base_gateway_config)
        
        # Test optional methods with default implementations
        assert await gateway.cancel_payment("test_id") is False
        
        refund_result = await gateway.refund_payment("test_id", 100.0, "test reason")
        assert refund_result["success"] is False
        assert "not supported" in refund_result["message"]
        
        assert await gateway.validate_webhook({}, "signature") is True
        assert await gateway.extract_payment_info({}) == {}
        
        config = await gateway.get_config()
        assert config["enabled"] is True
        
        validation = await gateway.validate_amount(100.0, "USD")
        assert validation["valid"] is True
        
        assert gateway.validate_webhook_signature({}, "signature") is True
        
        currencies = gateway.get_supported_currencies()
        assert "USD" in currencies
        assert "EUR" in currencies
        assert "RUB" in currencies
        
        formatted = gateway.format_amount(100.50, "USD")
        assert formatted == "100.50 USD"


class TestCryptomusGateway:
    """Test cases for CryptomusGateway."""

    @pytest.fixture
    def cryptomus_config(self) -> Dict[str, Any]:
        """Create Cryptomus gateway configuration."""
        return {
            "enabled": True,
            "api_key": "test_api_key",
            "merchant_id": "test_merchant_id",
            "api_url": "https://api.cryptomus.com/v1"
        }

    @pytest.fixture
    def cryptomus_gateway(self, cryptomus_config: Dict[str, Any]) -> CryptomusGateway:
        """Create Cryptomus gateway instance."""
        return CryptomusGateway(cryptomus_config)

    @pytest.fixture
    def payment_data(self) -> PaymentData:
        """Create sample payment data."""
        return PaymentData(
            order_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            product_id=str(uuid.uuid4()),
            amount=100.0,
            currency="USD",
            description="Test payment",
            user_telegram_id=123456,
            webhook_url="https://example.com/webhook",
            return_url="https://example.com/return"
        )

    async def test_cryptomus_create_payment_success(
        self,
        cryptomus_gateway: CryptomusGateway,
        payment_data: PaymentData,
        mocker: MockerFixture
    ):
        """Test successful payment creation with Cryptomus."""
        # Mock the HTTP request
        mock_response = {
            "result": {
                "uuid": "crypto_payment_123",
                "url": "https://cryptomus.com/pay/123"
            }
        }
        
        mock_post = mocker.patch('aiohttp.ClientSession.post')
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        mock_post.return_value.__aenter__.return_value.status = 200

        # Act
        result = await cryptomus_gateway.create_payment(payment_data)

        # Assert
        assert result.success is True
        assert result.payment_id == "crypto_payment_123"
        assert result.payment_url == "https://cryptomus.com/pay/123"
        assert result.external_payment_id == "crypto_payment_123"

    async def test_cryptomus_create_payment_api_error(
        self,
        cryptomus_gateway: CryptomusGateway,
        payment_data: PaymentData,
        mocker: MockerFixture
    ):
        """Test payment creation failure with Cryptomus API error."""
        # Mock the HTTP request failure
        mock_post = mocker.patch('aiohttp.ClientSession.post')
        mock_post.return_value.__aenter__.return_value.status = 400
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
            "errors": ["Invalid merchant ID"]
        })

        # Act
        result = await cryptomus_gateway.create_payment(payment_data)

        # Assert
        assert result.success is False
        assert "API request failed" in result.error_message

    async def test_cryptomus_get_payment_status(
        self,
        cryptomus_gateway: CryptomusGateway,
        mocker: MockerFixture
    ):
        """Test payment status retrieval from Cryptomus."""
        # Mock the HTTP request
        mock_response = {
            "result": {
                "status": "paid",
                "amount": "100.00",
                "currency": "USD"
            }
        }
        
        mock_post = mocker.patch('aiohttp.ClientSession.post')
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        mock_post.return_value.__aenter__.return_value.status = 200

        # Act
        status = await cryptomus_gateway.get_payment_status("test_payment_id")

        # Assert
        assert status == PaymentStatus.COMPLETED

    async def test_cryptomus_handle_webhook(
        self,
        cryptomus_gateway: CryptomusGateway
    ):
        """Test webhook handling for Cryptomus."""
        # Arrange
        webhook_data = {
            "uuid": "crypto_payment_123",
            "order_id": "order_456",
            "status": "paid",
            "amount": "100.00",
            "currency": "USD"
        }

        # Act
        result = await cryptomus_gateway.handle_webhook(webhook_data)

        # Assert
        assert result is not None
        assert result.payment_id == "crypto_payment_123"
        assert result.status == PaymentStatus.COMPLETED
        assert result.amount == 100.0
        assert result.currency == "USD"

    async def test_cryptomus_validate_webhook_signature(
        self,
        cryptomus_gateway: CryptomusGateway,
        mocker: MockerFixture
    ):
        """Test webhook signature validation for Cryptomus."""
        # Mock signature validation
        mocker.patch.object(cryptomus_gateway, '_generate_signature', return_value="valid_signature")
        
        webhook_data = {"test": "data"}
        signature = "valid_signature"

        # Act
        is_valid = await cryptomus_gateway.validate_webhook(webhook_data, signature)

        # Assert
        assert is_valid is True

    async def test_cryptomus_invalid_webhook_signature(
        self,
        cryptomus_gateway: CryptomusGateway,
        mocker: MockerFixture
    ):
        """Test invalid webhook signature for Cryptomus."""
        # Mock signature validation
        mocker.patch.object(cryptomus_gateway, '_generate_signature', return_value="valid_signature")
        
        webhook_data = {"test": "data"}
        signature = "invalid_signature"

        # Act
        is_valid = await cryptomus_gateway.validate_webhook(webhook_data, signature)

        # Assert
        assert is_valid is False


class TestTelegramStarsGateway:
    """Test cases for TelegramStarsGateway."""

    @pytest.fixture
    def telegram_stars_config(self) -> Dict[str, Any]:
        """Create Telegram Stars gateway configuration."""
        return {
            "enabled": True,
            "bot_token": "test_bot_token"
        }

    @pytest.fixture
    def telegram_stars_gateway(self, telegram_stars_config: Dict[str, Any]) -> TelegramStarsGateway:
        """Create Telegram Stars gateway instance."""
        return TelegramStarsGateway(telegram_stars_config)

    @pytest.fixture
    def payment_data(self) -> PaymentData:
        """Create sample payment data for Telegram Stars."""
        return PaymentData(
            order_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            product_id=str(uuid.uuid4()),
            amount=100.0,
            currency="XTR",  # Telegram Stars use XTR currency
            description="Test payment",
            user_telegram_id=123456
        )

    async def test_telegram_stars_create_payment_success(
        self,
        telegram_stars_gateway: TelegramStarsGateway,
        payment_data: PaymentData,
        mocker: MockerFixture
    ):
        """Test successful payment creation with Telegram Stars."""
        # Mock the Telegram Bot API request
        mock_response = {
            "ok": True,
            "result": {
                "invoice_link": "https://t.me/invoice/123"
            }
        }
        
        mock_post = mocker.patch('aiohttp.ClientSession.post')
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        mock_post.return_value.__aenter__.return_value.status = 200

        # Act
        result = await telegram_stars_gateway.create_payment(payment_data)

        # Assert
        assert result.success is True
        assert result.payment_url == "https://t.me/invoice/123"
        assert result.payment_id is not None

    async def test_telegram_stars_create_payment_api_error(
        self,
        telegram_stars_gateway: TelegramStarsGateway,
        payment_data: PaymentData,
        mocker: MockerFixture
    ):
        """Test payment creation failure with Telegram Stars API error."""
        # Mock the HTTP request failure
        mock_response = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: invalid chat_id"
        }
        
        mock_post = mocker.patch('aiohttp.ClientSession.post')
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        mock_post.return_value.__aenter__.return_value.status = 400

        # Act
        result = await telegram_stars_gateway.create_payment(payment_data)

        # Assert
        assert result.success is False
        assert "Bad Request: invalid chat_id" in result.error_message

    async def test_telegram_stars_handle_webhook(
        self,
        telegram_stars_gateway: TelegramStarsGateway
    ):
        """Test webhook handling for Telegram Stars."""
        # Arrange
        webhook_data = {
            "pre_checkout_query": {
                "id": "query_123",
                "from": {"id": 123456},
                "currency": "XTR",
                "total_amount": 100,
                "invoice_payload": "order_456"
            }
        }

        # Act
        result = await telegram_stars_gateway.handle_webhook(webhook_data)

        # Assert
        assert result is not None
        assert result.payment_id == "query_123"
        assert result.status == PaymentStatus.PENDING
        assert result.amount == 100.0
        assert result.currency == "XTR"

    async def test_telegram_stars_handle_successful_payment_webhook(
        self,
        telegram_stars_gateway: TelegramStarsGateway
    ):
        """Test webhook handling for successful Telegram Stars payment."""
        # Arrange
        webhook_data = {
            "message": {
                "successful_payment": {
                    "currency": "XTR",
                    "total_amount": 100,
                    "invoice_payload": "order_456",
                    "telegram_payment_charge_id": "charge_123",
                    "provider_payment_charge_id": "provider_123"
                }
            }
        }

        # Act
        result = await telegram_stars_gateway.handle_webhook(webhook_data)

        # Assert
        assert result is not None
        assert result.external_payment_id == "charge_123"
        assert result.status == PaymentStatus.COMPLETED
        assert result.amount == 100.0
        assert result.currency == "XTR"

    async def test_telegram_stars_get_payment_status_not_supported(
        self,
        telegram_stars_gateway: TelegramStarsGateway
    ):
        """Test that payment status checking returns pending for Telegram Stars."""
        # Act
        status = await telegram_stars_gateway.get_payment_status("test_payment_id")

        # Assert
        # Telegram Stars doesn't support direct status checking, so it returns PENDING
        assert status == PaymentStatus.PENDING

    async def test_telegram_stars_currency_validation(
        self,
        telegram_stars_gateway: TelegramStarsGateway
    ):
        """Test currency validation for Telegram Stars."""
        # Act
        currencies = telegram_stars_gateway.get_supported_currencies()

        # Assert
        assert currencies == ["XTR"]

    async def test_telegram_stars_amount_formatting(
        self,
        telegram_stars_gateway: TelegramStarsGateway
    ):
        """Test amount formatting for Telegram Stars."""
        # Act
        formatted = telegram_stars_gateway.format_amount(100.0, "XTR")

        # Assert
        assert formatted == "100 ⭐"


class TestPaymentGatewayFactory:
    """Test cases for PaymentGatewayFactory."""

    @pytest.fixture
    def gateway_configs(self) -> Dict[str, Dict[str, Any]]:
        """Create gateway configurations."""
        return {
            "cryptomus": {
                "enabled": True,
                "api_key": "test_key",
                "merchant_id": "test_merchant"
            },
            "telegram_stars": {
                "enabled": True,
                "bot_token": "test_token"
            }
        }

    @pytest.fixture
    def factory(self, gateway_configs: Dict[str, Dict[str, Any]]) -> PaymentGatewayFactory:
        """Create payment gateway factory."""
        return PaymentGatewayFactory(gateway_configs)

    def test_factory_initialization(self, factory: PaymentGatewayFactory):
        """Test factory initialization."""
        assert factory is not None
        assert len(factory._gateways) >= 2  # Should have registered gateways

    def test_factory_get_gateway_cryptomus(self, factory: PaymentGatewayFactory):
        """Test getting Cryptomus gateway from factory."""
        # Act
        gateway = factory.get_gateway(PaymentMethod.CRYPTOMUS)

        # Assert
        assert gateway is not None
        assert isinstance(gateway, CryptomusGateway)
        assert gateway.payment_method == PaymentMethod.CRYPTOMUS

    def test_factory_get_gateway_telegram_stars(self, factory: PaymentGatewayFactory):
        """Test getting Telegram Stars gateway from factory."""
        # Act
        gateway = factory.get_gateway(PaymentMethod.TELEGRAM_STARS)

        # Assert
        assert gateway is not None
        assert isinstance(gateway, TelegramStarsGateway)
        assert gateway.payment_method == PaymentMethod.TELEGRAM_STARS

    def test_factory_get_gateway_not_found(self, factory: PaymentGatewayFactory):
        """Test getting non-existent gateway from factory."""
        # Act
        gateway = factory.get_gateway(PaymentMethod.MANUAL)

        # Assert
        assert gateway is None

    def test_factory_get_supported_methods(self, factory: PaymentGatewayFactory):
        """Test getting supported payment methods."""
        # Act
        methods = factory.get_supported_methods()

        # Assert
        assert PaymentMethod.CRYPTOMUS in methods
        assert PaymentMethod.TELEGRAM_STARS in methods
        assert len(methods) >= 2

    def test_factory_disabled_gateway(self):
        """Test factory with disabled gateway."""
        # Arrange
        configs = {
            "cryptomus": {
                "enabled": False,  # Disabled
                "api_key": "test_key",
                "merchant_id": "test_merchant"
            }
        }
        factory = PaymentGatewayFactory(configs)

        # Act
        gateway = factory.get_gateway(PaymentMethod.CRYPTOMUS)

        # Assert
        assert gateway is None  # Should not return disabled gateway

    def test_factory_register_custom_gateway(self, gateway_configs: Dict[str, Dict[str, Any]]):
        """Test registering custom gateway with factory."""
        # Arrange
        class CustomGateway(PaymentGateway):
            @property
            def gateway_name(self) -> str:
                return "custom_gateway"
            
            @property
            def payment_method(self) -> PaymentMethod:
                return PaymentMethod.MANUAL
            
            async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
                return PaymentResult(success=True)
            
            async def get_payment_status(self, payment_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, webhook_data: dict) -> WebhookData:
                return None

        factory = PaymentGatewayFactory(gateway_configs)
        
        # Act
        factory.register_gateway(PaymentMethod.MANUAL, CustomGateway)
        gateway = factory.get_gateway(PaymentMethod.MANUAL)

        # Assert
        assert gateway is not None
        assert isinstance(gateway, CustomGateway)

    def test_factory_with_empty_config(self):
        """Test factory with empty configuration."""
        # Arrange
        factory = PaymentGatewayFactory({})

        # Act
        methods = factory.get_supported_methods()
        gateway = factory.get_gateway(PaymentMethod.CRYPTOMUS)

        # Assert
        assert len(methods) == 0
        assert gateway is None

    def test_factory_gateway_availability(self, factory: PaymentGatewayFactory):
        """Test gateway availability checking."""
        # Act
        cryptomus_gateway = factory.get_gateway(PaymentMethod.CRYPTOMUS)
        telegram_gateway = factory.get_gateway(PaymentMethod.TELEGRAM_STARS)

        # Assert
        assert cryptomus_gateway.is_available() is True
        assert telegram_gateway.is_available() is True