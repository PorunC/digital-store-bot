"""User context middleware for automatic user management."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser

from src.application.services.user_service import UserApplicationService
from src.domain.entities.user import User
from src.shared.dependency_injection import container

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseMiddleware):
    """Middleware to automatically manage user context."""

    def __init__(self):
        self.user_service: Optional[UserApplicationService] = None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Provide user context to the handler."""
        try:
            # Get user service from container
            if not self.user_service:
                self.user_service = container.resolve(UserApplicationService)

            # Extract Telegram user from event
            telegram_user = data.get("event_from_user")
            if not telegram_user or not isinstance(telegram_user, TelegramUser):
                # Skip if no user context (e.g., channel posts)
                return await handler(event, data)

            # Get or create user
            user = await self._get_or_create_user(telegram_user, data)
            
            if user:
                # Add user to handler data
                data["user"] = user
                data["user_id"] = str(user.id)
                data["telegram_user"] = telegram_user
                
                # Record user activity
                try:
                    await self.user_service.record_user_activity(str(user.id))
                except Exception as e:
                    logger.warning(f"Failed to record user activity: {e}")

            return await handler(event, data)

        except Exception as e:
            logger.error(f"Error in user context middleware: {e}")
            # Continue without user context on error
            return await handler(event, data)

    async def _get_or_create_user(
        self,
        telegram_user: TelegramUser,
        data: Dict[str, Any]
    ) -> Optional[User]:
        """Get existing user or create new one."""
        try:
            # Try to get existing user
            user = await self.user_service.get_user_by_telegram_id(telegram_user.id)
            
            if user:
                # Update user profile if needed
                if (user.profile.first_name != telegram_user.first_name or
                    user.profile.username != telegram_user.username):
                    
                    user = await self.user_service.update_user_profile(
                        str(user.id),
                        first_name=telegram_user.first_name,
                        username=telegram_user.username,
                        language_code=telegram_user.language_code
                    )
                return user

            # Create new user
            # Extract referrer info from start parameter if available
            referrer_id = self._extract_referrer_id(data)
            invite_source = self._extract_invite_source(data)

            user = await self.user_service.register_user(
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                username=telegram_user.username,
                language_code=telegram_user.language_code or "en",
                referrer_id=referrer_id,
                invite_source=invite_source
            )

            logger.info(f"New user registered: {telegram_user.id} ({telegram_user.first_name})")
            return user

        except Exception as e:
            logger.error(f"Error getting/creating user {telegram_user.id}: {e}")
            return None

    def _extract_referrer_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract referrer ID from start parameter."""
        try:
            # Look for start parameter in command args
            command = data.get("command")
            if command and hasattr(command, "args") and command.args:
                args = command.args
                if args.startswith("ref_"):
                    return args[4:]  # Remove "ref_" prefix
                elif args.startswith("invite_"):
                    return args[7:]  # Remove "invite_" prefix
            
            return None
        except Exception:
            return None

    def _extract_invite_source(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract invite source from start parameter."""
        try:
            # Look for invite source in command args
            command = data.get("command")
            if command and hasattr(command, "args") and command.args:
                args = command.args
                if args.startswith("source_"):
                    return args[7:]  # Remove "source_" prefix
                elif "_" in args:
                    # Format: ref_userid_source or invite_code_source
                    parts = args.split("_")
                    if len(parts) >= 3:
                        return parts[2]
            
            return None
        except Exception:
            return None