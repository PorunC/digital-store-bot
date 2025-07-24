# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Full automated setup (recommended)
./scripts/setup.sh

# Manual setup
poetry install
cp config/settings.example.yml config/settings.yml
poetry run pre-commit install

# Run application
poetry run python -m src.main                # Production mode
poetry run python -m src.main --dev          # Development with auto-reload
```

### Testing
```bash
# Run all tests with coverage
poetry run pytest

# Run specific test types
poetry run pytest -m unit                    # Unit tests only
poetry run pytest -m integration             # Integration tests only
poetry run pytest -m "not slow"              # Skip slow tests

# Run single test file
poetry run pytest tests/unit/domain/test_user.py

# Run tests matching pattern
poetry run pytest -k "test_subscription"
```

### Code Quality
```bash
# Format and lint (run all in sequence)
poetry run black src tests
poetry run isort src tests
poetry run flake8 src tests
poetry run mypy src

# Run all quality checks at once
poetry run pre-commit run --all-files
```

### Database Operations
```bash
# Create new migration
poetry run python -m src.infrastructure.database.migrations.migration_manager create "migration_description"

# Apply migrations
poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade

# Rollback migration
poetry run python -m src.infrastructure.database.migrations.migration_manager downgrade
```

### Docker Operations
```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f bot
docker compose logs -f admin

# Production deployment with monitoring
docker compose --profile monitoring up -d

# Stop and cleanup
docker compose down
docker compose build --no-cache  # Rebuild containers
```

## Project Architecture

This project implements **Domain-Driven Design (DDD)** with **Clean Architecture** principles, a complete rewrite addressing coupling issues from the original 3xui-shop implementation.

### Core Architectural Patterns

- **Domain-Driven Design**: Rich domain entities with business logic encapsulation
- **Dependency Injection**: Custom DI container with `@inject` decorator for automatic resolution
- **Event-Driven Architecture**: Domain events with async event bus for loose coupling
- **CQRS Pattern**: Separate command and query handlers for clear responsibility separation
- **Repository Pattern**: Abstract data access with Unit of Work pattern
- **Hexagonal Architecture**: Ports and adapters with strict dependency inversion

### Layer Structure

```
src/
├── domain/                    # Core business logic (no external dependencies)
│   ├── entities/             # Rich domain objects (User, Order, Product)
│   ├── value_objects/        # Immutable values (Money, UserProfile)
│   ├── repositories/         # Abstract data access interfaces
│   ├── services/             # Complex business rules coordination
│   └── events/               # Domain events for state changes
├── application/              # Application orchestration layer
│   ├── commands/             # State-changing operations (Create, Update, Delete)
│   ├── queries/              # Read-only data retrieval operations
│   ├── handlers/             # Command/query processors
│   └── services/             # Application workflow coordination
├── infrastructure/           # Technical implementation details
│   ├── database/             # SQLAlchemy repositories, migrations, models
│   ├── external/             # Payment gateways (Cryptomus, Telegram Stars)
│   ├── background_tasks/     # APScheduler jobs and cleanup tasks
│   └── configuration/        # Settings management with Pydantic
├── presentation/             # User interface layers
│   ├── telegram/             # Aiogram bot handlers and middleware
│   ├── web/                  # FastAPI admin panel
│   └── webhooks/             # Payment callback processing
└── shared/                   # Cross-cutting concerns
    ├── dependency_injection/ # DI container and decorators
    ├── events/               # Event bus and base event classes
    └── exceptions/           # Custom exception types
```

### Key Components

- **DI Container** (`src/shared/dependency_injection/container.py`): Type-based dependency resolution with singleton/factory patterns
- **Event Bus** (`src/shared/events/bus.py`): Async in-memory event dispatcher for service decoupling
- **Database Manager** (`src/infrastructure/database/manager.py`): Connection pooling and session management
- **Payment Gateway Factory** (`src/infrastructure/external/payment_gateways/factory.py`): Pluggable payment processing system
- **UnitOfWork Pattern**: Transaction boundary management across repositories

## Configuration Management

Configuration uses **modular YAML** with environment variable overrides:

### Setup Process
1. Copy base configuration: `cp config/settings.example.yml config/settings.yml`
2. Edit required fields: `bot.token`, `bot.admins` (admin user IDs)
3. Configure payment gateways: `payments.cryptomus.api_key` and `merchant_id`
4. Set database URL for production: `database.url`

### Key Configuration Sections
- `bot`: Telegram bot token and admin settings
- `database`: SQLite (dev) or PostgreSQL (production) connection
- `redis`: Caching and event storage (Docker: `digitalstore-redis:6379`)
- `payments`: Gateway settings (Cryptomus, Telegram Stars)
- `shop`: Business rules (trial periods, referral rates, default currency)

### Products Configuration
Products are loaded from `data/products.json` (copy from `products.example.json`):
- **Categories**: software, gaming, subscription, digital_goods, services
- **Delivery Types**: license_key, account_info, download_link, api_access, manual
- **Stock Management**: Automatic stock tracking with configurable thresholds
- **Dynamic Templates**: Key generation with placeholders for user data

## Dependency Injection Usage

The DI system enables constructor injection with automatic type resolution:

```python
from src.shared.dependency_injection import container, inject

