# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this Digital Store Bot v2 project.

## 🏗️ Architecture Overview

This is a **Domain-Driven Design (DDD)** implementation of a Telegram e-commerce bot with **high decoupling** and **clean architecture**. The project addresses the coupling issues found in the original 3xui-shop project.

### Key Architectural Patterns

- **Domain-Driven Design**: Clear business boundaries with entities, value objects, and domain services
- **Dependency Injection**: Using `dependency-injector` for loose coupling
- **Event-Driven Architecture**: Domain events for service communication
- **Repository Pattern**: Data access abstraction
- **Unit of Work**: Transaction management
- **Hexagonal Architecture**: Ports and adapters pattern

## 📁 Project Structure

```
src/
├── domain/                    # Business logic layer
│   ├── entities/             # Business entities (User, Product, Order)
│   ├── value_objects/        # Immutable value objects (Money, UserProfile)
│   ├── repositories/         # Repository interfaces
│   ├── services/             # Domain services
│   └── events/               # Domain events
├── application/              # Application layer
│   ├── commands/             # Command handlers (CQRS)
│   ├── queries/              # Query handlers (CQRS)
│   ├── handlers/             # Event handlers
│   └── services/             # Application services
├── infrastructure/           # Infrastructure layer
│   ├── database/             # SQLAlchemy implementation
│   ├── external/             # External service adapters
│   ├── messaging/            # Message bus implementation
│   └── configuration/        # Configuration management
├── presentation/             # Presentation layer
│   ├── telegram/             # Telegram bot interface
│   ├── web/                  # Web API (if needed)
│   └── cli/                  # CLI interface
└── shared/                   # Shared kernel
    ├── events/               # Event system
    ├── dependency_injection/ # DI framework
    └── exceptions/           # Custom exceptions
```

## 🚀 Essential Commands

### Development Setup
```bash
# Install dependencies
poetry install

# Setup project (creates config files, pre-commit hooks)
./scripts/setup.sh

# Run the application
poetry run python -m src.main

# Run in development mode with auto-reload
poetry run python -m src.main --dev
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_example.py

# Run tests matching pattern
poetry run pytest -k "test_user"
```

### Code Quality
```bash
# Format code
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
# Create migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

## 🔧 Configuration Management

The application uses **modular configuration** with Pydantic Settings:

- **Main config**: `config/settings.yml` - YAML-based configuration
- **Environment override**: `.env` file for secrets and environment-specific settings
- **Settings classes**: Organized by domain (BotConfig, DatabaseConfig, etc.)

Example configuration access:
```python
from infrastructure.configuration import get_settings

settings = get_settings()
bot_token = settings.bot.token
db_url = settings.database.get_url()
```

## 🔄 Dependency Injection Usage

The DI container manages all dependencies:

```python
from shared.dependency_injection import container, inject

# Register dependencies
container.register_singleton(UserRepository, SqlAlchemyUserRepository)

# Inject dependencies
@inject
def my_service(user_repo: UserRepository) -> None:
    users = await user_repo.get_all()
```

## 📡 Event System Usage

Domain events enable loose coupling between services:

```python
from shared.events import event_bus
from domain.events import UserRegistered

# Publish event
event = UserRegistered.create(user_id="123", telegram_id=456789)
await event_bus.publish(event)

# Handle event
@event_handler("UserRegistered")
class SendWelcomeMessage:
    async def handle(self, event: DomainEvent) -> None:
        # Send welcome message logic
        pass
```

## 🏛️ Key Design Principles

### 1. **Dependency Inversion**
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- Use `@inject` decorator for automatic dependency injection

### 2. **Single Responsibility**
- Each class has one reason to change
- Separate business logic from infrastructure concerns
- Use domain services for complex business rules

### 3. **Open/Closed Principle**
- Open for extension, closed for modification
- Use strategy pattern for payment gateways
- Event-driven architecture for adding new features

### 4. **Event-Driven Communication**
- Services communicate through domain events
- Avoid direct service-to-service calls
- Use event handlers for side effects

## 📝 Common Development Patterns

### Adding a New Entity
1. Create entity in `src/domain/entities/`
2. Define repository interface in `src/domain/repositories/`
3. Implement repository in `src/infrastructure/database/`
4. Create domain events in `src/domain/events/`
5. Add migration for database schema

### Adding a New Feature
1. Create command/query in `src/application/`
2. Implement handler in `src/application/handlers/`
3. Add presentation layer in `src/presentation/telegram/`
4. Register dependencies in DI container
5. Write tests for all layers

### Adding External Integration
1. Define port (interface) in `src/domain/`
2. Create adapter in `src/infrastructure/external/`
3. Register in DI container
4. Use events for integration points

## 🧪 Testing Strategy

- **Unit Tests**: Test domain logic in isolation
- **Integration Tests**: Test repository implementations
- **Application Tests**: Test command/query handlers
- **End-to-End Tests**: Test complete user journeys
- **Mock external dependencies** using `pytest-mock`

## 🚨 Important Notes

- **Never import infrastructure from domain layer**
- **Use dependency injection** instead of direct instantiation
- **Publish domain events** for all important business actions
- **Keep value objects immutable** (frozen=True)
- **Use async/await** for all I/O operations
- **Follow the dependency rule**: dependencies point inward toward the domain

## 🔍 Debugging Tips

- Check DI container registrations for missing dependencies
- Verify event handlers are properly registered
- Use logging extensively (configured in settings.yml)
- Check configuration loading order (YAML → ENV → defaults)
- Validate database connections and migrations

This architecture ensures **high maintainability**, **testability**, and **extensibility** while solving the coupling issues present in the original project.