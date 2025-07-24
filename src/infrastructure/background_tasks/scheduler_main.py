#!/usr/bin/env python3
"""Task scheduler main entry point."""

import asyncio
import logging
import signal
import sys
from datetime import timedelta
from pathlib import Path

# Add the current working directory to Python path for module imports
import os
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from src.infrastructure.background_tasks.task_scheduler import TaskScheduler


async def main() -> None:
    """Main entry point for task scheduler."""
    import sys
    from src.infrastructure.configuration import get_settings
    from src.shared.dependency_injection import container
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Task Scheduler Service")
    
    # Load configuration
    settings = get_settings()
    
    # Setup dependencies using UnitOfWork pattern only
    from src.infrastructure.database import DatabaseManager
    
    # Register configuration
    container.register_instance(type(settings), settings)
    
    # Register database manager
    db_manager = DatabaseManager(settings.database)
    container.register_instance(DatabaseManager, db_manager)
    
    # Initialize database first
    await db_manager.initialize()
    
    # UnitOfWork factory - All services now use UnitOfWork pattern exclusively
    def create_unit_of_work():
        from src.domain.repositories.base import UnitOfWork
        from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
        return SqlAlchemyUnitOfWork(db_manager.get_session_factory())
    
    # Register UnitOfWork factory
    from src.domain.repositories.base import UnitOfWork
    container.register_factory(UnitOfWork, create_unit_of_work)
    
    # Register payment gateway factory without bot (for background tasks)
    from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    def create_payment_gateway_factory() -> PaymentGatewayFactory:
        return PaymentGatewayFactory(settings, bot=None)
    container.register_factory(PaymentGatewayFactory, create_payment_gateway_factory)
    
    # Register application services as factories with dependencies
    from src.application.services import (
        OrderApplicationService,
        PaymentApplicationService, 
        UserApplicationService
    )
    
    def create_user_service() -> UserApplicationService:
        uow = container.resolve(UnitOfWork)
        return UserApplicationService(uow)
    
    def create_order_service() -> OrderApplicationService:
        uow = container.resolve(UnitOfWork)
        return OrderApplicationService(uow)
    
    def create_payment_service() -> PaymentApplicationService:
        payment_gateway_factory = container.resolve(PaymentGatewayFactory)
        uow = container.resolve(UnitOfWork)
        return PaymentApplicationService(payment_gateway_factory, uow)
    
    container.register_factory(UserApplicationService, create_user_service)
    container.register_factory(OrderApplicationService, create_order_service)
    container.register_factory(PaymentApplicationService, create_payment_service)
    
    # Register notification service
    from src.infrastructure.notifications.notification_service import NotificationService
    container.register_singleton(NotificationService, NotificationService)
    
    # Database already initialized above
    
    # Create and configure scheduler
    scheduler = TaskScheduler()
    
    # Add payment cleanup task
    from src.infrastructure.background_tasks.payment_tasks import PaymentTasks
    payment_tasks = PaymentTasks()
    
    scheduler.add_task(
        name="payment_cleanup", 
        func=payment_tasks.process_expired_orders,
        interval=timedelta(minutes=15)
    )
    
    # Graceful shutdown handler
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping scheduler...")
        asyncio.create_task(scheduler.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start scheduler
        await scheduler.start()
        logger.info("Task scheduler started successfully")
        
        # Keep running
        while scheduler.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
    finally:
        await scheduler.stop()
        logger.info("Task scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())