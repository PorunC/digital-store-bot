"""Dependency injection containers using dependency-injector."""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide

# Use lazy imports to avoid circular import issues


def _create_database_manager(settings):
    """Factory for DatabaseManager."""
    from ..infrastructure.database.manager import DatabaseManager
    db_manager = DatabaseManager(settings.database)
    # Note: Database will be initialized by the application before container setup
    return db_manager

def _create_unit_of_work(db_manager):
    """Factory for UnitOfWork."""
    from ..infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
    return SqlAlchemyUnitOfWork(db_manager.get_session_factory())

def _create_event_bus():
    """Factory for EventBus."""
    from ..shared.events.bus import EventBus
    return EventBus()

def _create_telegram_notifier(bot_token, admin_ids):
    """Factory for TelegramNotifier."""
    from ..infrastructure.notifications.telegram_notifier import TelegramNotifier
    return TelegramNotifier(bot_token, admin_ids)

def _create_notification_service(bot_token, admin_ids):
    """Factory for NotificationService."""
    from ..infrastructure.notifications.notification_service import NotificationService, NotificationChannel
    from ..infrastructure.notifications.telegram_notifier import TelegramNotifier
    
    # Create a notification service with properly initialized notifiers
    service = NotificationService()
    service.notifiers[NotificationChannel.TELEGRAM] = TelegramNotifier(bot_token, admin_ids)
    return service

def _create_payment_gateway_factory(settings):
    """Factory for PaymentGatewayFactory."""
    from ..infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    return PaymentGatewayFactory(settings)

def _create_analytics_service(settings):
    """Factory for AnalyticsService."""
    from ..infrastructure.external.analytics.analytics_service import AnalyticsService
    return AnalyticsService(settings)

def _create_user_repository_factory(database_session_factory):
    """Factory for user repository factory."""
    from ..infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
    
    def create_user_repository(session):
        return SqlAlchemyUserRepository(session)
    
    return create_user_repository

def _create_order_repository_factory(database_session_factory):
    """Factory for order repository factory."""
    from ..infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
    
    def create_order_repository(session):
        return SqlAlchemyOrderRepository(session)
    
    return create_order_repository

def _create_product_repository_factory(database_session_factory):
    """Factory for product repository factory."""
    from ..infrastructure.database.repositories.product_repository import SqlAlchemyProductRepository
    
    def create_product_repository(session):
        return SqlAlchemyProductRepository(session)
    
    return create_product_repository

def _create_promocode_repository_factory(database_session_factory):
    """Factory for promocode repository factory."""
    from ..infrastructure.database.repositories.promocode_repository import SqlAlchemyPromocodeRepository
    
    def create_promocode_repository(session):
        return SqlAlchemyPromocodeRepository(session)
    
    return create_promocode_repository

def _create_referral_repository_factory(database_session_factory):
    """Factory for referral repository factory."""
    from ..infrastructure.database.repositories.referral_repository import SqlAlchemyReferralRepository
    
    def create_referral_repository(session):
        return SqlAlchemyReferralRepository(session)
    
    return create_referral_repository

def _create_user_service(unit_of_work, user_repository_factory):
    """Factory for UserApplicationService."""
    from ..application.services.user_service import UserApplicationService
    return UserApplicationService(unit_of_work, user_repository_factory)

def _create_product_service(unit_of_work, product_repository_factory):
    """Factory for ProductApplicationService."""
    from ..application.services.product_service import ProductApplicationService
    return ProductApplicationService(unit_of_work, product_repository_factory)

def _create_order_service(unit_of_work, order_repository_factory, product_repository_factory, user_repository_factory):
    """Factory for OrderApplicationService."""
    from ..application.services.order_service import OrderApplicationService
    return OrderApplicationService(unit_of_work, order_repository_factory, product_repository_factory, user_repository_factory)

def _create_payment_service(gateway_factory, unit_of_work, order_repository_factory):
    """Factory for PaymentApplicationService."""
    from ..application.services.payment_service import PaymentApplicationService
    return PaymentApplicationService(gateway_factory, unit_of_work, order_repository_factory)

def _create_referral_service(unit_of_work, referral_repository_factory, user_repository_factory):
    """Factory for ReferralApplicationService."""
    from ..application.services.referral_service import ReferralApplicationService
    return ReferralApplicationService(unit_of_work, referral_repository_factory, user_repository_factory)

def _create_promocode_service(unit_of_work, promocode_repository_factory, user_repository_factory):
    """Factory for PromocodeApplicationService."""
    from ..application.services.promocode_service import PromocodeApplicationService
    return PromocodeApplicationService(unit_of_work, promocode_repository_factory, user_repository_factory)

def _create_trial_service(unit_of_work, user_repository_factory):
    """Factory for TrialApplicationService."""
    from ..application.services.trial_service import TrialApplicationService
    return TrialApplicationService(unit_of_work, user_repository_factory)

