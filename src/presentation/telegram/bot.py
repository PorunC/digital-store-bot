"""Telegram bot implementation."""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.infrastructure.configuration.settings import Settings
from src.shared.dependency_injection import inject

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
        from aiohttp import web, ClientSession
        from aiohttp.web import run_app
        
        # Set webhook
        webhook_url = self.settings.external.webhook_url
        if webhook_url:
            # Remove existing webhook first
            await self.bot.delete_webhook()
            # Set new webhook
            await self.bot.set_webhook(
                url=webhook_url,
                secret_token=self.settings.external.webhook_secret,
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to {webhook_url}")
        
        # Create web application
        app = web.Application()
        
        # Add webhook route
        async def webhook_handler(request):
            data = await request.json()
            # Process update through dispatcher
            await self.dispatcher.feed_webhook_update(self.bot, data)
            return web.Response()
        
        # Add health check route
        async def health_handler(request):
            return web.json_response({"status": "healthy"})
        
        app.router.add_post("/webhook", webhook_handler)
        app.router.add_get("/health", health_handler)
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        
        logger.info("Webhook server started on port 8000")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down webhook server")
            await runner.cleanup()

    async def stop(self) -> None:
        """Stop the bot."""
        await self.bot.session.close()
        logger.info("Telegram bot stopped")