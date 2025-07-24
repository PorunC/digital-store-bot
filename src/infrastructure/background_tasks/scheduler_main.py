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
    from src.core.containers import setup_scheduler_container
    
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
    
    # Register database manager
    db_manager = DatabaseManager(settings.database)
    
    # Initialize database first
    await db_manager.initialize()
    
    # Configure container with settings after database is initialized
    container = setup_scheduler_container(settings, db_manager)
    
    # Wire the container for dependency injection
    container.wire(modules=[
        "src.infrastructure.background_tasks.payment_tasks"
    ])
    
    # UnitOfWork factory - All services now use UnitOfWork pattern exclusively
    def create_unit_of_work():
        from src.domain.repositories.base import UnitOfWork
        from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
        return SqlAlchemyUnitOfWork(db_manager.get_session_factory())
    
    # Register UnitOfWork factory
    from src.domain.repositories.base import UnitOfWork
    # Removed: container registration now in container definition
    
    # Register payment gateway factory without bot (for background tasks)
    from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    def create_payment_gateway_factory() -> PaymentGatewayFactory:
        return PaymentGatewayFactory(settings, bot=None)
    # Removed: container registration now in container definition
    
    # Register application services as factories with dependencies
    from src.application.services import (
        OrderApplicationService,
        PaymentApplicationService, 
        UserApplicationService
    )
    
    def create_user_service() -> UserApplicationService:
        uow = container.UnitOfWork()
        return UserApplicationService(uow)
    
    def create_order_service() -> OrderApplicationService:
        uow = container.UnitOfWork()
        return OrderApplicationService(uow)
    
    def create_payment_service() -> PaymentApplicationService:
        payment_gateway_factory = container.payment_gateway_factory()
        uow = container.UnitOfWork()
        return PaymentApplicationService(payment_gateway_factory, uow)
    
    # Removed: container registration now in container definition
    # Removed: container registration now in container definition
    # Removed: container registration now in container definition
    
    # Register notification service
    from src.infrastructure.notifications.notification_service import NotificationService
    # Removed: container registration now in container definition
    
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