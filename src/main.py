"""Main application entry point."""

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from src.infrastructure.configuration import get_settings
from src.infrastructure.database import DatabaseManager
from src.presentation.telegram import TelegramBot
from src.shared.dependency_injection import container
from src.shared.events import event_bus


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


async def setup_dependencies() -> None:
    """Setup dependency injection container."""
    settings = get_settings()
    
    # Register configuration
    container.register_instance(type(settings), settings)
    
    # Register database manager
    db_manager = DatabaseManager(settings.database)
    container.register_instance(DatabaseManager, db_manager)
    
    # TODO: Register repositories, services, etc.


async def main() -> None:
    """Main application entry point."""
    logger = None
    try:
        # Load settings
        settings = get_settings()
        
        # Setup logging
        await setup_logging(settings)
        logger = logging.getLogger(__name__)
        logger.info("Starting Digital Store Bot v2")
        
        # Setup dependencies
        await setup_dependencies()
        
        # Start event bus
        await event_bus.start_processing()
        
        # Initialize database
        db_manager = container.resolve(DatabaseManager)
        await db_manager.initialize()
        
        # Start Telegram bot
        bot = TelegramBot(settings)
        await bot.start()
        
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
        await event_bus.stop_processing()
        if logger:
            logger.info("Application stopped")
        else:
            print("Application stopped")


if __name__ == "__main__":
    asyncio.run(main())