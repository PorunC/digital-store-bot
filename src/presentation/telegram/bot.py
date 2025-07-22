"""Telegram bot implementation."""

import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from infrastructure.configuration.settings import Settings
from shared.dependency_injection import inject

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot adapter."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.bot = Bot(
            token=settings.bot.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dispatcher = Dispatcher()
        
    async def start(self) -> None:
        """Start the Telegram bot."""
        try:
            # Setup middleware and handlers
            await self._setup_middleware()
            await self._setup_handlers()
            
            # Start polling or webhook
            if self.settings.external.webhook_url:
                await self._start_webhook()
            else:
                await self._start_polling()
                
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise

    async def _setup_middleware(self) -> None:
        """Setup bot middleware."""
        # TODO: Add middleware for database, authentication, etc.
        pass

    async def _setup_handlers(self) -> None:
        """Setup message handlers."""
        # TODO: Register command and message handlers
        pass

    async def _start_polling(self) -> None:
        """Start bot in polling mode."""
        logger.info("Starting bot in polling mode")
        await self.dispatcher.start_polling(self.bot)

    async def _start_webhook(self) -> None:
        """Start bot in webhook mode."""
        logger.info("Starting bot in webhook mode")
        # TODO: Implement webhook setup
        pass

    async def stop(self) -> None:
        """Stop the bot."""
        await self.bot.session.close()
        logger.info("Telegram bot stopped")