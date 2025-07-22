# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Essential Commands

### Development Setup
```bash
# Install dependencies and setup project
./scripts/setup.sh

# Install dependencies only
poetry install

# Run the application
poetry run python -m src.main

# Run in development with auto-reload
poetry run python -m src.main --dev
```

### Testing
```bash
# Run all tests with coverage
poetry run pytest

# Run specific test markers
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m "not slow"

# Run tests without coverage (faster)
poetry run pytest --no-cov

# Run specific test file
poetry run pytest tests/unit/domain/test_user.py

# Run tests matching pattern
poetry run pytest -k "test_subscription"
```

### Code Quality
```bash
# Format code (line length: 100)
poetry run black src tests

# Sort imports
poetry run isort src tests

# Run linting
poetry run flake8 src tests

# Type checking
poetry run mypy src

# Run all quality checks
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

# View bot logs
docker compose logs -f bot

# Start with monitoring stack
docker compose --profile monitoring up -d

# Stop all services
docker compose down

# Rebuild containers
docker compose build --no-cache
```

## 🏗️ Architecture Overview

This is a **Domain-Driven Design (DDD)** implementation with **clean architecture** principles, addressing coupling issues from the original 3xui-shop project.

### Core Patterns

- **Domain-Driven Design**: Clear business boundaries with entities, value objects, and domain services
- **Dependency Injection**: Custom container with automatic resolution via `@inject` decorator
- **Event-Driven Architecture**: Domain events with async event bus for service communication
- **CQRS**: Separate command and query handlers for clear responsibility separation
- **Repository Pattern**: Data access abstraction with interface-based contracts
- **Hexagonal Architecture**: Ports and adapters pattern with dependency inversion

### Layer Structure

```
src/
├── domain/                    # Business logic (no external dependencies)
│   ├── entities/             # Rich domain objects (User, Order, Product)
│   ├── value_objects/        # Immutable objects (Money, UserProfile)
│   ├── repositories/         # Abstract data access interfaces
│   ├── services/             # Domain services for complex business rules
│   └── events/               # Domain events for state changes
├── application/              # Application orchestration
│   ├── commands/             # State-changing operations
│   ├── queries/              # Read-only data retrieval
│   ├── handlers/             # Command/query processors
│   └── services/             # Application workflow coordination
├── infrastructure/           # Technical implementation
│   ├── database/             # SQLAlchemy repositories and migrations
│   ├── external/             # Payment gateways (Cryptomus, Telegram Stars)
│   ├── background_tasks/     # Scheduled jobs and cleanup
│   └── configuration/        # Settings management
├── presentation/             # User interfaces
│   ├── telegram/             # Aiogram bot with handlers and middleware
│   ├── web/                  # Admin panel
│   └── webhooks/             # Payment callback processing
└── shared/                   # Cross-cutting concerns
    ├── dependency_injection/ # DI container and decorators
    ├── events/               # Event bus and base event classes
    └── exceptions/           # Custom exception types
```

### Key Components

- **DI Container** (`src/shared/dependency_injection/container.py`): Type-based dependency resolution with singleton/factory patterns
- **Event Bus** (`src/shared/events/bus.py`): Async in-memory event dispatcher for loose coupling
- **Database Manager** (`src/infrastructure/database/manager.py`): Connection pooling and session management
- **Configuration System** (`src/infrastructure/configuration/settings.py`): Pydantic-based settings with YAML/ENV support
- **Payment Gateway Factory** (`src/infrastructure/external/payment_gateways/factory.py`): Pluggable payment processing

## 🔧 Configuration Management

Configuration uses **modular YAML** with environment overrides:

- **Primary config**: `config/settings.yml` (copy from `settings.example.yml`)
- **Environment variables**: `.env` file for secrets and overrides
- **Docker environment**: Environment variables in `docker-compose.yml`

Key sections:
- `bot`: Telegram bot token and admin settings  
- `database`: Connection settings (SQLite/PostgreSQL)
- `redis`: Caching and event storage
- `payments`: Gateway configuration (Cryptomus, Telegram Stars)
- `shop`: Business logic (trial periods, referral rates)

## 📡 Dependency Injection Usage

The DI system enables constructor injection with automatic resolution:

```python
from src.shared.dependency_injection import container, inject

# Register dependencies (done in main.py)
container.register_singleton(UserRepository, SqlAlchemyUserRepository)

# Automatic injection
@inject
async def my_handler(user_repo: UserRepository) -> None:
    user = await user_repo.get_by_id("123")
```

## 🎯 Event System Usage

Domain events enable decoupled communication between services:

```python
from src.shared.events import event_bus
from src.domain.events.user_events import UserRegistered

# Publish from entity
user.add_domain_event(UserRegistered.create(user_id="123"))
await event_bus.publish_many(user.get_domain_events())

# Handle events
@event_handler("UserRegistered")
class WelcomeMessageHandler:
    @inject
    async def handle(self, event: UserRegistered, notification_service: NotificationService) -> None:
        await notification_service.send_welcome_message(event.user_id)
```

## 🏛️ Development Guidelines

### Adding New Features

1. **Domain First**: Create entities, value objects, and domain events in `src/domain/`
2. **Application Layer**: Add commands/queries and handlers in `src/application/`
3. **Infrastructure**: Implement repositories and external service adapters
4. **Presentation**: Add Telegram handlers or web endpoints
5. **Register Dependencies**: Update DI container registrations in `main.py`

### Database Changes

1. Modify models in `src/infrastructure/database/models/`
2. Create migration: `poetry run python -m src.infrastructure.database.migrations.migration_manager create "description"`
3. Apply migration: `poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade`

### Payment Gateway Integration

1. Implement `PaymentGateway` interface from `src/infrastructure/external/payment_gateways/base.py`
2. Register in factory (`src/infrastructure/external/payment_gateways/factory.py`)
3. Add webhook handling if needed
4. Update configuration schema

### Testing Strategy

- **Unit Tests**: Test domain logic in isolation (`tests/unit/domain/`)
- **Integration Tests**: Test repository implementations (`tests/integration/`)
- **Application Tests**: Test command/query handlers end-to-end
- **Use factories**: Create test data with `factory-boy` patterns

## ⚠️ Important Constraints

- **Dependency Rule**: Never import infrastructure from domain layer
- **Event Publishing**: Always publish domain events for important business actions
- **Immutable Value Objects**: Use `frozen=True` for value object dataclasses
- **Async Everywhere**: All I/O operations must use async/await
- **Type Safety**: Extensive type hints required, mypy must pass
- **Interface Segregation**: Depend on abstractions, not concrete implementations

## 🚨 Common Issues

- **Missing Dependencies**: Check DI container registrations in `main.py`
- **Event Handler Not Triggered**: Verify handler is registered with `@event_handler` decorator
- **Migration Conflicts**: Always create migrations on feature branches
- **Configuration Errors**: Validate settings loading order (YAML → ENV → defaults)
- **Circular Dependencies**: Resolve through interfaces and dependency injection

This architecture ensures high maintainability, testability, and extensibility while maintaining clean separation of concerns and business logic isolation.