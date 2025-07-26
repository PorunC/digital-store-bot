"""Payment gateway factory with proper dependency injection."""

import logging
from typing import Dict, List, Optional, Union, Any

from aiogram import Bot

from src.domain.entities.order import PaymentMethod
from .base import PaymentGateway
from .telegram_stars import TelegramStarsGateway
from .cryptomus import CryptomusGateway

logger = logging.getLogger(__name__)


class PaymentGatewayFactory:
    """Factory for creating payment gateways."""

    def __init__(self, config: Union[Dict[str, Dict[str, Any]], Any], bot: Optional[Bot] = None):
        """
        Initialize factory with configuration.
        
        Args:
            config: Either a dictionary with gateway configs or Settings object
            bot: Optional Telegram bot instance
        """
        self.config = config
        self.bot = bot
        self._gateways: Dict[PaymentMethod, PaymentGateway] = {}
        self._registry: Dict[PaymentMethod, type] = {}
        
        # Register default gateways
        self.register_gateway(PaymentMethod.TELEGRAM_STARS, TelegramStarsGateway)
        self.register_gateway(PaymentMethod.CRYPTOMUS, CryptomusGateway)
        
        self._initialize_gateways()

    def register_gateway(self, payment_method: PaymentMethod, gateway_class: type) -> None:
        """Register a gateway class for a payment method."""
        self._registry[payment_method] = gateway_class
        logger.debug(f"Registered gateway {gateway_class.__name__} for {payment_method}")

    def _get_gateway_config(self, gateway_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a gateway."""
        if isinstance(self.config, dict):
            # Direct dictionary configuration (for testing)
            return self.config.get(gateway_name)
        else:
            # Settings object configuration (for production)
            try:
                if hasattr(self.config, 'payments'):
                    payments = self.config.payments
                    if gateway_name == 'telegram_stars' and hasattr(payments, 'telegram_stars'):
                        return {
                            "enabled": payments.telegram_stars.enabled,
                            "bot_token": getattr(payments.telegram_stars, 'bot_token', None)
                        }
                    elif gateway_name == 'cryptomus' and hasattr(payments, 'cryptomus'):
                        return {
                            "enabled": payments.cryptomus.enabled,
                            "api_key": payments.cryptomus.api_key,
                            "merchant_id": payments.cryptomus.merchant_id
                        }
            except AttributeError:
                logger.warning(f"Could not access configuration for {gateway_name}")
        return None

    def _initialize_gateways(self) -> None:
        """Initialize available payment gateways."""
        try:
            # Initialize Telegram Stars gateway
            telegram_config = self._get_gateway_config('telegram_stars')
            if telegram_config and telegram_config.get('enabled', False):
                gateway_class = self._registry.get(PaymentMethod.TELEGRAM_STARS)
                if gateway_class:
                    self._gateways[PaymentMethod.TELEGRAM_STARS] = gateway_class(
                        config=telegram_config,
                        bot=self.bot
                    )
                    logger.info("Telegram Stars gateway initialized")

            # Initialize Cryptomus gateway
            cryptomus_config = self._get_gateway_config('cryptomus')
            if cryptomus_config and cryptomus_config.get('enabled', False):
                # Validate Cryptomus configuration
                if cryptomus_config.get("api_key") and cryptomus_config.get("merchant_id"):
                    gateway_class = self._registry.get(PaymentMethod.CRYPTOMUS)
                    if gateway_class:
                        self._gateways[PaymentMethod.CRYPTOMUS] = gateway_class(cryptomus_config)
                        logger.info("Cryptomus gateway initialized")
                else:
                    logger.warning("Cryptomus gateway disabled: missing configuration")

        except Exception as e:
            logger.error(f"Error initializing payment gateways: {e}")

    def set_bot_instance(self, bot) -> None:
        """Set bot instance for Telegram Stars gateway."""
        self.bot = bot
        # Re-initialize Telegram Stars gateway with bot
        telegram_config = self._get_gateway_config('telegram_stars')
        if (telegram_config and telegram_config.get('enabled', False) and 
            PaymentMethod.TELEGRAM_STARS in self._registry):
            gateway_class = self._registry[PaymentMethod.TELEGRAM_STARS]
            self._gateways[PaymentMethod.TELEGRAM_STARS] = gateway_class(
                config=telegram_config,
                bot=self.bot
            )
            logger.info("Telegram Stars gateway updated with bot instance")

    def get_gateway(self, payment_method: PaymentMethod) -> Optional[PaymentGateway]:
        """Get payment gateway by method."""
        # Ensure payment_method is PaymentMethod enum
        if isinstance(payment_method, str):
            try:
                payment_method = PaymentMethod(payment_method)
            except ValueError:
                logger.warning(f"Invalid payment method string: {payment_method}")
                return None
        
        gateway = self._gateways.get(payment_method)
        
        if gateway and gateway.is_available():
            return gateway
        
        logger.warning(f"Payment gateway {payment_method} not available")
        return None

    def get_available_gateways(self) -> List[PaymentGateway]:
        """Get all available payment gateways."""
        return [
            gateway for gateway in self._gateways.values()
            if gateway.is_available()
        ]

    def get_gateway_by_name(self, gateway_name: str) -> Optional[PaymentGateway]:
        """Get payment gateway by name."""
        for gateway in self._gateways.values():
            if gateway.gateway_name.lower() == gateway_name.lower():
                return gateway if gateway.is_available() else None
        return None

    def is_gateway_available(self, payment_method: PaymentMethod) -> bool:
        """Check if payment gateway is available."""
        gateway = self._gateways.get(payment_method)
        return gateway is not None and gateway.is_available()

    def get_supported_currencies(self) -> List[str]:
        """Get all supported currencies across gateways."""
        currencies = set()
        for gateway in self.get_available_gateways():
            currencies.update(gateway.get_supported_currencies())
        return list(currencies)

    def get_gateway_for_currency(self, currency: str) -> Optional[PaymentGateway]:
        """Get best gateway for a specific currency."""
        # Priority order for currency support
        priority_methods = [
            PaymentMethod.TELEGRAM_STARS,  # Prefer Telegram Stars for XTR
            PaymentMethod.CRYPTOMUS        # Fallback to crypto
        ]
        
        for method in priority_methods:
            gateway = self.get_gateway(method)
            if gateway and currency in gateway.get_supported_currencies():
                return gateway
        
        # Return any available gateway as last resort
        available_gateways = self.get_available_gateways()
        return available_gateways[0] if available_gateways else None

    def reload_configuration(self, config: Union[Dict[str, Dict[str, Any]], Any]) -> None:
        """Reload gateway configuration."""
        self.config = config
        self._gateways.clear()
        self._initialize_gateways()
        logger.info("Payment gateways reloaded")

    def get_supported_methods(self) -> List[PaymentMethod]:
        """Get list of supported payment methods."""
        return [
            method for method, gateway in self._gateways.items()
            if gateway.is_available()
        ]

    def get_gateway_status(self) -> Dict[str, dict]:
        """Get status of all gateways."""
        status = {}
        
        for method, gateway in self._gateways.items():
            status[method.value] = {
                "name": gateway.gateway_name,
                "available": gateway.is_available(),
                "enabled": gateway.is_available(),
                "supported_currencies": gateway.get_supported_currencies()
            }
        
        return status