def _create_product_loader_service(unit_of_work, settings):
    """Factory for ProductLoaderService."""
    from ..application.services.product_loader_service import ProductLoaderService
    return ProductLoaderService(unit_of_work, settings)

# Repository factory functions - repositories need to be created per session
# These will be injected directly into services rather than as singletons


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application container for dependency injection."""
    
    # Configuration
    config = providers.Configuration()
    
    # Settings (will be injected)
    settings = providers.Object(None)
    
    # Database
    database_manager = providers.Singleton(
        providers.Callable(
            _create_database_manager,
            settings=settings
        )
    )
    
    database_session_factory = providers.Resource(
        providers.Callable(
            lambda db_manager: db_manager.get_session_factory(),
            db_manager=database_manager
        )
    )
    
    # Unit of Work
    unit_of_work = providers.Factory(
        providers.Callable(
            _create_unit_of_work,
            db_manager=database_manager
        )
    )
    
    # Event Bus
    event_bus = providers.Singleton(
        providers.Callable(_create_event_bus)
    )
    
    # Notification services
    telegram_notifier = providers.Singleton(
        providers.Callable(
            _create_telegram_notifier,
            bot_token=config.bot.token,
            admin_ids=config.bot.admins
        )
    )
    
    notification_service = providers.Singleton(
        providers.Callable(
            _create_notification_service,
            bot_token=config.bot.token,
            admin_ids=config.bot.admins
        )
    )
    
    # Payment gateway
    payment_gateway_factory = providers.Singleton(
        providers.Callable(
            _create_payment_gateway_factory,
            settings=settings
        )
    )
    
    # Analytics
    analytics_service = providers.Singleton(
        providers.Callable(
            _create_analytics_service,
            settings=settings
        )
    )
    
    # Repository Factories
    user_repository_factory = providers.Singleton(
        providers.Callable(
            _create_user_repository_factory,
            database_session_factory=database_session_factory
        )
    )
    
    order_repository_factory = providers.Singleton(
        providers.Callable(
            _create_order_repository_factory,
            database_session_factory=database_session_factory
        )
    )
    
    product_repository_factory = providers.Singleton(
        providers.Callable(
            _create_product_repository_factory,
            database_session_factory=database_session_factory
        )
    )
    
    promocode_repository_factory = providers.Singleton(
        providers.Callable(
            _create_promocode_repository_factory,
            database_session_factory=database_session_factory
        )
    )
    
    referral_repository_factory = providers.Singleton(
        providers.Callable(
            _create_referral_repository_factory,
            database_session_factory=database_session_factory
        )
    )
    
    # Application Services
    user_service = providers.Factory(
        providers.Callable(
            _create_user_service,
            unit_of_work=unit_of_work,
            user_repository_factory=user_repository_factory
        )
    )
    
    product_service = providers.Factory(
        providers.Callable(
            _create_product_service,
            unit_of_work=unit_of_work,
            product_repository_factory=product_repository_factory
        )
    )
    
    order_service = providers.Factory(
        providers.Callable(
            _create_order_service,
            unit_of_work=unit_of_work,
            order_repository_factory=order_repository_factory,
            product_repository_factory=product_repository_factory,
            user_repository_factory=user_repository_factory
        )
    )
    
    payment_service = providers.Factory(
        providers.Callable(
            _create_payment_service,
            gateway_factory=payment_gateway_factory,
            unit_of_work=unit_of_work,
            order_repository_factory=order_repository_factory
        )
    )
    
    referral_service = providers.Factory(
        providers.Callable(
            _create_referral_service,
            unit_of_work=unit_of_work,
            referral_repository_factory=referral_repository_factory,
            user_repository_factory=user_repository_factory
        )
    )
    
    promocode_service = providers.Factory(
        providers.Callable(
            _create_promocode_service,
            unit_of_work=unit_of_work,
            promocode_repository_factory=promocode_repository_factory,
            user_repository_factory=user_repository_factory
        )
    )
    
    trial_service = providers.Factory(
        providers.Callable(
            _create_trial_service,
            unit_of_work=unit_of_work,
            user_repository_factory=user_repository_factory
        )
    )
    
    product_loader_service = providers.Factory(
        providers.Callable(
            _create_product_loader_service,
            unit_of_work=unit_of_work,
            settings=settings
        )
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


def setup_container(settings) -> ApplicationContainer:
    """Setup and configure the main container."""
    container.config.from_dict(settings.model_dump())
    container.settings.override(settings)
    return container


def setup_scheduler_container(settings, db_manager) -> ApplicationContainer:
    """Setup and configure container for scheduler with pre-initialized database."""
    container.config.from_dict(settings.model_dump())
    container.settings.override(settings)
    # Override the database manager with the already initialized one
    container.database_manager.override(db_manager)
    return container


def wire_container(modules: list[str]) -> None:
    """Wire the container to specified modules."""
    container.wire(modules=modules)


def unwire_container() -> None:
    """Unwire the container."""
    container.unwire()