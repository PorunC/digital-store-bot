"""SQLAlchemy Promocode repository implementation."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.promocode import Promocode, PromocodeType, PromocodeStatus
from src.domain.repositories.promocode_repository import PromocodeRepository
from ..models.promocode import PromocodeModel


class SqlAlchemyPromocodeRepository(PromocodeRepository):
    """SQLAlchemy implementation of Promocode repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[Promocode]:
        """Get promocode by ID."""
        try:
            promocode_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(PromocodeModel).where(PromocodeModel.id == promocode_uuid)
        result = await self.session.execute(stmt)
        promocode_model = result.scalar_one_or_none()
        
        if promocode_model:
            return self._model_to_entity(promocode_model)
        return None

    async def get_all(self) -> List[Promocode]:
        """Get all promocodes."""
        stmt = select(PromocodeModel).order_by(PromocodeModel.created_at.desc())
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def add(self, entity: Promocode) -> Promocode:
        """Add a new promocode."""
        promocode_model = self._entity_to_model(entity)
        self.session.add(promocode_model)
        await self.session.flush()
        await self.session.refresh(promocode_model)
        
        return self._model_to_entity(promocode_model)

    async def update(self, entity: Promocode) -> Promocode:
        """Update an existing promocode."""
        stmt = select(PromocodeModel).where(PromocodeModel.id == entity.id)
        result = await self.session.execute(stmt)
        promocode_model = result.scalar_one_or_none()
        
        if not promocode_model:
            raise ValueError(f"Promocode with ID {entity.id} not found")

        # Update fields
        promocode_model.code = entity.code
        promocode_model.promocode_type = entity.promocode_type.value
        promocode_model.duration_days = entity.duration_days
        promocode_model.discount_percent = entity.discount_percent
        promocode_model.discount_amount = entity.discount_amount
        promocode_model.max_uses = entity.max_uses
        promocode_model.current_uses = entity.current_uses
        promocode_model.status = entity.status.value
        promocode_model.expires_at = entity.expires_at
        promocode_model.activated_at = entity.activated_at
        promocode_model.deactivated_at = entity.deactivated_at
        promocode_model.metadata = entity.metadata
        promocode_model.version = entity.version

        await self.session.flush()
        return self._model_to_entity(promocode_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete a promocode by ID."""
        try:
            promocode_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(PromocodeModel).where(PromocodeModel.id == promocode_uuid)
        result = await self.session.execute(stmt)
        promocode_model = result.scalar_one_or_none()
        
        if promocode_model:
            await self.session.delete(promocode_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if promocode exists."""
        try:
            promocode_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(PromocodeModel.id).where(PromocodeModel.id == promocode_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_code(self, code: str) -> Optional[Promocode]:
        """Find promocode by code."""
        stmt = select(PromocodeModel).where(PromocodeModel.code == code.upper())
        result = await self.session.execute(stmt)
        promocode_model = result.scalar_one_or_none()
        
        if promocode_model:
            return self._model_to_entity(promocode_model)
        return None

    async def find_active_codes(self) -> List[Promocode]:
        """Find active promocodes."""
        now = datetime.utcnow()
        stmt = select(PromocodeModel).where(
            and_(
                PromocodeModel.status == PromocodeStatus.ACTIVE.value,
                or_(
                    PromocodeModel.expires_at.is_(None),
                    PromocodeModel.expires_at > now
                ),
                or_(
                    PromocodeModel.max_uses == -1,
                    PromocodeModel.current_uses < PromocodeModel.max_uses
                )
            )
        ).order_by(PromocodeModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def find_by_type(self, promocode_type: PromocodeType) -> List[Promocode]:
        """Find promocodes by type."""
        stmt = select(PromocodeModel).where(
            PromocodeModel.promocode_type == promocode_type.value
        ).order_by(PromocodeModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def find_expired_codes(self) -> List[Promocode]:
        """Find expired promocodes."""
        now = datetime.utcnow()
        stmt = select(PromocodeModel).where(
            and_(
                PromocodeModel.expires_at.is_not(None),
                PromocodeModel.expires_at <= now,
                PromocodeModel.status != PromocodeStatus.EXPIRED.value
            )
        ).order_by(PromocodeModel.expires_at)
        
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def find_exhausted_codes(self) -> List[Promocode]:
        """Find promocodes that have reached max uses."""
        stmt = select(PromocodeModel).where(
            and_(
                PromocodeModel.max_uses != -1,
                PromocodeModel.current_uses >= PromocodeModel.max_uses,
                PromocodeModel.status == PromocodeStatus.ACTIVE.value
            )
        ).order_by(PromocodeModel.created_at)
        
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def search_codes(self, query: str) -> List[Promocode]:
        """Search promocodes by query."""
        search_term = f"%{query.upper()}%"
        
        stmt = select(PromocodeModel).where(
            func.upper(PromocodeModel.code).like(search_term)
        ).order_by(PromocodeModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        promocode_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in promocode_models]

    async def get_usage_stats(self) -> dict:
        """Get promocode usage statistics."""
        # Total promocodes by status
        status_stmt = select(
            PromocodeModel.status,
            func.count(PromocodeModel.id).label('count')
        ).group_by(PromocodeModel.status)
        
        status_result = await self.session.execute(status_stmt)
        status_data = status_result.all()

        # Total usage
        usage_stmt = select(
            func.sum(PromocodeModel.current_uses).label('total_uses'),
            func.count(PromocodeModel.id).label('total_codes'),
            func.avg(PromocodeModel.current_uses).label('avg_uses_per_code')
        )
        
        usage_result = await self.session.execute(usage_stmt)
        usage_data = usage_result.first()

        # Usage by type
        type_stmt = select(
            PromocodeModel.promocode_type,
            func.count(PromocodeModel.id).label('codes'),
            func.sum(PromocodeModel.current_uses).label('uses')
        ).group_by(PromocodeModel.promocode_type)
        
        type_result = await self.session.execute(type_stmt)
        type_data = type_result.all()

        return {
            "codes_by_status": {
                row.status: row.count for row in status_data
            },
            "total_uses": usage_data.total_uses or 0,
            "total_codes": usage_data.total_codes or 0,
            "average_uses_per_code": float(usage_data.avg_uses_per_code or 0),
            "usage_by_type": [
                {
                    "type": row.promocode_type,
                    "codes": row.codes,
                    "uses": row.uses
                }
                for row in type_data
            ]
        }

    def _model_to_entity(self, model: PromocodeModel) -> Promocode:
        """Convert PromocodeModel to Promocode entity."""
        promocode = Promocode(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            code=model.code,
            promocode_type=PromocodeType(model.promocode_type),
            duration_days=model.duration_days,
            discount_percent=model.discount_percent,
            discount_amount=model.discount_amount,
            max_uses=model.max_uses,
            current_uses=model.current_uses,
            status=PromocodeStatus(model.status),
            expires_at=model.expires_at,
            activated_at=model.activated_at,
            deactivated_at=model.deactivated_at,
            metadata=model.metadata or {}
        )

        # Clear domain events as they come from persistence
        promocode.clear_domain_events()
        return promocode

    def _entity_to_model(self, entity: Promocode) -> PromocodeModel:
        """Convert Promocode entity to PromocodeModel."""
        return PromocodeModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            code=entity.code,
            promocode_type=entity.promocode_type.value,
            duration_days=entity.duration_days,
            discount_percent=entity.discount_percent,
            discount_amount=entity.discount_amount,
            max_uses=entity.max_uses,
            current_uses=entity.current_uses,
            status=entity.status.value,
            expires_at=entity.expires_at,
            activated_at=entity.activated_at,
            deactivated_at=entity.deactivated_at,
            metadata=entity.metadata
        )