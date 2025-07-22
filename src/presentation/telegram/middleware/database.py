"""Database middleware for providing database sessions."""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.infrastructure.database.manager import DatabaseManager
from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session to handlers."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Provide database session to the handler."""
        async with self.db_manager.get_session() as session:
            try:
                # Provide session and unit of work to handler
                data["session"] = session
                data["unit_of_work"] = SqlAlchemyUnitOfWork(session)
                
                # Call the handler
                result = await handler(event, data)
                
                # Commit session if no explicit transaction was used
                await session.commit()
                
                return result
                
            except Exception as e:
                # Rollback on error
                await session.rollback()
                logger.error(f"Database error in middleware: {e}")
                raise