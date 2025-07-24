"""SQLAlchemy Invite repository implementation."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.invite import Invite, InviteStatus
from src.domain.repositories.invite_repository import InviteRepository
from ..models.invite import InviteModel


class SqlAlchemyInviteRepository(InviteRepository):
    """SQLAlchemy implementation of Invite repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[Invite]:
        """Get invite by ID."""
        try:
            invite_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(InviteModel).where(InviteModel.id == invite_uuid)
        result = await self.session.execute(stmt)
        invite_model = result.scalar_one_or_none()
        
        if invite_model:
            return self._model_to_entity(invite_model)
        return None

    async def get_all(self) -> List[Invite]:
        """Get all invites."""
        stmt = select(InviteModel).order_by(InviteModel.created_at.desc())
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def add(self, entity: Invite) -> Invite:
        """Add a new invite."""
        invite_model = self._entity_to_model(entity)
        self.session.add(invite_model)
        await self.session.flush()
        await self.session.refresh(invite_model)
        
        return self._model_to_entity(invite_model)

    async def update(self, entity: Invite) -> Invite:
        """Update an existing invite."""
        stmt = select(InviteModel).where(InviteModel.id == entity.id)
        result = await self.session.execute(stmt)
        invite_model = result.scalar_one_or_none()
        
        if not invite_model:
            raise ValueError(f"Invite with ID {entity.id} not found")

        # Update fields
        invite_model.name = entity.name
        invite_model.hash_code = entity.hash_code
        invite_model.description = entity.description
        invite_model.campaign = entity.campaign
        invite_model.total_clicks = entity.total_clicks
        invite_model.total_conversions = entity.total_conversions
        invite_model.conversion_reward_days = entity.conversion_reward_days
        invite_model.status = entity.status.value
        invite_model.expires_at = entity.expires_at
        invite_model.last_clicked_at = entity.last_clicked_at
        invite_model.deactivated_at = entity.deactivated_at
        # Note: Invite entity doesn't have metadata field
        invite_model.version = entity.version

        await self.session.flush()
        return self._model_to_entity(invite_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete an invite by ID."""
        try:
            invite_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(InviteModel).where(InviteModel.id == invite_uuid)
        result = await self.session.execute(stmt)
        invite_model = result.scalar_one_or_none()
        
        if invite_model:
            await self.session.delete(invite_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if invite exists."""
        try:
            invite_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(InviteModel.id).where(InviteModel.id == invite_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_hash(self, hash_code: str) -> Optional[Invite]:
        """Find invite by hash code."""
        stmt = select(InviteModel).where(InviteModel.hash_code == hash_code)
        result = await self.session.execute(stmt)
        invite_model = result.scalar_one_or_none()
        
        if invite_model:
            return self._model_to_entity(invite_model)
        return None

    async def find_by_name(self, name: str) -> Optional[Invite]:
        """Find invite by name."""
        stmt = select(InviteModel).where(InviteModel.name == name)
        result = await self.session.execute(stmt)
        invite_model = result.scalar_one_or_none()
        
        if invite_model:
            return self._model_to_entity(invite_model)
        return None

    async def find_active_invites(self) -> List[Invite]:
        """Find active invites."""
        now = datetime.utcnow()
        stmt = select(InviteModel).where(
            and_(
                InviteModel.status == InviteStatus.ACTIVE.value,
                or_(
                    InviteModel.expires_at.is_(None),
                    InviteModel.expires_at > now
                )
            )
        ).order_by(InviteModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def find_by_campaign(self, campaign: str) -> List[Invite]:
        """Find invites by campaign."""
        stmt = select(InviteModel).where(
            InviteModel.campaign == campaign
        ).order_by(InviteModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def find_expired_invites(self) -> List[Invite]:
        """Find expired invites."""
        now = datetime.utcnow()
        stmt = select(InviteModel).where(
            and_(
                InviteModel.expires_at.is_not(None),
                InviteModel.expires_at <= now,
                InviteModel.status != InviteStatus.EXPIRED.value
            )
        ).order_by(InviteModel.expires_at)
        
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def search_invites(self, query: str) -> List[Invite]:
        """Search invites by query."""
        search_term = f"%{query.lower()}%"
        
        stmt = select(InviteModel).where(
            or_(
                func.lower(InviteModel.name).like(search_term),
                func.lower(InviteModel.description).like(search_term),
                func.lower(InviteModel.campaign).like(search_term)
            )
        ).order_by(InviteModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def get_top_performing_invites(self, limit: int = 10, days: int = 30) -> List[Invite]:
        """Get top performing invites by conversion rate."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(InviteModel).where(
            and_(
                InviteModel.created_at >= start_date,
                InviteModel.total_clicks > 0
            )
        ).order_by(
            (InviteModel.total_conversions / InviteModel.total_clicks).desc(),
            InviteModel.total_conversions.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        invite_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in invite_models]

    async def get_invite_stats(self) -> dict:
        """Get invite statistics."""
        # Total invites by status
        status_stmt = select(
            InviteModel.status,
            func.count(InviteModel.id).label('count')
        ).group_by(InviteModel.status)
        
        status_result = await self.session.execute(status_stmt)
        status_data = status_result.all()

        # Overall performance
        performance_stmt = select(
            func.sum(InviteModel.total_clicks).label('total_clicks'),
            func.sum(InviteModel.total_conversions).label('total_conversions'),
            func.count(InviteModel.id).label('total_invites'),
            func.avg(InviteModel.total_clicks).label('avg_clicks_per_invite'),
            func.avg(InviteModel.total_conversions).label('avg_conversions_per_invite')
        )
        
        performance_result = await self.session.execute(performance_stmt)
        performance_data = performance_result.first()

        # Campaign performance
        campaign_stmt = select(
            InviteModel.campaign,
            func.count(InviteModel.id).label('invites'),
            func.sum(InviteModel.total_clicks).label('clicks'),
            func.sum(InviteModel.total_conversions).label('conversions')
        ).where(
            InviteModel.campaign.is_not(None)
        ).group_by(InviteModel.campaign)
        
        campaign_result = await self.session.execute(campaign_stmt)
        campaign_data = campaign_result.all()

        total_clicks = performance_data.total_clicks or 0
        total_conversions = performance_data.total_conversions or 0

        return {
            "invites_by_status": {
                row.status: row.count for row in status_data
            },
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_invites": performance_data.total_invites or 0,
            "overall_conversion_rate": (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
            "average_clicks_per_invite": float(performance_data.avg_clicks_per_invite or 0),
            "average_conversions_per_invite": float(performance_data.avg_conversions_per_invite or 0),
            "campaign_performance": [
                {
                    "campaign": row.campaign,
                    "invites": row.invites,
                    "clicks": row.clicks,
                    "conversions": row.conversions,
                    "conversion_rate": (row.conversions / row.clicks * 100) if row.clicks > 0 else 0
                }
                for row in campaign_data
            ]
        }

    def _model_to_entity(self, model: InviteModel) -> Invite:
        """Convert InviteModel to Invite entity."""
        invite = Invite(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            name=model.name,
            hash_code=model.hash_code,
            description=model.description,
            campaign=model.campaign,
            total_clicks=model.total_clicks,
            total_conversions=model.total_conversions,
            conversion_reward_days=model.conversion_reward_days,
            status=InviteStatus(model.status),
            expires_at=model.expires_at,
            last_clicked_at=model.last_clicked_at,
            deactivated_at=model.deactivated_at,
            # Note: Invite entity doesn't have metadata field
        )

        # Clear domain events as they come from persistence
        invite.clear_domain_events()
        return invite

    def _entity_to_model(self, entity: Invite) -> InviteModel:
        """Convert Invite entity to InviteModel."""
        return InviteModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            name=entity.name,
            hash_code=entity.hash_code,
            description=entity.description,
            campaign=entity.campaign,
            total_clicks=entity.total_clicks,
            total_conversions=entity.total_conversions,
            conversion_reward_days=entity.conversion_reward_days,
            status=entity.status.value,
            expires_at=entity.expires_at,
            last_clicked_at=entity.last_clicked_at,
            deactivated_at=entity.deactivated_at,
            # Note: Invite entity doesn't have metadata field
        )