# Service registration (done in main.py)
container.register_factory(UserRepository, create_user_repository)

# Automatic injection in handlers/services
@inject
async def my_handler(user_service: UserApplicationService) -> None:
    user = await user_service.get_user_by_id("123")
    
# Works in class constructors too
@inject
class OrderService:
    def __init__(self, uow: UnitOfWork, payment_factory: PaymentGatewayFactory):
        self.uow = uow
        self.payment_factory = payment_factory
```

## Event System Usage

Domain events enable decoupled communication between bounded contexts:

```python
from src.shared.events import event_bus
from src.domain.events.user_events import UserRegistered

# Publishing from domain entities
user = User.create(username="john", email="john@example.com")
user.add_domain_event(UserRegistered.create(user_id=user.id, email=user.email))

# Event handlers run automatically
@event_handler("UserRegistered")
class WelcomeMessageHandler:
    @inject
    async def handle(self, event: UserRegistered, notification_service: NotificationService):
        await notification_service.send_welcome_message(event.user_id)
```

## Development Guidelines

### Adding New Features
1. **Domain First**: Create entities and value objects in `src/domain/entities/`
2. **Define Events**: Add domain events in `src/domain/events/` for important state changes
3. **Repository Interfaces**: Define data access contracts in `src/domain/repositories/`
4. **Application Layer**: Implement commands/queries in `src/application/`
5. **Infrastructure**: Implement repositories and external adapters
6. **Presentation**: Add Telegram handlers in `src/presentation/telegram/handlers/`
7. **Register Dependencies**: Update DI registrations in `src/main.py`

### Database Schema Changes
1. Modify SQLAlchemy models in `src/infrastructure/database/models/`
2. Create migration: `poetry run python -m ...migration_manager create "description"`
3. Test migration: `poetry run python -m ...migration_manager upgrade`
4. Update repository implementations if needed

### Payment Gateway Integration
1. Implement `PaymentGateway` base class from `src/infrastructure/external/payment_gateways/base.py`
2. Register in factory (`src/infrastructure/external/payment_gateways/factory.py`)
3. Add webhook handling in `src/presentation/webhooks/` if required
4. Update configuration schema in `src/infrastructure/configuration/settings.py`

### Testing Strategy
- **Unit Tests** (`tests/unit/`): Test domain logic in isolation using mocks
- **Integration Tests** (`tests/integration/`): Test repository implementations with real database
- **Application Tests**: End-to-end testing of command/query handlers
- **Factory Pattern**: Use `factory-boy` for consistent test data generation

## Important Development Constraints

- **Dependency Rule**: Domain layer never imports from application/infrastructure
- **Async Everywhere**: All I/O operations must use async/await patterns
- **Event Publishing**: Always publish domain events for significant business state changes
- **Immutable Value Objects**: Use `frozen=True` dataclasses for value objects
- **Type Safety**: Comprehensive type hints required, `mypy` must pass without errors
- **Interface Segregation**: Depend on abstractions (interfaces), not concrete implementations

## Common Development Issues

- **Missing Dependencies**: Check DI container registrations in `src/main.py:setup_dependencies()`
- **Event Handlers Not Triggering**: Verify handler registration with `@event_handler` decorator
- **Migration Conflicts**: Always create migrations on feature branches, resolve before merging
- **Configuration Loading**: Validate settings precedence (YAML → ENV vars → defaults)
- **Circular Dependencies**: Resolve through interfaces and proper dependency injection patterns
- **Database Sessions**: Always use UnitOfWork pattern, never direct session access

This architecture ensures maintainability, testability, and extensibility while maintaining clean separation of concerns and business logic isolation.