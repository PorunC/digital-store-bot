"""Background tasks for notification processing."""

import logging
from datetime import datetime, timedelta
from typing import List

from src.application.services import (
    UserApplicationService,
    OrderApplicationService
)
from src.infrastructure.notifications.notification_service import (
    NotificationService,
    NotificationChannel
)
from src.core.containers import ApplicationContainer
from dependency_injector.wiring import inject, Provide

logger = logging.getLogger(__name__)


class NotificationTasks:
    """Background tasks for notification processing."""
    
    def __init__(self):
        """Initialize NotificationTasks without service injection to avoid async context issues."""
        pass
    
    @inject
    async def send_trial_expiry_reminders(
        self,
        user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
        notification_service: NotificationService = Provide[ApplicationContainer.notification_service]
    ) -> dict:
        """Send reminders to users whose trials are expiring soon."""
        try:
            logger.info("Starting trial expiry reminder processing")
            
            # Get users with trials expiring in 1 day
            expiring_users = await user_service.find_users_with_expiring_trials(days=1)
            
            sent_count = 0
            for user in expiring_users:
                try:
                    await notification_service.send_trial_expiry_reminder(
                        user=user,
                        channels=[NotificationChannel.TELEGRAM]
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send trial expiry reminder to user {user.id}: {e}")
            
            result = {
                "status": "success",
                "users_processed": len(expiring_users),
                "notifications_sent": sent_count,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Trial expiry reminders sent: {sent_count}/{len(expiring_users)}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process trial expiry reminders: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    @inject
    async def send_subscription_renewal_reminders(
        self,
        user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
        notification_service: NotificationService = Provide[ApplicationContainer.notification_service]
    ) -> dict:
        """Send renewal reminders to users with expiring premium subscriptions."""
        try:
            logger.info("Starting subscription renewal reminder processing")
            
            # Get users with premium expiring in 3 days
            expiring_users = await user_service.find_users_with_expiring_premium(days=3)
            
            sent_count = 0
            for user in expiring_users:
                try:
                    await notification_service.send_subscription_renewal_reminder(
                        user=user,
                        channels=[NotificationChannel.TELEGRAM]
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send renewal reminder to user {user.id}: {e}")
            
            result = {
                "status": "success", 
                "users_processed": len(expiring_users),
                "notifications_sent": sent_count,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Renewal reminders sent: {sent_count}/{len(expiring_users)}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process renewal reminders: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    @inject
    async def send_daily_admin_summary(
        self,
        user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
        order_service: OrderApplicationService = Provide[ApplicationContainer.order_service],
        notification_service: NotificationService = Provide[ApplicationContainer.notification_service]
    ) -> dict:
        """Send daily summary to administrators."""
        try:
            logger.info("Starting daily admin summary processing")
            
            # Get statistics for the summary
            user_stats = await user_service.get_daily_user_statistics()
            order_stats = await order_service.get_daily_order_statistics()
            
            await notification_service.send_admin_daily_summary(
                user_stats=user_stats,
                order_stats=order_stats,
                channels=[NotificationChannel.TELEGRAM]
            )
            
            result = {
                "status": "success",
                "summary_sent": True,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info("Daily admin summary sent successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to send daily admin summary: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    @inject
    async def process_pending_notifications(
        self,
        notification_service: NotificationService = Provide[ApplicationContainer.notification_service]
    ) -> dict:
        """Process any pending notifications in the queue."""
        try:
            logger.info("Starting pending notifications processing")
            
            # This would typically process a notification queue
            # For now, just return success
            
            result = {
                "status": "success",
                "processed_count": 0,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info("Pending notifications processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process pending notifications: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }