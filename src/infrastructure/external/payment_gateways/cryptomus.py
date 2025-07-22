"""Cryptomus payment gateway implementation with security fixes."""

import hashlib
import hmac
import json
import logging
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from .base import PaymentGateway, PaymentData, PaymentResult, PaymentStatus, PaymentMethod, WebhookData

logger = logging.getLogger(__name__)


class CryptomusGateway(PaymentGateway):
    """Cryptomus cryptocurrency payment gateway."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.merchant_id = config.get("merchant_id")
        self.base_url = "https://api.cryptomus.com/v1"
        
        # Validate configuration
        if self.is_enabled and (not self.api_key or not self.merchant_id):
            logger.error("Cryptomus API key or merchant ID not configured")
            self.is_enabled = False

    @property
    def gateway_name(self) -> str:
        """Get gateway name."""
        return "Cryptomus"

    @property
    def payment_method(self) -> PaymentMethod:
        """Get payment method."""
        return PaymentMethod.CRYPTOMUS

    async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
        """Create a Cryptomus payment."""
        try:
            if not self.is_available():
                return PaymentResult(
                    success=False,
                    error_message="Cryptomus gateway is not available"
                )

            # Prepare payment request
            payment_request = {
                "amount": str(payment_data.amount),
                "currency": payment_data.currency,
                "order_id": payment_data.order_id,
                "url_return": payment_data.return_url,
                "url_callback": payment_data.webhook_url,
                "is_payment_multiple": False,
                "lifetime": 3600,  # 1 hour
                "to_currency": "USDT",  # Default crypto currency
                "additional_data": json.dumps({
                    "user_id": payment_data.user_id,
                    "product_id": payment_data.product_id,
                    "user_telegram_id": payment_data.user_telegram_id
                })
            }

            # Make API request
            response = await self._make_request("POST", "/payment", payment_request)
            
            if response and response.get("state") == 0:
                result_data = response.get("result", {})
                
                return PaymentResult(
                    success=True,
                    payment_id=result_data.get("uuid"),
                    payment_url=result_data.get("url"),
                    metadata={
                        "order_id": result_data.get("order_id"),
                        "amount": result_data.get("amount"),
                        "currency": result_data.get("currency"),
                        "to_currency": result_data.get("to_currency"),
                        "expires_at": result_data.get("expired_at")
                    }
                )
            else:
                error_msg = response.get("message", "Unknown error") if response else "API request failed"
                return PaymentResult(
                    success=False,
                    error_message=f"Cryptomus error: {error_msg}"
                )

        except Exception as e:
            logger.error(f"Failed to create Cryptomus payment: {e}")
            return PaymentResult(
                success=False,
                error_message=f"Failed to create payment: {str(e)}"
            )

    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status from Cryptomus."""
        try:
            response = await self._make_request("POST", "/payment/info", {
                "uuid": payment_id
            })
            
            if response and response.get("state") == 0:
                result = response.get("result", {})
                status = result.get("payment_status")
                
                # Map Cryptomus statuses to our enum
                status_mapping = {
                    "paid": PaymentStatus.COMPLETED,
                    "paid_over": PaymentStatus.COMPLETED,
                    "fail": PaymentStatus.FAILED,
                    "cancel": PaymentStatus.CANCELLED,
                    "process": PaymentStatus.PENDING,
                    "check": PaymentStatus.PENDING,
                    "refund": PaymentStatus.REFUNDED,
                    "refund_process": PaymentStatus.REFUNDED
                }
                
                return status_mapping.get(status, PaymentStatus.PENDING)
            
            return PaymentStatus.FAILED

        except Exception as e:
            logger.error(f"Failed to get Cryptomus payment status: {e}")
            return PaymentStatus.FAILED

    async def handle_webhook(self, webhook_data: dict) -> Optional[WebhookData]:
        """Handle Cryptomus webhook with proper signature validation."""
        try:
            # Validate webhook signature for security
            if not self._validate_webhook_signature(webhook_data):
                logger.warning("Invalid Cryptomus webhook signature")
                return None

            # Extract payment information
            order_id = webhook_data.get("order_id")
            uuid = webhook_data.get("uuid")
            status = webhook_data.get("status")
            amount = webhook_data.get("amount")
            currency = webhook_data.get("currency")
            
            if not order_id or not uuid:
                logger.warning("Missing required fields in Cryptomus webhook")
                return None

            # Map status
            status_mapping = {
                "paid": PaymentStatus.COMPLETED,
                "paid_over": PaymentStatus.COMPLETED,
                "fail": PaymentStatus.FAILED,
                "cancel": PaymentStatus.CANCELLED,
                "refund": PaymentStatus.REFUNDED
            }
            
            mapped_status = status_mapping.get(status, PaymentStatus.PENDING)
            
            return WebhookData(
                payment_id=order_id,  # Our order_id
                external_payment_id=uuid,
                status=mapped_status,
                amount=float(amount) if amount else None,
                currency=currency,
                metadata={
                    "cryptomus_uuid": uuid,
                    "cryptomus_status": status,
                    "payer_currency": webhook_data.get("payer_currency"),
                    "payer_amount": webhook_data.get("payer_amount"),
                    "txid": webhook_data.get("txid"),
                    "block_id": webhook_data.get("block_id")
                }
            )

        except Exception as e:
            logger.error(f"Error handling Cryptomus webhook: {e}")
            return None

    def _validate_webhook_signature(self, webhook_data: dict) -> bool:
        """Validate Cryptomus webhook signature."""
        try:
            # Extract signature from headers or data
            received_signature = webhook_data.get("sign")
            if not received_signature:
                return False

            # Create expected signature
            # Sort data for consistent hashing
            sorted_data = dict(sorted(webhook_data.items()))
            
            # Remove signature from data
            if "sign" in sorted_data:
                del sorted_data["sign"]
            
            # Create query string
            query_string = urlencode(sorted_data)
            
            # Create signature
            expected_signature = hashlib.md5(
                f"{query_string}{self.api_key}".encode()
            ).hexdigest()
            
            return hmac.compare_digest(received_signature, expected_signature)

        except Exception as e:
            logger.error(f"Error validating Cryptomus webhook signature: {e}")
            return False

    async def _make_request(self, method: str, endpoint: str, data: dict) -> Optional[dict]:
        """Make authenticated request to Cryptomus API."""
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Create signature
            data_json = json.dumps(data, sort_keys=True)
            sign = hashlib.md5(f"{data_json}{self.api_key}".encode()).hexdigest()
            
            headers = {
                "merchant": self.merchant_id,
                "sign": sign,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data_json,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Cryptomus API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Cryptomus API request failed: {e}")
            return None

    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ["USD", "EUR", "RUB", "BTC", "ETH", "USDT", "BNB"]

    def validate_webhook_signature(self, data: dict, signature: str) -> bool:
        """Public method to validate webhook signature."""
        return self._validate_webhook_signature(data)