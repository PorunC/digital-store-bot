"""Payment gateway factory with proper dependency injection."""

import logging
from typing import Dict, List, Optional

from aiogram import Bot

from src.infrastructure.configuration.settings import Settings
from .base import PaymentGateway, PaymentMethod
from .telegram_stars import TelegramStarsGateway
from .cryptomus import CryptomusGateway

logger = logging.getLogger(__name__)


class PaymentGatewayFactory:
    """Factory for creating payment gateways."""

    def __init__(self, settings: Settings, bot: Optional[Bot] = None):
        self.settings = settings
        self.bot = bot
        self._gateways: Dict[PaymentMethod, PaymentGateway] = {}
        self._initialize_gateways()

    def _initialize_gateways(self) -> None:
        """Initialize available payment gateways."""
        try:
            # Initialize Telegram Stars gateway
            if self.settings.payments.telegram_stars.enabled and self.bot:
                telegram_config = {
                    "enabled": self.settings.payments.telegram_stars.enabled
                }
                self._gateways[PaymentMethod.TELEGRAM_STARS] = TelegramStarsGateway(
                    config=telegram_config,
                    bot=self.bot
                )
                logger.info("Telegram Stars gateway initialized")

            # Initialize Cryptomus gateway
            if self.settings.payments.cryptomus.enabled:
                cryptomus_config = {
                    "enabled": self.settings.payments.cryptomus.enabled,
                    "api_key": self.settings.payments.cryptomus.api_key,
                    "merchant_id": self.settings.payments.cryptomus.merchant_id
                }
                
                # Validate Cryptomus configuration
                if cryptomus_config["api_key"] and cryptomus_config["merchant_id"]:
                    self._gateways[PaymentMethod.CRYPTOMUS] = CryptomusGateway(cryptomus_config)
                    logger.info("Cryptomus gateway initialized")
                else:
                    logger.warning("Cryptomus gateway disabled: missing configuration")

        except Exception as e:
            logger.error(f"Error initializing payment gateways: {e}")

    def get_gateway(self, payment_method: PaymentMethod) -> Optional[PaymentGateway]:
        """Get payment gateway by method."""
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

    def reload_configuration(self, settings: Settings) -> None:
        """Reload gateway configuration."""
        self.settings = settings
        self._gateways.clear()
        self._initialize_gateways()
        logger.info("Payment gateways reloaded")

    def get_gateway_status(self) -> Dict[str, dict]:
        """Get status of all gateways."""
        status = {}
        
        for method, gateway in self._gateways.items():
            status[method.value] = {
                "name": gateway.gateway_name,
                "available": gateway.is_available(),
                "enabled": gateway.is_enabled,
                "supported_currencies": gateway.get_supported_currencies()
            }
        
        return status