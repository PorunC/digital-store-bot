"""Invite link domain events."""

from typing import Any, Dict, Optional

from .base import DomainEvent


class InviteCreated(DomainEvent):
    """Event published when an invite link is created."""

    @classmethod
    def create(
        cls,
        invite_id: str,
        name: str,
        hash_code: str,
        campaign: Optional[str] = None
    ) -> "InviteCreated":
        """Create InviteCreated event."""
        return super().create(
            aggregate_id=invite_id,
            aggregate_type="Invite",
            name=name,
            hash_code=hash_code,
            campaign=campaign
        )


class InviteClicked(DomainEvent):
    """Event published when an invite link is clicked."""

    @classmethod
    def create(
        cls,
        invite_id: str,
        name: str,
        hash_code: str,
        total_clicks: int,
        user_info: Dict[str, Any]
    ) -> "InviteClicked":
        """Create InviteClicked event."""
        return super().create(
            aggregate_id=invite_id,
            aggregate_type="Invite",
            name=name,
            hash_code=hash_code,
            total_clicks=total_clicks,
            user_info=user_info
        )


class InviteConverted(DomainEvent):
    """Event published when an invite link converts."""

    @classmethod
    def create(
        cls,
        invite_id: str,
        name: str,
        hash_code: str,
        user_id: str,
        conversion_type: str,
        total_conversions: int
    ) -> "InviteConverted":
        """Create InviteConverted event."""
        return super().create(
            aggregate_id=invite_id,
            aggregate_type="Invite",
            name=name,
            hash_code=hash_code,
            user_id=user_id,
            conversion_type=conversion_type,
            total_conversions=total_conversions
        )


class InviteDeactivated(DomainEvent):
    """Event published when an invite link is deactivated."""

    @classmethod
    def create(
        cls,
        invite_id: str,
        name: str,
        hash_code: str,
        reason: Optional[str] = None
    ) -> "InviteDeactivated":
        """Create InviteDeactivated event."""
        return super().create(
            aggregate_id=invite_id,
            aggregate_type="Invite",
            name=name,
            hash_code=hash_code,
            reason=reason
        )