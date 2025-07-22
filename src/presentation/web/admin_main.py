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
    
    # Register application services
    from src.application.services import (
        UserApplicationService,
        ProductApplicationService,
        OrderApplicationService,
        PaymentApplicationService,
        ReferralApplicationService,
        PromocodeApplicationService,
        TrialApplicationService
    )
    
    container.register_singleton(UserApplicationService, UserApplicationService)
    container.register_singleton(ProductApplicationService, ProductApplicationService)
    container.register_singleton(OrderApplicationService, OrderApplicationService)
    container.register_singleton(PaymentApplicationService, PaymentApplicationService)
    container.register_singleton(ReferralApplicationService, ReferralApplicationService)
    container.register_singleton(PromocodeApplicationService, PromocodeApplicationService)
    container.register_singleton(TrialApplicationService, TrialApplicationService)
    
    # Initialize database
    await db_manager.initialize()


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