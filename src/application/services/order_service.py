"""Order application service with complete functionality."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.order import Order, OrderStatus, PaymentMethod
from src.domain.repositories.order_repository import OrderRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork
from src.domain.value_objects.money import Money
from src.shared.events import event_bus


class OrderApplicationService:
    """Order application service handling order-related operations."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        order_repository_factory = None,
        product_repository_factory = None,
        user_repository_factory = None
    ):
        self.unit_of_work = unit_of_work
        self._order_repository_factory = order_repository_factory
        self._product_repository_factory = product_repository_factory
        self._user_repository_factory = user_repository_factory
        
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
            
    def _get_product_repository(self) -> ProductRepository:
        """Get product repository using factory or fallback to direct creation."""
        if self._product_repository_factory and hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return self._product_repository_factory(self.unit_of_work.session)
            
        # Fallback to anti-pattern during transition period
        from src.infrastructure.database.repositories.product_repository import SqlAlchemyProductRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyProductRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")
            
    def _get_user_repository(self) -> UserRepository:
        """Get user repository using factory or fallback to direct creation."""
        if self._user_repository_factory and hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return self._user_repository_factory(self.unit_of_work.session)
            
        # Fallback to anti-pattern during transition period
        from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyUserRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")

    async def create_order(
        self,
        user_id: str,
        product_id: str,
        quantity: int = 1,
        payment_method: Optional[PaymentMethod] = None,
        referrer_id: Optional[str] = None,
        promocode: Optional[str] = None,
        is_trial: bool = False,
        is_extend: bool = False,
        notes: Optional[str] = None
    ) -> Order:
        """Create a new order."""
        async with self.unit_of_work:
            # Validate user exists
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            # Validate product exists and is available
            product = await self._get_product_repository().get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            if not product.is_available:
                raise ValueError(f"Product {product.name} is not available")

            if product.stock != -1 and product.stock < quantity:
                raise ValueError(f"Insufficient stock for product {product.name}")

            # Calculate total amount
            total_amount = Money(
                amount=product.price.amount * quantity,
                currency=product.price.currency
            )

            # Convert referrer_id to UUID if it's a valid UUID string
            # If it's not a UUID, try to find user by telegram_id and use their UUID
            referrer_uuid = None
            if referrer_id:
                try:
                    # First try direct UUID conversion
                    referrer_uuid = uuid.UUID(referrer_id)
                except ValueError:
                    # If not a UUID, assume it's a telegram_id and look up the user
                    try:
                        referrer_user = await self._get_user_repository().get_by_telegram_id(int(referrer_id))
                        if referrer_user:
                            referrer_uuid = referrer_user.id
                    except (ValueError, TypeError):
                        # If all conversion attempts fail, set to None
                        referrer_uuid = None
                    
            # Create order
            order = Order.create(
                user_id=uuid.UUID(user_id),
                product_id=uuid.UUID(product_id),
                product_name=product.name,
                product_description=product.description,
                amount=total_amount,
                quantity=quantity,
                referrer_id=referrer_uuid,
                promocode=promocode,
                is_trial=is_trial,
                is_extend=is_extend
            )
            
            # Set payment method if provided
            if payment_method:
                order.payment_method = payment_method
                
            # Add notes if provided
            if notes:
                order.add_note(notes)

            # Set expiration time (30 minutes for payment)
            order.set_expiration(datetime.utcnow() + timedelta(minutes=30))

            # Reserve stock with optimistic locking
            try:
                product.decrease_stock(quantity)
                await self._get_product_repository().update(product)
            except ValueError as e:
                # Stock validation failed
                raise ValueError(f"Cannot create order: {e}")
            except Exception as e:
                # Potential concurrency conflict - reload and retry once
                fresh_product = await self._get_product_repository().get_by_id(product_id)
                if fresh_product and fresh_product.stock >= quantity:
                    fresh_product.decrease_stock(quantity)
                    await self._get_product_repository().update(fresh_product)
                else:
                    raise ValueError(f"Insufficient stock for product {product.name}")

            order = await self._get_order_repository().add(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        async with self.unit_of_work:
            return await self._get_order_repository().get_by_id(order_id)

    async def get_order_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Get order by payment ID."""
        async with self.unit_of_work:
            return await self._get_order_repository().find_by_payment_id(payment_id)

    async def get_user_orders(self, user_id: str) -> List[Order]:
        """Get orders for a user."""
        async with self.unit_of_work:
            user_uuid = uuid.UUID(user_id)
            return await self._get_order_repository().find_by_user_id(user_uuid)

    async def get_pending_orders(self, user_id: str) -> List[Order]:
        """Get pending orders for a user."""
        async with self.unit_of_work:
            user_uuid = uuid.UUID(user_id)
            return await self._get_order_repository().find_pending_orders(user_uuid)

    async def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get orders by status."""
        async with self.unit_of_work:
            return await self._get_order_repository().find_by_status(status)

    async def update_payment_info(
        self,
        order_id: str,
        payment_id: str,
        external_payment_id: Optional[str] = None,
        payment_gateway: Optional[str] = None,
        payment_url: Optional[str] = None
    ) -> Order:
        """Update order payment information."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            order.set_payment_details(
                payment_method=order.payment_method,
                payment_gateway=payment_gateway or "unknown",
                payment_id=payment_id,
                external_payment_id=external_payment_id,
                payment_url=payment_url
            )

            order = await self._get_order_repository().update(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def mark_as_paid(
        self,
        order_id: str,
        external_payment_id: Optional[str] = None
    ) -> Order:
        """Mark order as paid."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
                raise ValueError(f"Cannot mark order {order_id} as paid - invalid status: {order.status}")

            order.mark_as_paid(external_payment_id)

            order = await self._get_order_repository().update(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def mark_as_completed(self, order_id: str, notes: Optional[str] = None) -> Order:
        """Mark order as completed."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status != OrderStatus.PAID:
                raise ValueError(f"Cannot mark order {order_id} as completed - must be paid first")

            order.complete(notes)

            # Update user subscription if applicable
            if not order.is_trial:
                user = await self._get_user_repository().get_by_id(str(order.user_id))
                if user:
                    product = await self._get_product_repository().get_by_id(str(order.product_id))
                    if product:
                        if order.is_extend:
                            user.extend_subscription(product.duration_days)
                        else:
                            user.extend_subscription(product.duration_days)
                        
                        user.record_purchase(order.amount.amount, order.amount.currency)
                        await self._get_user_repository().update(user)

            order = await self._get_order_repository().update(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> Order:
        """Cancel an order."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
                raise ValueError(f"Cannot cancel order {order_id} - invalid status: {order.status}")

            # Release reserved stock
            if order.status == OrderStatus.PENDING:
                product = await self._get_product_repository().get_by_id(str(order.product_id))
                if product:
                    product.increase_stock(order.quantity)
                    await self._get_product_repository().update(product)

            order.cancel(reason)

            order = await self._get_order_repository().update(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def expire_order(self, order_id: str) -> Order:
        """Expire an order due to timeout."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            if order.status != OrderStatus.PENDING:
                raise ValueError(f"Cannot expire order {order_id} - not pending")

            # Release reserved stock
            product = await self._get_product_repository().get_by_id(str(order.product_id))
            if product:
                product.increase_stock(order.quantity)
                await self._get_product_repository().update(product)

            order.expire()

            order = await self._get_order_repository().update(order)
            await self._publish_events(order)
            await self.unit_of_work.commit()
            return order

    async def process_expired_orders(self) -> List[Order]:
        """Process all expired orders with proper transaction handling."""
        import logging
        logger = logging.getLogger(__name__)
        
        # First, get expired orders in a separate transaction
        async with self.unit_of_work:
            expired_orders = await self._get_order_repository().find_expired()
            
        if not expired_orders:
            return []
            
        processed_orders = []
        failed_orders = []
        
        # Process orders in batches to avoid long-running transactions
        batch_size = 10
        for i in range(0, len(expired_orders), batch_size):
            batch = expired_orders[i:i + batch_size]
            
            async with self.unit_of_work:
                for order in batch:
                    try:
                        # Check if order is still expired (avoid race conditions)
                        current_order = await self._get_order_repository().get_by_id(str(order.id))
                        if not current_order or not current_order.is_expired:
                            continue
                            
                        # Release stock if order is still pending
                        if current_order.status == OrderStatus.PENDING:
                            product = await self._get_product_repository().get_by_id(str(current_order.product_id))
                            if product:
                                product.increase_stock(current_order.quantity)
                                await self._get_product_repository().update(product)
                        
                        # Mark order as expired
                        current_order.expire()
                        updated_order = await self._get_order_repository().update(current_order)
                        await self._publish_events(updated_order)
                        processed_orders.append(updated_order)
                        
                    except Exception as e:
                        failed_orders.append((order.id, str(e)))
                        logger.error(f"Error processing expired order {order.id}: {e}", exc_info=True)
                        
                # Commit the batch
                await self.unit_of_work.commit()
        
        if failed_orders:
            logger.warning(f"Failed to process {len(failed_orders)} expired orders: {failed_orders}")
            
        logger.info(f"Successfully processed {len(processed_orders)} expired orders")
        return processed_orders

    async def add_order_notes(self, order_id: str, notes: str) -> Order:
        """Add notes to an order."""
        async with self.unit_of_work:
            order = await self._get_order_repository().get_by_id(order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")

            existing_notes = order.notes or ""
            separator = "\n---\n" if existing_notes else ""
            new_notes = f"{existing_notes}{separator}{datetime.utcnow().isoformat()}: {notes}"
            
            order.add_note(notes)

            order = await self._get_order_repository().update(order)
            await self.unit_of_work.commit()
            return order

    async def get_revenue_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get revenue statistics."""
        async with self.unit_of_work:
            return await self._get_order_repository().get_revenue_stats(start_date, end_date)

    async def get_order_stats(self) -> dict:
        """Get order statistics."""
        async with self.unit_of_work:
            return await self._get_order_repository().get_order_stats()

    async def _publish_events(self, order: Order) -> None:
        """Publish domain events."""
        events = order.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        order.clear_domain_events()