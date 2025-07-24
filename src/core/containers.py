"""Dependency injection containers using dependency-injector."""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide

# Use lazy imports to avoid circular import issues


def _create_database_manager(settings):
    """Factory for DatabaseManager."""
    from ..infrastructure.database.manager import DatabaseManager
    return DatabaseManager(settings.database)

def _create_unit_of_work(db_manager):
    """Factory for UnitOfWork."""
    from ..infrastructure.database.unit_of_work import UnitOfWork
    return UnitOfWork(db_manager.get_session_factory())

def _create_event_bus():
    """Factory for EventBus."""
    from ..shared.events.bus import EventBus
    return EventBus()

def _create_telegram_notifier(bot_token, admin_ids):
    """Factory for TelegramNotifier."""
    from ..infrastructure.notifications.telegram_notifier import TelegramNotifier
    return TelegramNotifier(bot_token, admin_ids)

def _create_notification_service(telegram_notifier):
    """Factory for NotificationService."""
    from ..infrastructure.notifications.notification_service import NotificationService
    return NotificationService(telegram_notifier)

def _create_payment_gateway_factory(settings):
    """Factory for PaymentGatewayFactory."""
    from ..infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    return PaymentGatewayFactory(settings)

def _create_analytics_service(settings):
    """Factory for AnalyticsService."""
    from ..infrastructure.external.analytics.analytics_service import AnalyticsService
    return AnalyticsService(settings)

def _create_user_service(unit_of_work, event_bus):
    """Factory for UserApplicationService."""
    from ..application.services.user_service import UserApplicationService
    return UserApplicationService(unit_of_work, event_bus)

def _create_product_service(unit_of_work, event_bus):
    """Factory for ProductApplicationService."""
    from ..application.services.product_service import ProductApplicationService
    return ProductApplicationService(unit_of_work, event_bus)

def _create_order_service(unit_of_work, event_bus):
    """Factory for OrderApplicationService."""
    from ..application.services.order_service import OrderApplicationService
    return OrderApplicationService(unit_of_work, event_bus)

def _create_payment_service(unit_of_work, gateway_factory, event_bus):
    """Factory for PaymentApplicationService."""
    from ..application.services.payment_service import PaymentApplicationService
    return PaymentApplicationService(unit_of_work, gateway_factory, event_bus)

def _create_referral_service(unit_of_work, event_bus):
    """Factory for ReferralApplicationService."""
    from ..application.services.referral_service import ReferralApplicationService
    return ReferralApplicationService(unit_of_work, event_bus)

def _create_promocode_service(unit_of_work, event_bus):
    """Factory for PromocodeApplicationService."""
    from ..application.services.promocode_service import PromocodeApplicationService
    return PromocodeApplicationService(unit_of_work, event_bus)

def _create_trial_service(unit_of_work, event_bus):
    """Factory for TrialApplicationService."""
    from ..application.services.trial_service import TrialApplicationService
    return TrialApplicationService(unit_of_work, event_bus)

def _create_product_loader_service(unit_of_work, settings):
    """Factory for ProductLoaderService."""
    from ..application.services.product_loader_service import ProductLoaderService
    return ProductLoaderService(unit_of_work, settings)


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
            lambda db_manager: db_manager.create_session_factory(),
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
            telegram_notifier=telegram_notifier
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
    
    # Application Services
    user_service = providers.Factory(
        providers.Callable(
            _create_user_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
        )
    )
    
    product_service = providers.Factory(
        providers.Callable(
            _create_product_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
        )
    )
    
    order_service = providers.Factory(
        providers.Callable(
            _create_order_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
        )
    )
    
    payment_service = providers.Factory(
        providers.Callable(
            _create_payment_service,
            unit_of_work=unit_of_work,
            gateway_factory=payment_gateway_factory,
            event_bus=event_bus
        )
    )
    
    referral_service = providers.Factory(
        providers.Callable(
            _create_referral_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
        )
    )
    
    promocode_service = providers.Factory(
        providers.Callable(
            _create_promocode_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
        )
    )
    
    trial_service = providers.Factory(
        providers.Callable(
            _create_trial_service,
            unit_of_work=unit_of_work,
            event_bus=event_bus
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
    return container


def wire_container(modules: list[str]) -> None:
    """Wire the container to specified modules."""
    container.wire(modules=modules)


def unwire_container() -> None:
    """Unwire the container."""
    container.unwire()