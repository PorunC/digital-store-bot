"""Main application entry point with dependency-injector."""

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from src.infrastructure.configuration.settings import get_settings
from src.infrastructure.database.manager import DatabaseManager
from src.presentation.telegram.bot import TelegramBot
from src.core.containers import ApplicationContainer
from src.shared.events.bus import EventBus


async def setup_logging(settings) -> None:
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        format=settings.logging.format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    if settings.logging.file_enabled:
        try:
            log_path = Path(settings.logging.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=settings.logging.file_max_bytes,
                backupCount=settings.logging.file_backup_count
            )
            file_handler.setFormatter(logging.Formatter(settings.logging.format))
            logging.getLogger().addHandler(file_handler)
        except (PermissionError, OSError) as e:
            # If we can't write to the log file, continue with console logging only
            print(f"Warning: Could not setup file logging: {e}. Using console logging only.")
            pass


async def setup_container(settings) -> ApplicationContainer:
    """Setup dependency injection container."""
    container = ApplicationContainer()
    
    # Configure the container with settings
    container.config.from_dict(settings.model_dump())
    container.settings.override(settings)
    
    # Initialize database
    db_manager = container.database_manager()
    await db_manager.initialize()
    
    return container


async def initialize_products(container: ApplicationContainer) -> None:
    """Initialize products from JSON configuration."""
    logger = logging.getLogger(__name__)
    try:
        # Get product loader service from container
        loader_service = container.product_loader_service()
        
        # Load products
        loaded_count = await loader_service.load_products_from_json()
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} products from JSON")
        else:
            logger.info("No products loaded (may already exist or file not found)")
            
    except Exception as e:
        logger.error(f"Failed to initialize products: {e}")
        # Don't exit, let the app continue even if products fail to load


async def run_migrations(container: ApplicationContainer) -> None:
    """Run database migrations."""
    logger = logging.getLogger(__name__)
    
    settings = container.settings()
    
    from src.infrastructure.database.migrations.migration_manager import MigrationManager
    migration_manager = MigrationManager(
        database_url=settings.database.get_url(),
        migrations_path="src/infrastructure/database/migrations"
    )
    await migration_manager.initialize()
    
    # Apply pending migrations
    migration_result = await migration_manager.apply_migrations()
    if migration_result["errors"] > 0:
        logger.error(f"Migration failed: {migration_result}")
        sys.exit(1)
    
    logger.info(f"Migration completed: {migration_result['applied']} migrations applied")


async def main() -> None:
    """Main application entry point."""
    logger = None
    container = None
    
    try:
        # Load settings
        settings = get_settings()
        
        # Setup logging
        await setup_logging(settings)
        logger = logging.getLogger(__name__)
        logger.info("Starting Digital Store Bot v2 with dependency-injector")
        
        # Setup container
        container = await setup_container(settings)
        
        # Start event bus
        event_bus = container.event_bus()
        await event_bus.start_processing()
        
        # Run database migrations
        await run_migrations(container)
        
        # Initialize products from JSON
        await initialize_products(container)
        
        # Wire container to modules for @inject decorators
        container.wire(modules=[
            "src.presentation.telegram.handlers.start",
            "src.presentation.telegram.handlers.catalog", 
            "src.presentation.telegram.handlers.profile",
            "src.presentation.telegram.handlers.payment",
            "src.presentation.telegram.handlers.admin",
            "src.presentation.telegram.handlers.support",
        ])
        
        # Start Telegram bot
        telegram_bot = TelegramBot(settings)
        await telegram_bot.start()
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Received interrupt signal")
        else:
            print("Received interrupt signal")
    except Exception as e:
        if logger:
            logger.error(f"Application failed to start: {e}", exc_info=True)
        else:
            print(f"Application failed to start: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if container:
            # Stop event bus
            event_bus = container.event_bus()
            await event_bus.stop_processing()
            
            # Unwire container
            container.unwire()
            
        if logger:
            logger.info("Application stopped")
        else:
            print("Application stopped")


if __name__ == "__main__":
    asyncio.run(main())