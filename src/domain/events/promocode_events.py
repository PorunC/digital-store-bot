"""Promocode domain events."""

from typing import Optional

from .base import DomainEvent


class PromocodeCreated(DomainEvent):
    """Event published when a promocode is created."""

    @classmethod
    def create(
        cls,
        promocode_id: str,
        code: str,
        promocode_type: str,
        duration_days: int,
        max_uses: int
    ) -> "PromocodeCreated":
        """Create PromocodeCreated event."""
        return super().create(
            aggregate_id=promocode_id,
            aggregate_type="Promocode",
            code=code,
            promocode_type=promocode_type,
            duration_days=duration_days,
            max_uses=max_uses
        )


class PromocodeActivated(DomainEvent):
    """Event published when a promocode is activated."""

    @classmethod
    def create(
        cls,
        promocode_id: str,
        code: str,
        user_id: str,
        promocode_type: str,
        duration_days: int
    ) -> "PromocodeActivated":
        """Create PromocodeActivated event."""
        return super().create(
            aggregate_id=promocode_id,
            aggregate_type="Promocode",
            code=code,
            user_id=user_id,
            promocode_type=promocode_type,
            duration_days=duration_days
        )


class PromocodeExpired(DomainEvent):
    """Event published when a promocode expires."""

    @classmethod
    def create(
        cls,
        promocode_id: str,
        code: str
    ) -> "PromocodeExpired":
        """Create PromocodeExpired event."""
        return super().create(
            aggregate_id=promocode_id,
            aggregate_type="Promocode",
            code=code
        )


class PromocodeDeactivated(DomainEvent):
    """Event published when a promocode is deactivated."""

    @classmethod
    def create(
        cls,
        promocode_id: str,
        code: str,
        reason: Optional[str] = None
    ) -> "PromocodeDeactivated":
        """Create PromocodeDeactivated event."""
        return super().create(
            aggregate_id=promocode_id,
            aggregate_type="Promocode",
            code=code,
            reason=reason
        )