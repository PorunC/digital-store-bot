"""SQLAlchemy Order repository implementation."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.order import Order, OrderStatus, PaymentMethod
from src.domain.repositories.order_repository import OrderRepository
from src.domain.value_objects.money import Money
from ..models.order import OrderModel


class SqlAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of Order repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[Order]:
        """Get order by ID."""
        try:
            order_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(OrderModel).where(OrderModel.id == order_uuid)
        result = await self.session.execute(stmt)
        order_model = result.scalar_one_or_none()
        
        if order_model:
            return self._model_to_entity(order_model)
        return None

    async def get_all(self) -> List[Order]:
        """Get all orders."""
        stmt = select(OrderModel).order_by(OrderModel.created_at.desc())
        result = await self.session.execute(stmt)
        order_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in order_models]

    async def add(self, entity: Order) -> Order:
        """Add a new order."""
        order_model = self._entity_to_model(entity)
        self.session.add(order_model)
        await self.session.flush()
        await self.session.refresh(order_model)
        
        return self._model_to_entity(order_model)

    async def update(self, entity: Order) -> Order:
        """Update an existing order."""
        stmt = select(OrderModel).where(OrderModel.id == entity.id)
        result = await self.session.execute(stmt)
        order_model = result.scalar_one_or_none()
        
        if not order_model:
            raise ValueError(f"Order with ID {entity.id} not found")

        # Update fields
        order_model.payment_id = entity.payment_id
        order_model.external_payment_id = entity.external_payment_id
        order_model.product_name = entity.product_name
        order_model.product_description = entity.product_description
        order_model.amount = entity.amount.amount
        order_model.currency = entity.amount.currency
        order_model.quantity = entity.quantity
        order_model.payment_method = str(entity.payment_method) if entity.payment_method else None
        order_model.payment_gateway = entity.payment_gateway
        order_model.payment_url = entity.payment_url
        order_model.status = entity.status.value
        order_model.expires_at = entity.expires_at
        order_model.paid_at = entity.paid_at
        order_model.completed_at = entity.completed_at
        order_model.cancelled_at = entity.cancelled_at
        order_model.notes = entity.notes
        order_model.referrer_id = entity.referrer_id
        order_model.promocode = entity.promocode
        order_model.is_trial = entity.is_trial
        order_model.is_extend = entity.is_extend
        order_model.version = entity.version

        await self.session.flush()
        return self._model_to_entity(order_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete an order by ID."""
        try:
            order_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(OrderModel).where(OrderModel.id == order_uuid)
        result = await self.session.execute(stmt)
        order_model = result.scalar_one_or_none()
        
        if order_model:
            await self.session.delete(order_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if order exists."""
        try:
            order_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(OrderModel.id).where(OrderModel.id == order_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_user_id(self, user_id: uuid.UUID) -> List[Order]:
        """Find orders by user ID."""
        stmt = select(OrderModel).where(
            OrderModel.user_id == user_id
        ).order_by(OrderModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        order_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in order_models]

    async def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find orders by status."""
        stmt = select(OrderModel).where(
            OrderModel.status == status.value
        ).order_by(OrderModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        order_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in order_models]

    async def find_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Find order by payment ID."""
        stmt = select(OrderModel).where(
            OrderModel.payment_id == payment_id
        )
        result = await self.session.execute(stmt)
        order_model = result.scalar_one_or_none()
        
        if order_model:
            return self._model_to_entity(order_model)
        return None

    async def find_expired(self) -> List[Order]:
        """Find expired orders."""
        now = datetime.utcnow()
        stmt = select(OrderModel).where(
            and_(
                OrderModel.expires_at.is_not(None),
                OrderModel.expires_at < now,
                OrderModel.status == OrderStatus.PENDING.value
            )
        ).order_by(OrderModel.expires_at)
        
        result = await self.session.execute(stmt)
        order_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in order_models]

    async def find_pending_orders(self, user_id: uuid.UUID) -> List[Order]:
        """Find pending orders for a user."""
        stmt = select(OrderModel).where(
            and_(
                OrderModel.user_id == user_id,
                OrderModel.status == OrderStatus.PENDING.value
            )
        ).order_by(OrderModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        order_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in order_models]

    async def get_revenue_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get revenue statistics."""
        # Base query for completed orders
        base_query = select(OrderModel).where(
            OrderModel.status.in_([
                OrderStatus.COMPLETED.value,
                OrderStatus.PAID.value
            ])
        )
        
        # Add date filters if provided
        if start_date:
            base_query = base_query.where(OrderModel.completed_at >= start_date)
        if end_date:
            base_query = base_query.where(OrderModel.completed_at <= end_date)

        # Total revenue
        revenue_stmt = select(
            func.sum(OrderModel.amount * OrderModel.quantity).label('total_revenue'),
            func.count(OrderModel.id).label('order_count'),
            func.avg(OrderModel.amount * OrderModel.quantity).label('avg_order_value')
        ).select_from(base_query.subquery())
        
        revenue_result = await self.session.execute(revenue_stmt)
        revenue_data = revenue_result.first()

        # Revenue by currency
        currency_stmt = select(
            OrderModel.currency,
            func.sum(OrderModel.amount * OrderModel.quantity).label('revenue'),
            func.count(OrderModel.id).label('orders')
        ).select_from(base_query.subquery()).group_by(OrderModel.currency)
        
        currency_result = await self.session.execute(currency_stmt)
        currency_data = currency_result.all()

        return {
            "total_revenue": float(revenue_data.total_revenue or 0),
            "order_count": revenue_data.order_count or 0,
            "average_order_value": float(revenue_data.avg_order_value or 0),
            "revenue_by_currency": [
                {
                    "currency": row.currency,
                    "revenue": float(row.revenue),
                    "orders": row.orders
                }
                for row in currency_data
            ]
        }

    async def get_order_stats(self) -> dict:
        """Get order statistics."""
        # Order counts by status
        status_stmt = select(
            OrderModel.status,
            func.count(OrderModel.id).label('count')
        ).group_by(OrderModel.status)
        
        status_result = await self.session.execute(status_stmt)
        status_data = status_result.all()

        # Recent order trends (last 30 days)
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        trend_stmt = select(
            func.date(OrderModel.created_at).label('date'),
            func.count(OrderModel.id).label('orders')
        ).where(
            OrderModel.created_at >= thirty_days_ago
        ).group_by(func.date(OrderModel.created_at)).order_by('date')
        
        trend_result = await self.session.execute(trend_stmt)
        trend_data = trend_result.all()

        return {
            "orders_by_status": {
                row.status: row.count for row in status_data
            },
            "daily_trends": [
                {
                    "date": row.date.isoformat(),
                    "orders": row.orders
                }
                for row in trend_data
            ]
        }

    def _model_to_entity(self, model: OrderModel) -> Order:
        """Convert OrderModel to Order entity."""
        amount = Money(amount=model.amount, currency=model.currency)
        
        order = Order(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            user_id=model.user_id,
            product_id=model.product_id,
            payment_id=model.payment_id,
            external_payment_id=model.external_payment_id,
            product_name=model.product_name,
            product_description=model.product_description,
            amount=amount,
            quantity=model.quantity,
            payment_method=PaymentMethod(model.payment_method) if model.payment_method else None,
            payment_gateway=model.payment_gateway,
            payment_url=model.payment_url,
            status=OrderStatus(model.status),
            expires_at=model.expires_at,
            paid_at=model.paid_at,
            completed_at=model.completed_at,
            cancelled_at=model.cancelled_at,
            notes=model.notes,
            referrer_id=model.referrer_id,
            promocode=model.promocode,
            is_trial=model.is_trial,
            is_extend=model.is_extend
        )

        # Clear domain events as they come from persistence
        order.clear_domain_events()
        return order

    def _entity_to_model(self, entity: Order) -> OrderModel:
        """Convert Order entity to OrderModel."""
        return OrderModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            user_id=entity.user_id,
            product_id=entity.product_id,
            payment_id=entity.payment_id,
            external_payment_id=entity.external_payment_id,
            product_name=entity.product_name,
            product_description=entity.product_description,
            amount=entity.amount.amount,
            currency=entity.amount.currency,
            quantity=entity.quantity,
            payment_method=str(entity.payment_method) if entity.payment_method else None,
            payment_gateway=entity.payment_gateway,
            payment_url=entity.payment_url,
            status=entity.status.value,
            expires_at=entity.expires_at,
            paid_at=entity.paid_at,
            completed_at=entity.completed_at,
            cancelled_at=entity.cancelled_at,
            notes=entity.notes,
            referrer_id=entity.referrer_id,
            promocode=entity.promocode,
            is_trial=entity.is_trial,
            is_extend=entity.is_extend
        )