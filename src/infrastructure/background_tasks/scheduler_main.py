#!/usr/bin/env python3
"""Task scheduler main entry point."""

import asyncio
import logging
import signal
from datetime import timedelta

from .task_scheduler import TaskScheduler


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
    
    # Setup dependencies (same as main.py)
    from src.domain.repositories import (
        UserRepository, ProductRepository, OrderRepository,
        ReferralRepository, InviteRepository, PromocodeRepository
    )
    from src.infrastructure.database.repositories import (
        SqlAlchemyUserRepository, SqlAlchemyProductRepository, SqlAlchemyOrderRepository,
        SqlAlchemyReferralRepository, SqlAlchemyInviteRepository, SqlAlchemyPromocodeRepository
    )
    from src.infrastructure.database import DatabaseManager
    
    # Register configuration
    container.register_instance(type(settings), settings)
    
    # Register database manager
    db_manager = DatabaseManager(settings.database)
    container.register_instance(DatabaseManager, db_manager)
    
    # Register repository factories
    def create_user_repository() -> UserRepository:
        return SqlAlchemyUserRepository(db_manager.get_session())
    
    def create_product_repository() -> ProductRepository:
        return SqlAlchemyProductRepository(db_manager.get_session())
    
    def create_order_repository() -> OrderRepository:
        return SqlAlchemyOrderRepository(db_manager.get_session())
    
    def create_referral_repository() -> ReferralRepository:
        return SqlAlchemyReferralRepository(db_manager.get_session())
        
    def create_invite_repository() -> InviteRepository:
        return SqlAlchemyInviteRepository(db_manager.get_session())
        
    def create_promocode_repository() -> PromocodeRepository:
        return SqlAlchemyPromocodeRepository(db_manager.get_session())
    
    def create_unit_of_work():
        from src.domain.repositories.base import UnitOfWork
        from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
        return SqlAlchemyUnitOfWork(db_manager.get_session())
    
    container.register_factory(UserRepository, create_user_repository)
    container.register_factory(ProductRepository, create_product_repository)
    container.register_factory(OrderRepository, create_order_repository)
    container.register_factory(ReferralRepository, create_referral_repository)
    container.register_factory(InviteRepository, create_invite_repository)
    container.register_factory(PromocodeRepository, create_promocode_repository)
    
    # Register UnitOfWork factory
    from src.domain.repositories.base import UnitOfWork
    container.register_factory(UnitOfWork, create_unit_of_work)
    
    # Register payment gateway factory without bot (for background tasks)
    from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    def create_payment_gateway_factory() -> PaymentGatewayFactory:
        return PaymentGatewayFactory(settings, bot=None)
    container.register_factory(PaymentGatewayFactory, create_payment_gateway_factory)
    
    # Register application services
    from src.application.services import (
        OrderApplicationService,
        PaymentApplicationService, 
        UserApplicationService
    )
    
    container.register_singleton(OrderApplicationService, OrderApplicationService)
    container.register_singleton(PaymentApplicationService, PaymentApplicationService)
    container.register_singleton(UserApplicationService, UserApplicationService)
    
    # Register notification service
    from src.infrastructure.notifications.notification_service import NotificationService
    container.register_singleton(NotificationService, NotificationService)
    
    # Initialize database
    await db_manager.initialize()
    
    # Create and configure scheduler
    scheduler = TaskScheduler()
    
    # Add payment cleanup task
    from .payment_tasks import PaymentTasks
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