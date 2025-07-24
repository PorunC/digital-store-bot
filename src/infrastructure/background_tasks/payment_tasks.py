"""Background tasks for payment processing."""

import logging
from datetime import datetime, timedelta
from typing import List

from src.application.services import (
    OrderApplicationService,
    PaymentApplicationService,
    UserApplicationService
)
from src.infrastructure.notifications.notification_service import (
    NotificationService,
    NotificationChannel
)
from src.core.containers import container

logger = logging.getLogger(__name__)


class PaymentTasks:
    """Background tasks for payment processing."""
    
    def __init__(self):
        self.order_service: OrderApplicationService = container.order_service()
        self.payment_service: PaymentApplicationService = container.payment_service()
        self.user_service: UserApplicationService = container.user_service()
        self.notification_service: NotificationService = container.notification_service()
    
    async def process_expired_orders(self) -> dict:
        """Process orders that have expired without payment."""
        try:
            logger.info("Starting expired orders processing")
            
            # Get and process expired orders
            expired_orders = await self.order_service.process_expired_orders()
            
            # Send notifications for expired orders
            notification_count = 0
            for order in expired_orders:
                try:
                    user = await self.user_service.get_user_by_id(str(order.user_id))
                    if user:
                        await self.notification_service.send_order_expired_notification(
                            user=user,
                            order=order,
                            channels=[NotificationChannel.TELEGRAM]
                        )
                        notification_count += 1
                except Exception as e:
                    logger.error(f"Error sending expiry notification for order {order.id}: {e}")
            
            result = {
                "processed_orders": len(expired_orders),
                "notifications_sent": notification_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Expired orders processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing expired orders: {e}")
            return {
                "processed_orders": 0,
                "notifications_sent": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_pending_payments(self) -> dict:
        """Check status of pending payments with external gateways."""
        try:
            logger.info("Starting pending payments check")
            
            # Get pending orders
            from src.domain.entities.order import OrderStatus
            pending_orders = await self.order_service.get_orders_by_status(OrderStatus.PENDING)
            
            checked_count = 0
            updated_count = 0
            
            for order in pending_orders:
                if not order.payment_id or not order.payment_method:
                    continue
                
                try:
                    # Check payment status
                    status_info = await self.payment_service.check_payment_status(str(order.id))
                    checked_count += 1
                    
                    # Update order if status changed
                    if status_info.get("status") == "paid" and order.status == OrderStatus.PENDING:
                        await self.order_service.mark_as_paid(
                            str(order.id),
                            status_info.get("external_payment_id")
                        )
                        await self.order_service.mark_as_completed(str(order.id))
                        updated_count += 1
                        
                        # Send success notification
                        user = await self.user_service.get_user_by_id(str(order.user_id))
                        if user:
                            await self.notification_service.send_payment_success_notification(
                                user=user,
                                order=order,
                                channels=[NotificationChannel.TELEGRAM]
                            )
                    
                except Exception as e:
                    logger.error(f"Error checking payment for order {order.id}: {e}")
            
            result = {
                "pending_orders": len(pending_orders),
                "checked_payments": checked_count,
                "updated_orders": updated_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Pending payments check completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking pending payments: {e}")
            return {
                "pending_orders": 0,
                "checked_payments": 0,
                "updated_orders": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_payment_data(self) -> dict:
        """Clean up old payment data and logs."""
        try:
            logger.info("Starting payment data cleanup")
            
            # This would involve cleaning up:
            # - Old webhook logs
            # - Expired payment sessions
            # - Temporary payment data
            
            # For now, return a placeholder result
            result = {
                "cleaned_webhooks": 0,
                "cleaned_sessions": 0,
                "cleaned_temp_data": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Payment data cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up payment data: {e}")
            return {
                "cleaned_webhooks": 0,
                "cleaned_sessions": 0,
                "cleaned_temp_data": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_payment_reports(self) -> dict:
        """Generate payment and revenue reports."""
        try:
            logger.info("Starting payment reports generation")
            
            # Get revenue statistics
            revenue_stats = await self.order_service.get_revenue_stats()
            order_stats = await self.order_service.get_order_stats()
            payment_stats = await self.payment_service.get_payment_statistics()
            
            # Generate daily report data
            report_data = {
                "date": datetime.utcnow().date().isoformat(),
                "revenue": revenue_stats,
                "orders": order_stats,
                "payments": payment_stats,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Here you would typically save this to a reporting database
            # or send to an analytics service
            
            result = {
                "report_generated": True,
                "total_revenue": revenue_stats.get("total_revenue", 0),
                "total_orders": revenue_stats.get("order_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Payment reports generated: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating payment reports: {e}")
            return {
                "report_generated": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def monitor_payment_gateways(self) -> dict:
        """Monitor payment gateway health and connectivity."""
        try:
            logger.info("Starting payment gateway monitoring")
            
            gateway_stats = {}
            
            # Check each payment method
            from src.domain.entities.order import PaymentMethod
            from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
            
            factory: PaymentGatewayFactory = container.payment_gateway_factory()
            
            for method in PaymentMethod:
                try:
                    gateway = factory.get_gateway(method)
                    
                    # Basic health check (could be enhanced with actual API calls)
                    gateway_stats[method.value] = {
                        "available": gateway.is_available(),
                        "enabled": gateway.is_enabled,
                        "last_checked": datetime.utcnow().isoformat()
                    }
                    
                except Exception as e:
                    gateway_stats[method.value] = {
                        "available": False,
                        "enabled": False,
                        "error": str(e),
                        "last_checked": datetime.utcnow().isoformat()
                    }
            
            # Check for any offline gateways and alert admins
            offline_gateways = [
                method for method, stats in gateway_stats.items()
                if not stats.get("available", False)
            ]
            
            if offline_gateways:
                await self.notification_service.send_admin_alert(
                    alert_type="payment_gateway_offline",
                    message=f"Payment gateways offline: {', '.join(offline_gateways)}",
                    metadata={"offline_gateways": offline_gateways}
                )
            
            result = {
                "gateways_checked": len(gateway_stats),
                "offline_gateways": len(offline_gateways),
                "gateway_stats": gateway_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Payment gateway monitoring completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error monitoring payment gateways: {e}")
            return {
                "gateways_checked": 0,
                "offline_gateways": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def reconcile_payments(self) -> dict:
        """Reconcile payments between internal records and gateway records."""
        try:
            logger.info("Starting payment reconciliation")
            
            # This would involve:
            # 1. Getting all completed orders from last 24 hours
            # 2. Checking each payment against gateway records
            # 3. Identifying discrepancies
            # 4. Flagging issues for manual review
            
            # Placeholder implementation
            result = {
                "orders_checked": 0,
                "discrepancies_found": 0,
                "reconciled_payments": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Payment reconciliation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error reconciling payments: {e}")
            return {
                "orders_checked": 0,
                "discrepancies_found": 0,
                "reconciled_payments": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }