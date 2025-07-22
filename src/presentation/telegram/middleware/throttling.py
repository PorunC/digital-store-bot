"""Throttling middleware for rate limiting user interactions."""

import asyncio
import time
import logging
from typing import Dict, Any, Callable, Awaitable
from collections import defaultdict, deque

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for throttling user requests to prevent spam and abuse.
    """
    
    def __init__(
        self,
        default_rate: float = 1.0,  # requests per second
        default_burst: int = 3,     # burst allowance
        admin_exempt: bool = True   # exempt admins from throttling
    ):
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.admin_exempt = admin_exempt
        
        # Rate limiting storage
        self.user_tokens: Dict[int, float] = defaultdict(lambda: default_burst)
        self.user_last_update: Dict[int, float] = defaultdict(time.time)
        self.user_violations: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))
        
        # Admin user IDs (should be loaded from config)
        self.admin_ids = {123456789}  # Configure admin IDs
        
        # Rate limit configurations for different operations
        self.rate_configs = {
            "message": {"rate": 1.0, "burst": 3},
            "callback": {"rate": 2.0, "burst": 5},
            "command": {"rate": 0.5, "burst": 2},
            "inline_query": {"rate": 3.0, "burst": 10}
        }
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Process the update through throttling middleware."""
        
        # Get user ID from the update
        user_id = self._get_user_id(event)
        if not user_id:
            return await handler(event, data)
        
        # Skip throttling for admins if configured
        if self.admin_exempt and user_id in self.admin_ids:
            return await handler(event, data)
        
        # Determine rate limit configuration
        rate_config = self._get_rate_config(event)
        
        # Check if user is rate limited
        if await self._is_rate_limited(user_id, rate_config):
            await self._handle_rate_limit_violation(event, user_id)
            return
        
        # Update user token bucket
        self._update_tokens(user_id, rate_config)
        
        # Continue to handler
        return await handler(event, data)
    
    def _get_user_id(self, event: Update) -> int:
        """Extract user ID from update."""
        if event.message:
            return event.message.from_user.id if event.message.from_user else None
        elif event.callback_query:
            return event.callback_query.from_user.id
        elif event.inline_query:
            return event.inline_query.from_user.id
        elif event.chosen_inline_result:
            return event.chosen_inline_result.from_user.id
        return None
    
    def _get_rate_config(self, event: Update) -> Dict[str, float]:
        """Get rate configuration based on update type."""
        if event.message:
            if event.message.text and event.message.text.startswith('/'):
                return self.rate_configs["command"]
            return self.rate_configs["message"]
        elif event.callback_query:
            return self.rate_configs["callback"]
        elif event.inline_query:
            return self.rate_configs["inline_query"]
        
        return {"rate": self.default_rate, "burst": self.default_burst}
    
    async def _is_rate_limited(self, user_id: int, config: Dict[str, float]) -> bool:
        """Check if user is rate limited using token bucket algorithm."""
        current_time = time.time()
        
        # Get current tokens and last update time
        tokens = self.user_tokens[user_id]
        last_update = self.user_last_update[user_id]
        
        # Calculate time passed and tokens to add
        time_passed = current_time - last_update
        tokens_to_add = time_passed * config["rate"]
        
        # Update tokens (capped at burst limit)
        new_tokens = min(config["burst"], tokens + tokens_to_add)
        
        # Check if we have enough tokens
        if new_tokens >= 1.0:
            self.user_tokens[user_id] = new_tokens - 1.0
            self.user_last_update[user_id] = current_time
            return False
        else:
            # Rate limited - record violation
            self.user_violations[user_id].append(current_time)
            return True
    
    def _update_tokens(self, user_id: int, config: Dict[str, float]) -> None:
        """Update user tokens after successful request."""
        current_time = time.time()
        self.user_last_update[user_id] = current_time
    
    async def _handle_rate_limit_violation(self, event: Update, user_id: int) -> None:
        """Handle rate limit violation."""
        violations = self.user_violations[user_id]
        current_time = time.time()
        
        # Count recent violations (last 60 seconds)
        recent_violations = sum(1 for v in violations if current_time - v < 60)
        
        # Progressive response based on violation count
        if recent_violations <= 3:
            message = "⏰ Slow down! You're sending messages too quickly."
        elif recent_violations <= 6:
            message = "🚫 Please wait a moment before sending another message."
        else:
            message = "🚨 Too many requests! Please wait 30 seconds before trying again."
            
            # Add temporary cooldown for repeat offenders
            await asyncio.sleep(1)
        
        # Send throttling message
        try:
            if event.message:
                await event.message.answer(message)
            elif event.callback_query:
                await event.callback_query.answer(message, show_alert=True)
        except Exception as e:
            logger.error(f"Error sending throttling message: {e}")
        
        # Log violation
        logger.warning(f"Rate limit violation by user {user_id}, recent violations: {recent_violations}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get throttling statistics for a user."""
        current_time = time.time()
        violations = self.user_violations[user_id]
        
        return {
            "user_id": user_id,
            "current_tokens": self.user_tokens[user_id],
            "last_update": self.user_last_update[user_id],
            "total_violations": len(violations),
            "recent_violations": sum(1 for v in violations if current_time - v < 300),  # Last 5 minutes
            "is_admin": user_id in self.admin_ids
        }
    
    def reset_user_limits(self, user_id: int) -> None:
        """Reset rate limits for a user (admin function)."""
        self.user_tokens[user_id] = self.default_burst
        self.user_last_update[user_id] = time.time()
        self.user_violations[user_id].clear()
        logger.info(f"Reset rate limits for user {user_id}")
    
    def add_admin(self, user_id: int) -> None:
        """Add user to admin exemption list."""
        self.admin_ids.add(user_id)
        logger.info(f"Added user {user_id} to admin exemption list")
    
    def remove_admin(self, user_id: int) -> None:
        """Remove user from admin exemption list."""
        self.admin_ids.discard(user_id)
        logger.info(f"Removed user {user_id} from admin exemption list")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global throttling statistics."""
        current_time = time.time()
        total_users = len(self.user_tokens)
        active_users = sum(1 for last_update in self.user_last_update.values() 
                          if current_time - last_update < 300)  # Active in last 5 minutes
        
        total_violations = sum(len(violations) for violations in self.user_violations.values())
        recent_violations = sum(
            sum(1 for v in violations if current_time - v < 60)
            for violations in self.user_violations.values()
        )
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_violations": total_violations,
            "recent_violations": recent_violations,
            "admin_count": len(self.admin_ids),
            "default_rate": self.default_rate,
            "default_burst": self.default_burst
        }