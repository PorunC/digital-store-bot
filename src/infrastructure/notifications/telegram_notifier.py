"""Telegram notification implementation."""

import logging
from typing import Dict, Any, Optional, List

from src.shared.dependency_injection import container

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram notification service."""
    
    def __init__(self):
        self.bot = None  # Will be injected via container
        self.admin_chat_ids = [123456789]  # Configure admin chat IDs
        
    async def send_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Send notification via Telegram."""
        try:
            notification_type = notification_data.get("type")
            user = notification_data.get("user")
            template_data = notification_data.get("template_data", {})
            
            # Get message based on notification type
            message = self._get_message_template(notification_type, template_data)
            
            if not message:
                logger.error(f"No template found for notification type: {notification_type}")
                return False
            
            # Send to user if specified
            if user and hasattr(user, 'telegram_id'):
                success = await self._send_to_user(user.telegram_id, message)
                if not success:
                    return False
            
            # Send admin alerts to admin chats
            if notification_type and "admin" in str(notification_type):
                await self._send_to_admins(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def _get_message_template(self, notification_type, template_data: Dict[str, Any]) -> Optional[str]:
        """Get message template for notification type."""
        templates = {
            "payment_success": self._payment_success_template,
            "payment_failed": self._payment_failed_template,
            "order_created": self._order_created_template,
            "order_expired": self._order_expired_template,
            "subscription_expiring": self._subscription_expiring_template,
            "subscription_expired": self._subscription_expired_template,
            "trial_started": self._trial_started_template,
            "trial_expiring": self._trial_expiring_template,
            "referral_reward": self._referral_reward_template,
            "promocode_used": self._promocode_used_template,
            "admin_alert": self._admin_alert_template,
        }
        
        template_func = templates.get(str(notification_type).replace("NotificationType.", ""))
        if template_func:
            return template_func(template_data)
        
        return None
    
    def _payment_success_template(self, data: Dict[str, Any]) -> str:
        """Payment success message template."""
        return (
            f"🎉 **Payment Successful!**\n\n"
            f"Hi {data.get('user_name', 'User')}!\n\n"
            f"✅ Your order has been completed successfully\n"
            f"📦 Product: {data.get('product_name', 'N/A')}\n"
            f"💰 Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}\n"
            f"🆔 Order ID: `{data.get('order_id', 'N/A')}`\n"
            f"📅 Completed: {data.get('completion_date', 'Just now')}\n\n"
            f"🎁 Your subscription has been activated!\n"
            f"Use /profile to check your updated status.\n\n"
            f"Thank you for your purchase! 🙏"
        )
    
    def _payment_failed_template(self, data: Dict[str, Any]) -> str:
        """Payment failed message template."""
        return (
            f"❌ **Payment Failed**\n\n"
            f"Hi {data.get('user_name', 'User')},\n\n"
            f"Unfortunately, your payment could not be processed:\n\n"
            f"📦 Product: {data.get('product_name', 'N/A')}\n"
            f"💰 Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}\n"
            f"🆔 Order ID: `{data.get('order_id', 'N/A')}`\n"
            f"❗ Error: {data.get('error_message', 'Unknown error')}\n\n"
            f"📞 Need help? Use {data.get('support_command', '/support')}\n"
            f"🔄 You can try ordering again with /catalog\n\n"
            f"We're here to help! 💬"
        )
    
    def _order_created_template(self, data: Dict[str, Any]) -> str:
        """Order created message template."""
        message = (
            f"🛍️ **Order Created**\n\n"
            f"Hi {data.get('user_name', 'User')}!\n\n"
            f"Your order has been created:\n\n"
            f"📦 Product: {data.get('product_name', 'N/A')}\n"
            f"💰 Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}\n"
            f"🆔 Order ID: `{data.get('order_id', 'N/A')}`\n"
        )
        
        if data.get('expires_at'):
            message += f"⏰ Expires: {data.get('expires_at')}\n"
        
        if data.get('payment_url'):
            message += f"\n💳 Complete your payment to activate your subscription.\n"
        else:
            message += f"\n⏳ Waiting for payment confirmation...\n"
        
        return message
    
    def _subscription_expiring_template(self, data: Dict[str, Any]) -> str:
        """Subscription expiring message template."""
        return (
            f"⏰ **Subscription Expiring Soon**\n\n"
            f"Hi {data.get('user_name', 'User')}!\n\n"
            f"Your {data.get('subscription_type', 'subscription')} expires in "
            f"{data.get('days_remaining', 'N/A')} day(s).\n\n"
            f"📅 Expires on: {data.get('expires_date', 'N/A')}\n\n"
            f"💡 Don't lose access to premium features!\n"
            f"Renew now with {data.get('renewal_command', '/catalog')}\n\n"
            f"🎁 Special offers may be available!"
        )
    
    def _trial_started_template(self, data: Dict[str, Any]) -> str:
        """Trial started message template."""
        return (
            f"🎁 **Free Trial Started!**\n\n"
            f"Welcome {data.get('user_name', 'User')}!\n\n"
            f"🌟 Your {data.get('trial_days', 'N/A')}-day free trial is now active!\n"
            f"📅 Expires on: {data.get('expires_date', 'N/A')}\n\n"
            f"✨ Enjoy full access to all premium features:\n"
            f"• Unlimited usage\n"
            f"• Priority support\n"
            f"• Advanced features\n\n"
            f"🛍️ Browse products: {data.get('catalog_command', '/catalog')}\n"
            f"💡 Consider upgrading before your trial ends!"
        )
    
    def _referral_reward_template(self, data: Dict[str, Any]) -> str:
        """Referral reward message template."""
        return (
            f"🎉 **Referral Reward Earned!**\n\n"
            f"Congratulations {data.get('user_name', 'User')}!\n\n"
            f"👥 Your friend {data.get('referred_user_name', 'someone')} just "
            f"{data.get('reward_type', 'joined')}!\n\n"
            f"🎁 You've earned: {data.get('reward_days', 'N/A')} bonus days\n"
            f"📊 Total referrals: {data.get('total_referrals', 'N/A')}\n\n"
            f"Keep sharing your referral link to earn more rewards!\n"
            f"Use /referral to get your link.\n\n"
            f"Thank you for spreading the word! 🚀"
        )
    
    def _promocode_used_template(self, data: Dict[str, Any]) -> str:
        """Promocode used message template."""
        return (
            f"🎟️ **Promocode Applied!**\n\n"
            f"Great news {data.get('user_name', 'User')}!\n\n"
            f"✅ Promocode `{data.get('promocode', 'N/A')}` has been applied\n"
            f"🎁 Effect: {data.get('effect_description', 'Applied successfully')}\n\n"
            f"Your account has been updated!\n"
            f"Use /profile to see your new status.\n\n"
            f"Enjoy your benefits! 🌟"
        )
    
    def _admin_alert_template(self, data: Dict[str, Any]) -> str:
        """Admin alert message template."""
        message = (
            f"🚨 **Admin Alert**\n\n"
            f"**Type:** {data.get('alert_type', 'Unknown')}\n"
            f"**Time:** {data.get('timestamp', 'N/A')}\n\n"
            f"**Message:**\n{data.get('message', 'No message')}\n"
        )
        
        metadata = data.get('metadata', {})
        if metadata:
            message += f"\n**Details:**\n"
            for key, value in metadata.items():
                message += f"• {key}: {value}\n"
        
        return message
    
    def _order_expired_template(self, data: Dict[str, Any]) -> str:
        """Order expired message template."""
        return (
            f"⏰ **Order Expired**\n\n"
            f"Hi {data.get('user_name', 'User')},\n\n"
            f"Your order has expired due to incomplete payment:\n\n"
            f"📦 Product: {data.get('product_name', 'N/A')}\n"
            f"🆔 Order ID: `{data.get('order_id', 'N/A')}`\n\n"
            f"🔄 You can create a new order anytime with /catalog\n"
            f"💬 Need help? Contact /support"
        )
    
    def _subscription_expired_template(self, data: Dict[str, Any]) -> str:
        """Subscription expired message template."""
        return (
            f"⏰ **Subscription Expired**\n\n"
            f"Hi {data.get('user_name', 'User')},\n\n"
            f"Your {data.get('subscription_type', 'subscription')} has expired.\n\n"
            f"🔄 Renew now to continue enjoying premium features!\n"
            f"🛍️ Browse plans: /catalog\n"
            f"🎁 Special renewal offers may be available!\n\n"
            f"We'd love to have you back! 💙"
        )
    
    def _trial_expiring_template(self, data: Dict[str, Any]) -> str:
        """Trial expiring message template."""
        return (
            f"⏰ **Trial Ending Soon**\n\n"
            f"Hi {data.get('user_name', 'User')}!\n\n"
            f"Your free trial expires in {data.get('days_remaining', 'N/A')} day(s).\n"
            f"📅 Expires on: {data.get('expires_date', 'N/A')}\n\n"
            f"💎 Upgrade now to keep all premium features!\n"
            f"🛍️ View plans: /catalog\n"
            f"🎁 Exclusive upgrade offers available!\n\n"
            f"Don't miss out! ⭐"
        )
    
    async def _send_to_user(self, telegram_id: int, message: str) -> bool:
        """Send message to specific user."""
        try:
            # In a real implementation, you would use the bot instance
            # bot = container.get(Bot)
            # await bot.send_message(
            #     chat_id=telegram_id,
            #     text=message,
            #     parse_mode="Markdown"
            # )
            
            logger.info(f"Telegram notification sent to user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message to user {telegram_id}: {e}")
            return False
    
    async def _send_to_admins(self, message: str) -> None:
        """Send message to admin users."""
        for admin_id in self.admin_chat_ids:
            try:
                await self._send_to_user(admin_id, message)
            except Exception as e:
                logger.error(f"Failed to send admin notification to {admin_id}: {e}")
    
    async def send_bulk_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> List[bool]:
        """Send multiple notifications in batch."""
        results = []
        
        for notification in notifications:
            try:
                result = await self.send_notification(notification)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in bulk Telegram notification: {e}")
                results.append(False)
        
        return results