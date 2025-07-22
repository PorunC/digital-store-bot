"""Example command handlers for CQRS pattern implementation.

This module demonstrates command handlers that modify state and perform business operations.
Commands are used for write operations and state changes.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.user import User
from src.domain.value_objects.money import Money
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.events.bus import EventBus


# Command Data Transfer Objects (DTOs)
@dataclass
class CreateUserCommand:
    """Command to create a new user."""
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: str = "en"


@dataclass
class UpdateUserProfileCommand:
    """Command to update user profile."""
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


@dataclass
class BlockUserCommand:
    """Command to block a user."""
    user_id: str
    reason: str
    blocked_by: str
    blocked_until: Optional[datetime] = None


@dataclass
class UnblockUserCommand:
    """Command to unblock a user."""
    user_id: str
    unblocked_by: str


@dataclass
class AddCreditsCommand:
    """Command to add credits to user account."""
    user_id: str
    amount: float
    currency: str = "USD"
    reason: str = "Manual credit addition"
    added_by: str


# Command Results
@dataclass
class CommandResult:
    """Base command result."""
    success: bool
    message: str
    data: Optional[dict] = None


@dataclass
class CreateUserResult(CommandResult):
    """Result for create user command."""
    user_id: Optional[str] = None


# Command Handlers
class UserCommandHandler:
    """Handler for user-related commands."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        event_bus: EventBus
    ):
        self.user_repository = user_repository
        self.event_bus = event_bus
    
    async def handle_create_user(self, command: CreateUserCommand) -> CreateUserResult:
        """Handle create user command."""
        try:
            # Check if user already exists
            existing_user = await self.user_repository.get_by_telegram_id(command.telegram_id)
            if existing_user:
                return CreateUserResult(
                    success=False,
                    message=f"User with Telegram ID {command.telegram_id} already exists",
                    user_id=existing_user.id
                )
            
            # Create new user
            user = User.create(
                telegram_id=command.telegram_id,
                username=command.username,
                first_name=command.first_name,
                last_name=command.last_name,
                language_code=command.language_code
            )
            
            # Save user
            await self.user_repository.save(user)
            
            # Publish domain events
            for event in user.domain_events:
                await self.event_bus.publish(event)
            user.clear_events()
            
            return CreateUserResult(
                success=True,
                message="User created successfully",
                user_id=user.id
            )
            
        except Exception as e:
            return CreateUserResult(
                success=False,
                message=f"Failed to create user: {str(e)}"
            )
    
    async def handle_update_user_profile(self, command: UpdateUserProfileCommand) -> CommandResult:
        """Handle update user profile command."""
        try:
            user = await self.user_repository.get_by_id(command.user_id)
            if not user:
                return CommandResult(
                    success=False,
                    message=f"User {command.user_id} not found"
                )
            
            # Update profile
            if command.first_name is not None:
                user.profile.first_name = command.first_name
            if command.last_name is not None:
                user.profile.last_name = command.last_name
            if command.username is not None:
                user.profile.username = command.username
            if command.language_code is not None:
                user.profile.language_code = command.language_code
            
            user.profile.updated_at = datetime.utcnow()
            
            # Save changes
            await self.user_repository.save(user)
            
            # Publish events
            for event in user.domain_events:
                await self.event_bus.publish(event)
            user.clear_events()
            
            return CommandResult(
                success=True,
                message="User profile updated successfully"
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to update user profile: {str(e)}"
            )
    
    async def handle_block_user(self, command: BlockUserCommand) -> CommandResult:
        """Handle block user command."""
        try:
            user = await self.user_repository.get_by_id(command.user_id)
            if not user:
                return CommandResult(
                    success=False,
                    message=f"User {command.user_id} not found"
                )
            
            # Block user
            user.block(command.reason, command.blocked_until)
            
            # Save changes
            await self.user_repository.save(user)
            
            # Publish events
            for event in user.domain_events:
                await self.event_bus.publish(event)
            user.clear_events()
            
            return CommandResult(
                success=True,
                message=f"User blocked successfully. Reason: {command.reason}"
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to block user: {str(e)}"
            )
    
    async def handle_unblock_user(self, command: UnblockUserCommand) -> CommandResult:
        """Handle unblock user command."""
        try:
            user = await self.user_repository.get_by_id(command.user_id)
            if not user:
                return CommandResult(
                    success=False,
                    message=f"User {command.user_id} not found"
                )
            
            # Unblock user
            user.unblock()
            
            # Save changes
            await self.user_repository.save(user)
            
            # Publish events
            for event in user.domain_events:
                await self.event_bus.publish(event)
            user.clear_events()
            
            return CommandResult(
                success=True,
                message="User unblocked successfully"
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to unblock user: {str(e)}"
            )
    
    async def handle_add_credits(self, command: AddCreditsCommand) -> CommandResult:
        """Handle add credits command."""
        try:
            user = await self.user_repository.get_by_id(command.user_id)
            if not user:
                return CommandResult(
                    success=False,
                    message=f"User {command.user_id} not found"
                )
            
            # Add credits
            credits = Money(command.amount, command.currency)
            user.add_credits(credits, command.reason)
            
            # Save changes
            await self.user_repository.save(user)
            
            # Publish events
            for event in user.domain_events:
                await self.event_bus.publish(event)
            user.clear_events()
            
            return CommandResult(
                success=True,
                message=f"Added {credits.amount} {credits.currency} to user account",
                data={
                    "amount_added": credits.amount,
                    "currency": credits.currency,
                    "new_balance": user.balance.amount
                }
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to add credits: {str(e)}"
            )


# Example usage:
"""
# In your service layer or controller:

command_handler = UserCommandHandler(user_repository, event_bus)

# Create user
create_command = CreateUserCommand(
    telegram_id=123456789,
    username="john_doe",
    first_name="John",
    last_name="Doe"
)
result = await command_handler.handle_create_user(create_command)

# Update user profile
update_command = UpdateUserProfileCommand(
    user_id="user-123",
    first_name="Johnny",
    language_code="es"
)
result = await command_handler.handle_update_user_profile(update_command)

# Block user
block_command = BlockUserCommand(
    user_id="user-123",
    reason="Violation of terms",
    blocked_by="admin-456"
)
result = await command_handler.handle_block_user(block_command)
"""