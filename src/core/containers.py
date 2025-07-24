"""Dependency injection containers using dependency-injector."""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide

from ..infrastructure.configuration.settings import Settings
from ..infrastructure.database.manager import DatabaseManager
from ..infrastructure.database.unit_of_work import UnitOfWork

# Repository providers
from ..infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from ..infrastructure.database.repositories.product_repository import SqlAlchemyProductRepository
from ..infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
from ..infrastructure.database.repositories.referral_repository import SqlAlchemyReferralRepository
from ..infrastructure.database.repositories.promocode_repository import SqlAlchemyPromocodeRepository
from ..infrastructure.database.repositories.invite_repository import SqlAlchemyInviteRepository

# Application services
from ..application.services.user_service import UserApplicationService
from ..application.services.product_service import ProductApplicationService
from ..application.services.order_service import OrderApplicationService
from ..application.services.payment_service import PaymentApplicationService
from ..application.services.referral_service import ReferralApplicationService
from ..application.services.promocode_service import PromocodeApplicationService
from ..application.services.trial_service import TrialApplicationService
from ..application.services.product_loader_service import ProductLoaderService

# Infrastructure services
from ..infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
from ..infrastructure.notifications.notification_service import NotificationService
from ..infrastructure.notifications.telegram_notifier import TelegramNotifier
from ..infrastructure.external.analytics.analytics_service import AnalyticsService

# Event system
from ..shared.events.bus import EventBus


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application container for dependency injection."""
    
    # Configuration
    config = providers.Configuration()
    
    # Settings
    settings = providers.Singleton(
        Settings
    )
    
    # Database
    database_manager = providers.Singleton(
        DatabaseManager,
        settings=settings
    )
    
    database_session_factory = providers.Resource(
        providers.Callable(
            lambda db_manager: db_manager.create_session_factory(),
            db_manager=database_manager
        )
    )
    
    # Unit of Work
    unit_of_work = providers.Factory(
        UnitOfWork,
        session_factory=database_session_factory
    )
    
    # Event Bus
    event_bus = providers.Singleton(EventBus)
    
    # Repositories
    user_repository = providers.Factory(
        SqlAlchemyUserRepository,
        session_factory=database_session_factory
    )
    
    product_repository = providers.Factory(
        SqlAlchemyProductRepository,
        session_factory=database_session_factory
    )
    
    order_repository = providers.Factory(
        SqlAlchemyOrderRepository,
        session_factory=database_session_factory
    )
    
    referral_repository = providers.Factory(
        SqlAlchemyReferralRepository,
        session_factory=database_session_factory
    )
    
    promocode_repository = providers.Factory(
        SqlAlchemyPromocodeRepository,
        session_factory=database_session_factory
    )
    
    invite_repository = providers.Factory(
        SqlAlchemyInviteRepository,
        session_factory=database_session_factory
    )
    
    # Notification services
    telegram_notifier = providers.Singleton(
        TelegramNotifier,
        bot_token=config.bot.token,
        admin_ids=config.bot.admins
    )
    
    notification_service = providers.Singleton(
        NotificationService,
        telegram_notifier=telegram_notifier
    )
    
    # Payment gateway
    payment_gateway_factory = providers.Singleton(
        PaymentGatewayFactory,
        settings=settings
    )
    
    # Analytics
    analytics_service = providers.Singleton(
        AnalyticsService,
        settings=settings
    )
    
    # Application Services
    user_service = providers.Factory(
        UserApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    product_service = providers.Factory(
        ProductApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    order_service = providers.Factory(
        OrderApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    payment_service = providers.Factory(
        PaymentApplicationService,
        unit_of_work=unit_of_work,
        gateway_factory=payment_gateway_factory,
        event_bus=event_bus
    )
    
    referral_service = providers.Factory(
        ReferralApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    promocode_service = providers.Factory(
        PromocodeApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    trial_service = providers.Factory(
        TrialApplicationService,
        unit_of_work=unit_of_work,
        event_bus=event_bus
    )
    
    product_loader_service = providers.Factory(
        ProductLoaderService,
        unit_of_work=unit_of_work,
        settings=settings
    )


class TelegramContainer(containers.DeclarativeContainer):
    """Container for Telegram-specific dependencies."""
    
    # Parent container
    app = providers.DependenciesContainer()
    
    # Telegram Bot instance will be injected at runtime
    bot = providers.Object(None)


class WebContainer(containers.DeclarativeContainer):
    """Container for Web/Admin panel dependencies."""
    
    # Parent container
    app = providers.DependenciesContainer()


class BackgroundTasksContainer(containers.DeclarativeContainer):
    """Container for background tasks dependencies."""
    
    # Parent container
    app = providers.DependenciesContainer()
    
    # Task scheduler will be injected at runtime
    scheduler = providers.Object(None)


# Global container instance
container = ApplicationContainer()


def setup_container(settings: Settings) -> ApplicationContainer:
    """Setup and configure the main container."""
    container.config.from_pydantic(settings)
    return container


def wire_container(modules: list[str]) -> None:
    """Wire the container to specified modules."""
    container.wire(modules=modules)


def unwire_container() -> None:
    """Unwire the container."""
    container.unwire()