"""Payment webhook handlers for external payment gateways."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.application.services import (
    PaymentApplicationService,
    OrderApplicationService,
    UserApplicationService
)
from src.domain.entities.order import PaymentMethod
from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
from src.core.containers import container
from src.shared.events import event_bus

logger = logging.getLogger(__name__)

payment_webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    status: str
    message: str
    timestamp: datetime
    order_id: Optional[str] = None


@payment_webhook_router.post("/cryptomus")
async def handle_cryptomus_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Handle Cryptomus payment webhook."""
    try:
        # Get raw body for signature validation
        raw_body = await request.body()
        
        # Parse JSON data
        try:
            webhook_data = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Cryptomus webhook")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Get signature from headers or data
        signature = webhook_data.get('sign') or request.headers.get('signature')
        
        # Log webhook for debugging
        logger.info(f"Received Cryptomus webhook: {webhook_data}")
        
        # Process webhook in background
        background_tasks.add_task(
            process_payment_webhook,
            PaymentMethod.CRYPTOMUS,
            webhook_data,
            signature
        )
        
        # Return immediate response
        return JSONResponse(
            status_code=200,
            content=WebhookResponse(
                status="success",
                message="Webhook received and queued for processing",
                timestamp=datetime.utcnow()
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Error handling Cryptomus webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@payment_webhook_router.post("/telegram-stars")
async def handle_telegram_stars_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Handle Telegram Stars payment webhook (if needed)."""
    try:
        webhook_data = await request.json()
        
        logger.info(f"Received Telegram Stars webhook: {webhook_data}")
        
        # Process webhook in background
        background_tasks.add_task(
            process_payment_webhook,
            PaymentMethod.TELEGRAM_STARS,
            webhook_data,
            None  # Stars webhooks might not need signature validation
        )
        
        return JSONResponse(
            status_code=200,
            content=WebhookResponse(
                status="success",
                message="Webhook received and queued for processing",
                timestamp=datetime.utcnow()
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Error handling Telegram Stars webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_payment_webhook(
    payment_method: PaymentMethod,
    webhook_data: Dict[str, Any],
    signature: Optional[str] = None
) -> Optional[str]:
    """Process payment webhook data."""
    try:
        # Get services
        payment_service: PaymentApplicationService = container.payment_service()
        order_service: OrderApplicationService = container.order_service()
        user_service: UserApplicationService = container.user_service()
        
        # Get payment gateway
        gateway_factory: PaymentGatewayFactory = container.payment_gateway_factory()
        gateway = gateway_factory.get_gateway(payment_method)
        
        # Validate webhook signature
        if not gateway.validate_webhook_signature(webhook_data, signature):
            logger.warning(f"Invalid webhook signature for {payment_method.value}")
            return None
        
        # Process webhook through gateway
        webhook_result = await gateway.handle_webhook(webhook_data)
        
        if not webhook_result:
            logger.warning(f"Gateway returned no result for webhook: {payment_method.value}")
            return None
        
        # Get order
        order = await order_service.get_order_by_id(webhook_result.payment_id)
        if not order:
            logger.error(f"Order not found for webhook: {webhook_result.payment_id}")
            return None
        
        # Update order based on webhook status
        if webhook_result.status.value in ["completed", "paid"]:
            # Mark as paid first
            paid_order = await order_service.mark_as_paid(
                order_id=str(order.id),
                external_payment_id=webhook_result.external_payment_id
            )
            
            # Then mark as completed
            completed_order = await order_service.mark_as_completed(
                order_id=str(order.id),
                notes=f"Payment confirmed via {payment_method.value} webhook"
            )
            
            # Send success notification
            await send_payment_success_notification(completed_order, webhook_result)
            
            logger.info(f"Order {order.id} completed via webhook")
            return str(completed_order.id)
            
        elif webhook_result.status.value in ["failed", "cancelled"]:
            # Cancel the order
            cancelled_order = await order_service.cancel_order(
                order_id=str(order.id),
                reason=f"Payment {webhook_result.status.value} via {payment_method.value}"
            )
            
            # Send failure notification
            await send_payment_failure_notification(cancelled_order, webhook_result)
            
            logger.info(f"Order {order.id} cancelled due to payment failure")
            return str(cancelled_order.id)
        
        else:
            logger.info(f"Webhook received for order {order.id} with status {webhook_result.status.value}")
            return str(order.id)
            
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}")
        return None


async def send_payment_success_notification(order, webhook_result):
    """Send payment success notification to user."""
    try:
        from aiogram import Bot
        from src.core.containers import container
        
        # Get bot instance (would need to be properly configured)
        # bot: Bot = container.Bot()
        
        user_service: UserApplicationService = container.user_service()
        user = await user_service.get_user_by_id(str(order.user_id))
        
        if not user:
            logger.error(f"User not found for order {order.id}")
            return
        
        success_message = (
            f"🎉 **Payment Successful!**\n\n"
            f"✅ Your order has been completed\n"
            f"📦 Product: {order.product_name}\n"
            f"💰 Amount: ${order.amount.amount:.2f} {order.amount.currency.upper()}\n"
            f"🆔 Order ID: `{str(order.id)[:8]}...`\n"
            f"📅 Completed: {order.completed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🎁 Your subscription has been activated!\n"
            f"Use /profile to check your new status."
        )
        
        # In a real implementation, you would send this via the bot
        # await bot.send_message(
        #     chat_id=user.telegram_id,
        #     text=success_message,
        #     parse_mode="Markdown"
        # )
        
        logger.info(f"Payment success notification prepared for user {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error sending payment success notification: {e}")


async def send_payment_failure_notification(order, webhook_result):
    """Send payment failure notification to user."""
    try:
        user_service: UserApplicationService = container.user_service()
        user = await user_service.get_user_by_id(str(order.user_id))
        
        if not user:
            logger.error(f"User not found for order {order.id}")
            return
        
        failure_message = (
            f"❌ **Payment Failed**\n\n"
            f"Your payment could not be processed:\n\n"
            f"📦 Product: {order.product_name}\n"
            f"💰 Amount: ${order.amount.amount:.2f} {order.amount.currency.upper()}\n"
            f"🆔 Order ID: `{str(order.id)[:8]}...`\n"
            f"📅 Failed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📞 Need help? Contact /support\n"
            f"🔄 You can try ordering again with /catalog"
        )
        
        # In a real implementation, you would send this via the bot
        logger.info(f"Payment failure notification prepared for user {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error sending payment failure notification: {e}")


@payment_webhook_router.get("/health")
async def webhook_health_check():
    """Health check endpoint for webhook service."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "payment-webhooks",
            "timestamp": datetime.utcnow().isoformat(),
            "supported_gateways": ["cryptomus", "telegram-stars"]
        }
    )


@payment_webhook_router.post("/test")
async def test_webhook_processing():
    """Test endpoint for webhook processing (development only)."""
    test_webhook_data = {
        "order_id": "test-order-123",
        "uuid": "test-payment-456",
        "status": "paid",
        "amount": "10.00",
        "currency": "USD",
        "sign": "test-signature"
    }
    
    # Process test webhook
    result = await process_payment_webhook(
        PaymentMethod.CRYPTOMUS,
        test_webhook_data,
        "test-signature"
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "test_completed",
            "processed_order_id": result,
            "test_data": test_webhook_data
        }
    )