"""Telegram Stars payment gateway implementation with bug fixes."""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import LabeledPrice

from src.domain.entities.order import PaymentMethod
from .base import PaymentGateway, PaymentData, PaymentResult, PaymentStatus, WebhookData

logger = logging.getLogger(__name__)


class TelegramStarsGateway(PaymentGateway):
    """Telegram Stars payment gateway."""

    def __init__(self, config: dict, bot: Optional[Bot] = None):
        super().__init__(config)
        self.bot = bot

    @property
    def gateway_name(self) -> str:
        """Get gateway name."""
        return "Telegram Stars"

    @property
    def payment_method(self) -> PaymentMethod:
        """Get payment method."""
        return PaymentMethod.TELEGRAM_STARS

    async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
        """Create a Telegram Stars payment."""
        if not self.bot:
            return PaymentResult(
                success=False,
                error_message="Telegram bot instance not available"
            )
            
        try:
            # Convert amount to Telegram Stars (1 Star = 1 cent USD approximately)
            # For different currencies, we need conversion logic
            stars_amount = self._convert_to_stars(payment_data.amount, payment_data.currency)
            
            if stars_amount <= 0:
                return PaymentResult(
                    success=False,
                    error_message=f"Invalid amount: {payment_data.amount} {payment_data.currency}"
                )

            # Create labeled price for Telegram
            prices = [LabeledPrice(label=payment_data.description, amount=stars_amount)]

            # Send invoice to user
            invoice_message = await self.bot.send_invoice(
                chat_id=payment_data.user_telegram_id,
                title=payment_data.description,
                description=f"Order #{payment_data.order_id}",
                payload=payment_data.order_id,  # Use order_id as payload
                provider_token="",  # Empty for Telegram Stars
                currency="XTR",  # Telegram Stars currency
                prices=prices,
                start_parameter=f"order_{payment_data.order_id}",
                photo_url=None,  # Optional product photo
                photo_size=None,
                photo_width=None,
                photo_height=None,
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                send_phone_number_to_provider=False,
                send_email_to_provider=False,
                is_flexible=False
            )

            return PaymentResult(
                success=True,
                payment_id=payment_data.order_id,  # Use order_id as payment_id
                metadata={
                    "message_id": invoice_message.message_id,
                    "stars_amount": stars_amount,
                    "original_amount": payment_data.amount,
                    "original_currency": payment_data.currency
                }
            )

        except Exception as e:
            logger.error(f"Failed to create Telegram Stars payment: {e}")
            return PaymentResult(
                success=False,
                error_message=f"Failed to create payment: {str(e)}"
            )

    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status (Telegram doesn't provide status API)."""
        # Telegram Stars doesn't have a status API
        # Status is determined through webhooks only
        return PaymentStatus.PENDING

    async def handle_webhook(self, webhook_data: dict) -> Optional[WebhookData]:
        """Handle Telegram Stars webhook (successful payment)."""
        try:
            # Telegram Stars webhook comes as successful_payment update
            if "successful_payment" in webhook_data:
                payment_info = webhook_data["successful_payment"]
                
                # Extract payment details
                payload = payment_info.get("invoice_payload")  # This is our order_id
                currency = payment_info.get("currency", "XTR")
                total_amount = payment_info.get("total_amount", 0)
                telegram_payment_charge_id = payment_info.get("telegram_payment_charge_id")
                
                if not payload:
                    logger.warning("No payload in Telegram Stars payment")
                    return None

                return WebhookData(
                    payment_id=payload,  # Our order_id
                    external_payment_id=telegram_payment_charge_id,
                    status=PaymentStatus.COMPLETED,
                    amount=total_amount / 100,  # Convert back from cents
                    currency=currency,
                    metadata={
                        "provider_payment_charge_id": payment_info.get("provider_payment_charge_id"),
                        "telegram_payment_charge_id": telegram_payment_charge_id
                    }
                )

            logger.warning(f"Unhandled Telegram webhook data: {webhook_data}")
            return None

        except Exception as e:
            logger.error(f"Error handling Telegram Stars webhook: {e}")
            return None

    def _convert_to_stars(self, amount: float, currency: str) -> int:
        """Convert amount to Telegram Stars (in kopecks/cents)."""
        # Simple conversion logic - in production, use real exchange rates
        conversion_rates = {
            "XTR": 1,  # Already in stars
            "USD": 100,  # 1 USD = 100 cents = 100 stars (approximately)
            "EUR": 110,  # 1 EUR = 110 stars (approximately)
            "RUB": 1,    # 1 RUB = 1 star (approximately)
        }
        
        if currency not in conversion_rates:
            logger.warning(f"Unsupported currency for Telegram Stars: {currency}")
            return 0
            
        # Convert to smallest unit (kopecks/cents) for Telegram
        stars = int(amount * conversion_rates[currency])
        
        # Minimum 1 star
        return max(1, stars)

    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ["XTR", "USD", "EUR", "RUB"]

    def format_amount(self, amount: float, currency: str) -> str:
        """Format amount for display."""
        if currency == "XTR":
            return f"⭐ {int(amount)}"
        return f"{amount:.2f} {currency}"