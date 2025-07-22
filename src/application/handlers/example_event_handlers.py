"""Example event handlers for domain events.

This module demonstrates how to handle domain events that are published when
business operations occur. Event handlers implement side effects and cross-cutting concerns.
"""

import logging
from typing import Dict, Any

from src.domain.events.user_events import (
    UserRegisteredEvent,
    UserSubscriptionExtendedEvent,
    UserBlockedEvent,
    UserUnblockedEvent
)
from src.domain.events.order_events import (
    OrderCreatedEvent,
    OrderCompletedEvent,
    OrderCancelledEvent
)
from src.domain.events.payment_events import (
    PaymentProcessedEvent,
    PaymentFailedEvent
)
from src.infrastructure.notifications.notification_service import NotificationService
from src.infrastructure.external.analytics.analytics_service import AnalyticsService
from src.shared.events.decorators import event_handler

logger = logging.getLogger(__name__)


class UserEventHandler:
    """Handler for user-related domain events."""
    
    def __init__(
        self,
        notification_service: NotificationService,
        analytics_service: AnalyticsService
    ):
        self.notification_service = notification_service
        self.analytics_service = analytics_service
    
    @event_handler(UserRegisteredEvent)
    async def handle_user_registered(self, event: UserRegisteredEvent) -> None:
        """Handle user registration event."""
        try:
            logger.info(f"New user registered: {event.user_id}")
            
            # Send welcome notification
            await self.notification_service.send_welcome_message(
                user_id=event.user_id,
                telegram_id=event.telegram_id,
                username=event.username,
                language_code=event.language_code
            )
            
            # Track analytics
            await self.analytics_service.track_user_registration(
                user_id=event.user_id,
                telegram_id=event.telegram_id,
                metadata={
                    "username": event.username,
                    "language_code": event.language_code,
                    "registration_date": event.timestamp.isoformat()
                }
            )
            
            # Start trial if enabled
            if event.trial_enabled:
                await self.notification_service.send_trial_started_notification(
                    user_id=event.user_id,
                    trial_duration_days=event.trial_duration_days
                )
            
            logger.info(f"User registration event handled successfully: {event.user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user registration event: {e}", exc_info=True)
    
    @event_handler(UserSubscriptionExtendedEvent)
    async def handle_subscription_extended(self, event: UserSubscriptionExtendedEvent) -> None:
        """Handle subscription extension event."""
        try:
            logger.info(f"Subscription extended for user: {event.user_id}")
            
            # Send confirmation notification
            await self.notification_service.send_subscription_extended_notification(
                user_id=event.user_id,
                subscription_type=event.subscription_type,
                duration_days=event.duration_days,
                expires_at=event.expires_at
            )
            
            # Track analytics
            await self.analytics_service.track_subscription_extension(
                user_id=event.user_id,
                subscription_type=event.subscription_type,
                duration_days=event.duration_days,
                metadata={
                    "expires_at": event.expires_at.isoformat(),
                    "extended_at": event.timestamp.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling subscription extension event: {e}", exc_info=True)
    
    @event_handler(UserBlockedEvent)
    async def handle_user_blocked(self, event: UserBlockedEvent) -> None:
        """Handle user blocked event."""
        try:
            logger.warning(f"User blocked: {event.user_id}, reason: {event.reason}")
            
            # Send notification to user
            await self.notification_service.send_account_blocked_notification(
                user_id=event.user_id,
                reason=event.reason,
                blocked_until=event.blocked_until
            )
            
            # Notify administrators
            await self.notification_service.send_admin_notification(
                message=f"User {event.user_id} has been blocked. Reason: {event.reason}",
                level="warning"
            )
            
            # Track analytics
            await self.analytics_service.track_user_blocked(
                user_id=event.user_id,
                reason=event.reason,
                metadata={
                    "blocked_until": event.blocked_until.isoformat() if event.blocked_until else None,
                    "blocked_at": event.timestamp.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling user blocked event: {e}", exc_info=True)


class OrderEventHandler:
    """Handler for order-related domain events."""
    
    def __init__(
        self,
        notification_service: NotificationService,
        analytics_service: AnalyticsService
    ):
        self.notification_service = notification_service
        self.analytics_service = analytics_service
    
    @event_handler(OrderCreatedEvent)
    async def handle_order_created(self, event: OrderCreatedEvent) -> None:
        """Handle order creation event."""
        try:
            logger.info(f"Order created: {event.order_id} for user: {event.user_id}")
            
            # Send order confirmation
            await self.notification_service.send_order_created_notification(
                user_id=event.user_id,
                order_id=event.order_id,
                product_name=event.product_name,
                amount=event.amount,
                currency=event.currency
            )
            
            # Track analytics
            await self.analytics_service.track_order_created(
                order_id=event.order_id,
                user_id=event.user_id,
                product_id=event.product_id,
                amount=event.amount,
                currency=event.currency,
                metadata={
                    "product_name": event.product_name,
                    "created_at": event.timestamp.isoformat()
                }
            )
            
            # Notify administrators for high-value orders
            if event.amount >= 100.0:  # High-value threshold
                await self.notification_service.send_admin_notification(
                    message=f"High-value order created: {event.order_id} - ${event.amount}",
                    level="info"
                )
            
        except Exception as e:
            logger.error(f"Error handling order creation event: {e}", exc_info=True)
    
    @event_handler(OrderCompletedEvent)
    async def handle_order_completed(self, event: OrderCompletedEvent) -> None:
        """Handle order completion event."""
        try:
            logger.info(f"Order completed: {event.order_id}")
            
            # Send completion notification with delivery
            await self.notification_service.send_order_completed_notification(
                user_id=event.user_id,
                order_id=event.order_id,
                product_name=event.product_name,
                delivery_content=event.delivery_content
            )
            
            # Track analytics
            await self.analytics_service.track_order_completed(
                order_id=event.order_id,
                user_id=event.user_id,
                revenue=event.amount,
                currency=event.currency,
                metadata={
                    "completion_time": event.timestamp.isoformat(),
                    "delivery_type": event.delivery_type
                }
            )
            
            # Update user loyalty points or rewards
            await self._award_loyalty_points(event.user_id, event.amount)
            
        except Exception as e:
            logger.error(f"Error handling order completion event: {e}", exc_info=True)
    
    async def _award_loyalty_points(self, user_id: str, order_amount: float) -> None:
        """Award loyalty points based on order amount."""
        points = int(order_amount)  # 1 point per dollar
        
        await self.notification_service.send_loyalty_points_notification(
            user_id=user_id,
            points_earned=points,
            total_points=points  # This would come from user service
        )


class PaymentEventHandler:
    """Handler for payment-related domain events."""
    
    def __init__(
        self,
        notification_service: NotificationService,
        analytics_service: AnalyticsService
    ):
        self.notification_service = notification_service
        self.analytics_service = analytics_service
    
    @event_handler(PaymentProcessedEvent)
    async def handle_payment_processed(self, event: PaymentProcessedEvent) -> None:
        """Handle successful payment processing."""
        try:
            logger.info(f"Payment processed: {event.payment_id}")
            
            # Send payment confirmation
            await self.notification_service.send_payment_success_notification(
                user_id=event.user_id,
                payment_id=event.payment_id,
                amount=event.amount,
                currency=event.currency,
                gateway=event.gateway
            )
            
            # Track analytics
            await self.analytics_service.track_payment_success(
                payment_id=event.payment_id,
                user_id=event.user_id,
                amount=event.amount,
                currency=event.currency,
                gateway=event.gateway,
                metadata={
                    "processed_at": event.timestamp.isoformat(),
                    "transaction_id": event.transaction_id
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling payment processed event: {e}", exc_info=True)
    
    @event_handler(PaymentFailedEvent)
    async def handle_payment_failed(self, event: PaymentFailedEvent) -> None:
        """Handle failed payment processing."""
        try:
            logger.warning(f"Payment failed: {event.payment_id}, reason: {event.failure_reason}")
            
            # Send failure notification
            await self.notification_service.send_payment_failed_notification(
                user_id=event.user_id,
                payment_id=event.payment_id,
                reason=event.failure_reason,
                amount=event.amount,
                currency=event.currency
            )
            
            # Track analytics
            await self.analytics_service.track_payment_failure(
                payment_id=event.payment_id,
                user_id=event.user_id,
                amount=event.amount,
                currency=event.currency,
                gateway=event.gateway,
                failure_reason=event.failure_reason,
                metadata={
                    "failed_at": event.timestamp.isoformat(),
                    "error_code": event.error_code
                }
            )
            
            # Notify administrators for investigation
            if event.amount >= 50.0:  # Significant failed payment
                await self.notification_service.send_admin_notification(
                    message=f"High-value payment failed: {event.payment_id} - ${event.amount} - {event.failure_reason}",
                    level="warning"
                )
            
        except Exception as e:
            logger.error(f"Error handling payment failed event: {e}", exc_info=True)


# Example event handler registry setup:
"""
# In your dependency injection container or main application setup:

def setup_event_handlers(container):
    notification_service = container.get(NotificationService)
    analytics_service = container.get(AnalyticsService)
    event_bus = container.get(EventBus)
    
    # Register user event handlers
    user_handler = UserEventHandler(notification_service, analytics_service)
    event_bus.register_handler(UserRegisteredEvent, user_handler.handle_user_registered)
    event_bus.register_handler(UserSubscriptionExtendedEvent, user_handler.handle_subscription_extended)
    event_bus.register_handler(UserBlockedEvent, user_handler.handle_user_blocked)
    
    # Register order event handlers
    order_handler = OrderEventHandler(notification_service, analytics_service)
    event_bus.register_handler(OrderCreatedEvent, order_handler.handle_order_created)
    event_bus.register_handler(OrderCompletedEvent, order_handler.handle_order_completed)
    
    # Register payment event handlers
    payment_handler = PaymentEventHandler(notification_service, analytics_service)
    event_bus.register_handler(PaymentProcessedEvent, payment_handler.handle_payment_processed)
    event_bus.register_handler(PaymentFailedEvent, payment_handler.handle_payment_failed)
"""