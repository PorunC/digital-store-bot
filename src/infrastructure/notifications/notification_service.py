"""Core notification service for payment and order events."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from src.domain.entities.order import Order
from src.domain.entities.user import User
from .telegram_notifier import TelegramNotifier
from .email_notifier import EmailNotifier

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    ORDER_CREATED = "order_created"
    ORDER_EXPIRED = "order_expired"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    TRIAL_STARTED = "trial_started"
    TRIAL_EXPIRING = "trial_expiring"
    REFERRAL_REWARD = "referral_reward"
    PROMOCODE_USED = "promocode_used"
    ADMIN_ALERT = "admin_alert"


class NotificationChannel(Enum):
    """Notification delivery channels."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationService:
    """Service for sending notifications across different channels."""
    
    def __init__(self):
        self.notifiers = {}
        self.enabled_channels = [NotificationChannel.TELEGRAM]  # Configure as needed
    
    async def send_payment_success_notification(
        self,
        user: User,
        order: Order,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send payment success notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.PAYMENT_SUCCESS,
            "user": user,
            "order": order,
            "template_data": {
                "user_name": user.profile.first_name,
                "product_name": order.product_name,
                "amount": f"${order.amount.amount:.2f}",
                "currency": order.amount.currency.upper(),
                "order_id": str(order.id)[:8],
                "completion_date": order.completed_at.strftime("%Y-%m-%d %H:%M") if order.completed_at else None
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_payment_failed_notification(
        self,
        user: User,
        order: Order,
        error_message: str = "Payment could not be processed",
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send payment failure notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.PAYMENT_FAILED,
            "user": user,
            "order": order,
            "template_data": {
                "user_name": user.profile.first_name,
                "product_name": order.product_name,
                "amount": f"${order.amount.amount:.2f}",
                "currency": order.amount.currency.upper(),
                "order_id": str(order.id)[:8],
                "error_message": error_message,
                "support_command": "/support"
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_order_created_notification(
        self,
        user: User,
        order: Order,
        payment_url: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send order created notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.ORDER_CREATED,
            "user": user,
            "order": order,
            "template_data": {
                "user_name": user.profile.first_name,
                "product_name": order.product_name,
                "amount": f"${order.amount.amount:.2f}",
                "currency": order.amount.currency.upper(),
                "order_id": str(order.id)[:8],
                "payment_url": payment_url,
                "expires_at": order.expires_at.strftime("%Y-%m-%d %H:%M") if order.expires_at else None
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_subscription_expiring_notification(
        self,
        user: User,
        days_remaining: int,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send subscription expiring notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.SUBSCRIPTION_EXPIRING,
            "user": user,
            "template_data": {
                "user_name": user.profile.first_name,
                "days_remaining": days_remaining,
                "subscription_type": user.subscription_type.value.title(),
                "expires_date": user.subscription_expires_at.strftime("%Y-%m-%d") if user.subscription_expires_at else None,
                "renewal_command": "/catalog"
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_trial_started_notification(
        self,
        user: User,
        trial_days: int,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send trial started notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.TRIAL_STARTED,
            "user": user,
            "template_data": {
                "user_name": user.profile.first_name,
                "trial_days": trial_days,
                "expires_date": user.subscription_expires_at.strftime("%Y-%m-%d") if user.subscription_expires_at else None,
                "catalog_command": "/catalog"
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_referral_reward_notification(
        self,
        user: User,
        referred_user_name: str,
        reward_days: int,
        reward_type: str,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send referral reward notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.REFERRAL_REWARD,
            "user": user,
            "template_data": {
                "user_name": user.profile.first_name,
                "referred_user_name": referred_user_name,
                "reward_days": reward_days,
                "reward_type": reward_type,
                "total_referrals": user.total_referrals
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_promocode_used_notification(
        self,
        user: User,
        promocode: str,
        effect_description: str,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send promocode used notification."""
        channels = channels or self.enabled_channels
        
        notification_data = {
            "type": NotificationType.PROMOCODE_USED,
            "user": user,
            "template_data": {
                "user_name": user.profile.first_name,
                "promocode": promocode,
                "effect_description": effect_description
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def send_admin_alert(
        self,
        alert_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, bool]:
        """Send admin alert notification."""
        channels = channels or [NotificationChannel.TELEGRAM]  # Admin alerts primarily via Telegram
        
        notification_data = {
            "type": NotificationType.ADMIN_ALERT,
            "template_data": {
                "alert_type": alert_type,
                "message": message,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "metadata": metadata or {}
            }
        }
        
        return await self._send_notification(notification_data, channels)
    
    async def _send_notification(
        self,
        notification_data: Dict[str, Any],
        channels: List[NotificationChannel]
    ) -> Dict[str, bool]:
        """Send notification through specified channels."""
        results = {}
        
        for channel in channels:
            try:
                notifier = self.notifiers.get(channel)
                if not notifier:
                    logger.warning(f"No notifier available for channel: {channel.value}")
                    results[channel.value] = False
                    continue
                
                success = await notifier.send_notification(notification_data)
                results[channel.value] = success
                
                if success:
                    logger.info(f"Notification sent successfully via {channel.value}")
                else:
                    logger.warning(f"Failed to send notification via {channel.value}")
                    
            except Exception as e:
                logger.error(f"Error sending notification via {channel.value}: {e}")
                results[channel.value] = False
        
        return results
    
    async def send_bulk_notifications(
        self,
        notifications: List[Dict[str, Any]],
        channels: List[NotificationChannel]
    ) -> List[Dict[str, bool]]:
        """Send multiple notifications in batch."""
        results = []
        
        for notification_data in notifications:
            try:
                result = await self._send_notification(notification_data, channels)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in bulk notification: {e}")
                results.append({channel.value: False for channel in channels})
        
        return results
    
    def add_notifier(self, channel: NotificationChannel, notifier) -> None:
        """Add a custom notifier for a channel."""
        self.notifiers[channel] = notifier
    
    def enable_channel(self, channel: NotificationChannel) -> None:
        """Enable a notification channel."""
        if channel not in self.enabled_channels:
            self.enabled_channels.append(channel)
    
    def disable_channel(self, channel: NotificationChannel) -> None:
        """Disable a notification channel."""
        if channel in self.enabled_channels:
            self.enabled_channels.remove(channel)
    
    def get_enabled_channels(self) -> List[NotificationChannel]:
        """Get list of enabled notification channels."""
        return self.enabled_channels.copy()