#!/usr/bin/env python3
"""Admin panel main entry point."""

import asyncio
import sys
from pathlib import Path

# Add the current working directory to Python path for module imports
import os
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

import uvicorn
from src.presentation.web.admin_panel import create_admin_app


async def setup_dependencies() -> None:
    """Setup dependency injection container for admin panel."""
    from src.infrastructure.configuration import get_settings
    from src.shared.dependency_injection import container
    
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
        from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
        payment_gateway_factory = PaymentGatewayFactory(settings, bot=None)
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
    
    # Database already initialized above


def main() -> None:
    """Main entry point for admin panel."""
    # Setup dependencies
    asyncio.run(setup_dependencies())
    
    # Create app
    app = create_admin_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        access_log=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()