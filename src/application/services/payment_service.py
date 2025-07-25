"""Payment application service with complete functionality."""

import uuid
from typing import Dict, List, Optional

from src.domain.entities.order import Order, PaymentMethod
from src.domain.repositories.order_repository import OrderRepository
from src.domain.repositories.base import UnitOfWork
from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
from src.infrastructure.external.payment_gateways.base import PaymentGateway, PaymentData, PaymentResult
from src.shared.events import event_bus


class PaymentApplicationService:
    """Payment application service handling payment processing."""

    def __init__(
        self,
        payment_gateway_factory: PaymentGatewayFactory,
        unit_of_work: UnitOfWork,
        order_repository_factory = None
    ):
        self.payment_gateway_factory = payment_gateway_factory
        self.unit_of_work = unit_of_work
        self._order_repository_factory = order_repository_factory
        
    def _get_order_repository(self) -> OrderRepository:
        """Get order repository using factory or fallback to direct creation."""
        if self._order_repository_factory and hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return self._order_repository_factory(self.unit_of_work.session)
            
        # Fallback to anti-pattern during transition period
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyOrderRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")

    async def create_payment(
        self,
        order_id: str,
        payment_method: PaymentMethod,
        return_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> PaymentResult:
        """Create a payment for an order."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status not in ["pending", "processing"]:
                raise ValueError(f"Cannot create payment for order {order_id} - invalid status: {order.status}")

            # Get appropriate payment gateway
            gateway = self.payment_gateway_factory.get_gateway(payment_method)
            
            # Create payment data
            payment_data = PaymentData(
                order_id=order_id,
                user_id=str(order.user_id),
                product_id=order.product_id,
                amount=order.amount.amount,
                currency=order.amount.currency,
                description=f"Payment for {order.product_name}",
                user_telegram_id=order.user_telegram_id,
                return_url=return_url,
                metadata=metadata or {}
            )

            # Process payment through gateway
            result = await gateway.create_payment(payment_data)

            if result.success:
                # Update order with payment information
                order.set_payment_info(
                    payment_id=result.payment_id,
                    external_payment_id=result.external_payment_id,
                    payment_gateway=payment_method,
                    payment_url=result.payment_url
                )
                order.payment_method = payment_method

                order = await self._get_order_repository().update(order)
                await self._publish_events(order)
                await self.unit_of_work.commit()

            return result

    async def process_webhook(
        self,
        payment_method: PaymentMethod,
        webhook_data: Dict,
        signature: Optional[str] = None
    ) -> Optional[Order]:
        """Process payment webhook."""
        async with self.unit_of_work:
            # Get appropriate payment gateway
            gateway = self.payment_gateway_factory.get_gateway(payment_method)
            
            # Validate webhook
            if not await gateway.validate_webhook(webhook_data, signature):
                raise ValueError("Invalid webhook signature")

            # Extract payment information
            payment_info = await gateway.extract_payment_info(webhook_data)
            
            if not payment_info.get("order_id"):
                raise ValueError("Order ID not found in webhook data")

            order = await self._get_order_repository().get_by_id(payment_info["order_id"])
            if not order:
                raise ValueError(f"Order {payment_info['order_id']} not found")

            # Update order based on payment status
            if payment_info.get("status") == "paid":
                order.mark_as_paid(payment_info.get("external_payment_id"))
                
                order = await self._get_order_repository().update(order)
                await self._publish_events(order)
                await self.unit_of_work.commit()
                
                return order

            elif payment_info.get("status") == "failed":
                order.cancel(f"Payment failed: {payment_info.get('error_message', 'Unknown error')}")
                
                order = await self._get_order_repository().update(order)
                await self._publish_events(order)
                await self.unit_of_work.commit()
                
                return order

            return None

    async def check_payment_status(self, order_id: str) -> Dict:
        """Check payment status for an order."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

        if not order.payment_id or not order.payment_method:
            return {
                "status": "no_payment",
                "message": "No payment information found for this order"
            }

            # Get appropriate payment gateway
            gateway = self.payment_gateway_factory.get_gateway(order.payment_method)
            
            # Check status through gateway
            status = await gateway.get_payment_status(order.payment_id)
            
            return {
                "order_id": order_id,
                "payment_id": order.payment_id,
                "external_payment_id": order.external_payment_id,
                "status": status.get("status"),
                "amount": order.amount.amount,
                "currency": order.amount.currency,
                "gateway": order.payment_gateway,
                "created_at": order.created_at.isoformat(),
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                "details": status
            }

    async def refund_payment(
        self,
        order_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict:
        """Refund a payment."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status != "paid":
                raise ValueError(f"Cannot refund order {order_id} - not paid")

            if not order.payment_id or not order.payment_method:
                raise ValueError(f"No payment information found for order {order_id}")

            # Get appropriate payment gateway
            gateway = self.payment_gateway_factory.get_gateway(order.payment_method)
            
            # Process refund
            refund_amount = amount or order.amount.amount
            result = await gateway.refund_payment(
                payment_id=order.payment_id,
                amount=refund_amount,
                reason=reason
            )

            if result.get("success"):
                # Update order status
                order.cancel(f"Refunded: {reason or 'No reason provided'}")
                
                order = await self._get_order_repository().update(order)
                await self._publish_events(order)
                await self.unit_of_work.commit()

            return result

    async def get_supported_payment_methods(self) -> List[PaymentMethod]:
        """Get list of supported payment methods."""
        return self.payment_gateway_factory.get_supported_methods()

    async def get_payment_method_config(self, payment_method: PaymentMethod) -> Dict:
        """Get configuration for a payment method."""
        gateway = self.payment_gateway_factory.get_gateway(payment_method)
        return await gateway.get_config()

    async def validate_payment_amount(
        self,
        payment_method: PaymentMethod,
        amount: float,
        currency: str
    ) -> Dict:
        """Validate payment amount for a method."""
        gateway = self.payment_gateway_factory.get_gateway(payment_method)
        return await gateway.validate_amount(amount, currency)

    async def get_payment_statistics(self) -> Dict:
        """Get payment statistics."""
        async with self.unit_of_work:
            # Get overall revenue stats
            revenue_stats = await self._get_order_repository().get_revenue_stats()
            
            # Get orders by status for payment analysis
            order_stats = await self._get_order_repository().get_order_stats()
            
            # Calculate payment method distribution
            all_orders = await self._get_order_repository().get_all()
            payment_method_stats = {}
            
            for order in all_orders:
                if order.payment_method:
                    method = order.payment_method
                    if method not in payment_method_stats:
                        payment_method_stats[method] = {
                            "count": 0,
                            "revenue": 0.0,
                            "currency": order.amount.currency
                        }
                    
                    payment_method_stats[method]["count"] += 1
                    if order.status in ["paid", "completed"]:
                        payment_method_stats[method]["revenue"] += order.amount.amount

            return {
                "revenue": revenue_stats,
                "orders": order_stats,
                "payment_methods": payment_method_stats,
                "supported_methods": [method for method in self.get_supported_payment_methods()]
            }

    async def _publish_events(self, order: Order) -> None:
        """Publish domain events."""
        events = order.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        order.clear_domain_events()