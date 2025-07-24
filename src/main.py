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

# No longer need repository imports - all services use UnitOfWork pattern


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
    
    # Initialize database first
    await db_manager.initialize()
    
    # Get session factory for UnitOfWork usage
    session_factory = db_manager.get_session_factory()
    
    # UnitOfWork factory - All services now use UnitOfWork pattern exclusively
    def create_unit_of_work():
        from src.domain.repositories.base import UnitOfWork
        from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
        return SqlAlchemyUnitOfWork(db_manager.get_session_factory())
    
    # Register UnitOfWork factory
    from src.domain.repositories.base import UnitOfWork
    container.register_factory(UnitOfWork, create_unit_of_work)
    
    # Register application services as factories with dependencies
    from src.application.services import (
        UserApplicationService,
        ProductApplicationService,
        OrderApplicationService,
        PaymentApplicationService,
        ReferralApplicationService,
        PromocodeApplicationService,
        TrialApplicationService
    )
    
    def create_user_service() -> UserApplicationService:
        uow = container.resolve(UnitOfWork)
        return UserApplicationService(uow)
    
    def create_product_service() -> ProductApplicationService:
        uow = container.resolve(UnitOfWork)
        return ProductApplicationService(uow)
    
    def create_order_service() -> OrderApplicationService:
        uow = container.resolve(UnitOfWork)
        return OrderApplicationService(uow)
    
    def create_payment_service() -> PaymentApplicationService:
        payment_gateway_factory = container.resolve(PaymentGatewayFactory)
        uow = container.resolve(UnitOfWork)
        return PaymentApplicationService(payment_gateway_factory, uow)
    
    def create_referral_service() -> ReferralApplicationService:
        uow = container.resolve(UnitOfWork)
        return ReferralApplicationService(uow)
    
    def create_promocode_service() -> PromocodeApplicationService:
        uow = container.resolve(UnitOfWork)
        return PromocodeApplicationService(uow)
    
    def create_trial_service() -> TrialApplicationService:
        uow = container.resolve(UnitOfWork)
        return TrialApplicationService(uow)
    
    container.register_factory(UserApplicationService, create_user_service)
    container.register_factory(ProductApplicationService, create_product_service)
    container.register_factory(OrderApplicationService, create_order_service)
    container.register_factory(PaymentApplicationService, create_payment_service)
    container.register_factory(ReferralApplicationService, create_referral_service)
    container.register_factory(PromocodeApplicationService, create_promocode_service)
    container.register_factory(TrialApplicationService, create_trial_service)
    
    # Register payment gateway factory
    from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    def create_payment_gateway_factory() -> PaymentGatewayFactory:
        # Bot will be available in the container when needed
        from aiogram import Bot
        try:
            bot = container.resolve(Bot)
        except:
            bot = None
        return PaymentGatewayFactory(settings, bot)
    container.register_factory(PaymentGatewayFactory, create_payment_gateway_factory)
    
    # Register notification service
    from src.infrastructure.notifications.notification_service import NotificationService
    container.register_singleton(NotificationService, NotificationService)


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
        
        # Run database migrations
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
        
        # Start Telegram bot and register bot instance in container
        telegram_bot = TelegramBot(settings)
        
        # Register the bot instance in the container for payment gateways
        from aiogram import Bot
        container.register_instance(Bot, telegram_bot.bot)
        
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
        await event_bus.stop_processing()
        if logger:
            logger.info("Application stopped")
        else:
            print("Application stopped")


if __name__ == "__main__":
    asyncio.run(main())