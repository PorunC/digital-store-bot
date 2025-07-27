"""User context middleware for automatic user management."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser

from src.domain.entities.user import User
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseMiddleware):
    """Middleware to automatically manage user context."""

    def __init__(self):
        """Initialize UserContextMiddleware without container dependency to avoid async context issues."""
        pass

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Provide user context to the handler."""
        try:
            # Ensure we have database session and unit of work from DatabaseMiddleware
            unit_of_work = data.get("unit_of_work")
            if not unit_of_work:
                logger.error("No unit_of_work found in middleware data - DatabaseMiddleware not properly configured")
                # Continue without user context
                data["user"] = None
                data["user_id"] = None
                data["telegram_user"] = data.get("event_from_user")
                return await handler(event, data)

            # Extract Telegram user from event
            telegram_user = data.get("event_from_user")
            if not telegram_user or not isinstance(telegram_user, TelegramUser):
                # Skip if no user context (e.g., channel posts)
                return await handler(event, data)

            # Get or create user using the unit_of_work from DatabaseMiddleware
            user = await self._get_or_create_user(telegram_user, data, unit_of_work)
            
            if user:
                # Add user to handler data
                data["user"] = user
                data["user_id"] = str(user.id)
                data["telegram_user"] = telegram_user
                
                # Record user activity
                try:
                    await self._record_user_activity(user.id, unit_of_work)
                except Exception as e:
                    logger.warning(f"Failed to record user activity: {e}")

            return await handler(event, data)

        except Exception as e:
            logger.error(f"Error in user context middleware: {e}")
            # Continue without user context on error - provide None user
            data["user"] = None
            data["user_id"] = None
            data["telegram_user"] = data.get("event_from_user")
            return await handler(event, data)

    async def _get_or_create_user(
        self,
        telegram_user: TelegramUser,
        data: Dict[str, Any],
        unit_of_work
    ) -> Optional[User]:
        """Get existing user or create new one using direct repository access."""
        try:
            # Create repository directly with the session from unit_of_work
            user_repository = SqlAlchemyUserRepository(unit_of_work.session)
            
            # Try to get existing user
            user = await user_repository.get_by_telegram_id(telegram_user.id)
            
            if user:
                # Update user profile if needed
                if (user.profile.first_name != telegram_user.first_name or
                    user.profile.username != telegram_user.username):
                    
                    user.profile.first_name = telegram_user.first_name
                    user.profile.username = telegram_user.username
                    if telegram_user.language_code:
                        user.profile.language_code = telegram_user.language_code
                    user = await user_repository.update(user)
                return user

            # Create new user
            # Extract referrer info from start parameter if available
            referrer_id = self._extract_referrer_id(data)
            invite_source = self._extract_invite_source(data)

            # Convert referrer_id if it's not a UUID
            referrer_uuid = None
            if referrer_id:
                import uuid
                try:
                    # Try direct UUID conversion
                    referrer_uuid = uuid.UUID(referrer_id)
                except ValueError:
                    # If not UUID, try to find user by telegram_id
                    try:
                        referrer_user = await user_repository.get_by_telegram_id(int(referrer_id))
                        if referrer_user:
                            referrer_uuid = referrer_user.id
                    except (ValueError, TypeError):
                        referrer_uuid = None

            # Create new user entity
            user = User.create(
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                username=telegram_user.username,
                language_code=telegram_user.language_code or "en",
                referrer_id=referrer_uuid,
                invite_source=invite_source
            )

            # Save to database
            user = await user_repository.add(user)

            logger.info(f"New user registered: {telegram_user.id} ({telegram_user.first_name})")
            return user

        except Exception as e:
            logger.error(f"Error getting/creating user {telegram_user.id}: {e}", exc_info=True)
            return None

    async def _record_user_activity(self, user_id, unit_of_work) -> None:
        """Record user activity using direct repository access."""
        try:
            # Create repository directly with the session from unit_of_work
            user_repository = SqlAlchemyUserRepository(unit_of_work.session)
            
            # Get user and update last activity
            user = await user_repository.get_by_id(str(user_id))
            if user:
                user.record_activity()
                await user_repository.update(user)
                
        except Exception as e:
            logger.warning(f"Failed to record user activity for {user_id}: {e}")

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