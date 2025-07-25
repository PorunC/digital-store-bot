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
        try:
            from src.presentation.telegram.middleware.user_context import UserContextMiddleware
            from src.presentation.telegram.middleware.database import DatabaseMiddleware
            from src.presentation.telegram.middleware.localization import LocalizationMiddleware
            from src.presentation.telegram.middleware.throttling import ThrottlingMiddleware
            from src.presentation.telegram.middleware.logging_middleware import LoggingMiddleware
            from src.shared.dependency_injection import container
            from src.infrastructure.database.manager import DatabaseManager
            
            # Get database manager from container
            db_manager = container.resolve(DatabaseManager)
            
            # Setup middleware in order (first added is outermost)
            self.dispatcher.message.middleware(LoggingMiddleware())
            self.dispatcher.callback_query.middleware(LoggingMiddleware())
            
            # Throttling with custom settings
            self.dispatcher.message.middleware(ThrottlingMiddleware(
                default_rate=self.settings.security.max_requests_per_minute / 60.0,
                default_burst=3,
                admin_exempt=True
            ))
            self.dispatcher.callback_query.middleware(ThrottlingMiddleware(
                default_rate=self.settings.security.max_requests_per_minute / 60.0,
                default_burst=5,
                admin_exempt=True
            ))
            
            # Database middleware with manager
            self.dispatcher.message.middleware(DatabaseMiddleware(db_manager))
            self.dispatcher.callback_query.middleware(DatabaseMiddleware(db_manager))
            
            # Localization middleware with settings
            self.dispatcher.message.middleware(LocalizationMiddleware(
                locales_path=self.settings.i18n.locales_dir,
                default_locale=self.settings.i18n.default_locale
            ))
            self.dispatcher.callback_query.middleware(LocalizationMiddleware(
                locales_path=self.settings.i18n.locales_dir,
                default_locale=self.settings.i18n.default_locale
            ))
            
            # User context middleware
            self.dispatcher.message.middleware(UserContextMiddleware())
            self.dispatcher.callback_query.middleware(UserContextMiddleware())
            
        except Exception as e:
            logger.warning(f"Some middleware could not be loaded: {e}")
            # Setup minimal middleware for basic functionality
            try:
                from src.presentation.telegram.middleware.user_context import UserContextMiddleware
                self.dispatcher.message.middleware(UserContextMiddleware())
                self.dispatcher.callback_query.middleware(UserContextMiddleware())
            except Exception as fallback_error:
                logger.error(f"Critical middleware missing - bot may not function properly: {fallback_error}")

    async def _setup_handlers(self) -> None:
        """Setup message handlers."""
        from src.presentation.telegram.handlers.start import start_router
        from src.presentation.telegram.handlers.catalog import catalog_router
        from src.presentation.telegram.handlers.payment import payment_router
        from src.presentation.telegram.handlers.profile import profile_router
        from src.presentation.telegram.handlers.admin import admin_router
        from src.presentation.telegram.handlers.support import support_router
        
        # Register routers
        self.dispatcher.include_router(start_router)
        self.dispatcher.include_router(catalog_router)
        self.dispatcher.include_router(payment_router)
        self.dispatcher.include_router(profile_router)
        self.dispatcher.include_router(admin_router)
        self.dispatcher.include_router(support_router)

    async def _start_polling(self) -> None:
        """Start bot in polling mode."""
        logger.info("Starting bot in polling mode")
        await self.dispatcher.start_polling(self.bot)

    async def _start_webhook(self) -> None:
        """Start bot in webhook mode."""
        logger.info("Starting bot in webhook mode")
        from aiohttp import web, ClientSession
        from aiohttp.web import run_app
        
        # Build webhook URL from domain and bot token if not explicitly set
        webhook_url = self.settings.external.webhook_url
        if not webhook_url and self.settings.bot.domain:
            # Extract bot token (before the colon)
            bot_token = self.settings.bot.token.split(':')[0] if ':' in self.settings.bot.token else self.settings.bot.token
            webhook_url = f"https://{self.settings.bot.domain}/webhook/bot{bot_token}"
        
        webhook_path = None
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
            
            # Extract path from webhook URL for routing
            from urllib.parse import urlparse
            parsed_url = urlparse(webhook_url)
            webhook_path = parsed_url.path
        
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
        
        # Add webhook route with correct path
        if webhook_path:
            app.router.add_post(webhook_path, webhook_handler)
        else:
            # Fallback to default webhook route
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