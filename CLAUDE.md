# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Direct Development
- `poetry run python -m src.main` - Run the bot directly
- `poetry run python -m src.main --dev` - Run in development mode
- `poetry run python -m src.presentation.web.admin_panel` - Run admin panel
- `poetry run python -m src.infrastructure.background_tasks.scheduler_main` - Run background scheduler

### Docker Development and Deployment
- `docker compose up -d` - Start all services (bot, postgres, redis, traefik)
- `docker compose up -d --profile monitoring` - Start with monitoring (prometheus, grafana)
- `docker compose up -d --profile logging` - Start with logging (loki, promtail)
- `docker compose down` - Stop all services
- `docker compose logs -f bot` - View bot logs
- `docker compose build` - Build containers

### Quick Docker Management Scripts
- `./scripts/quick_restart.sh` - Quick restart all services except Traefik
- `./scripts/restart_without_traefik.sh --app` - Restart application services
- `./scripts/docker_manager.sh zero-downtime --app` - Zero-downtime deployment
- `./scripts/docker_manager.sh status` - Check service status

### Database Management
- `poetry run python -m src.infrastructure.database.migrations.migration_manager create "description"` - Create migration
- `poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade` - Apply migrations
- `poetry run python -m src.infrastructure.database.migrations.migration_manager downgrade` - Rollback migrations

### Code Quality and Testing
- `poetry run pytest` - Run all tests
- `poetry run pytest -m unit` - Run unit tests only
- `poetry run pytest -m integration` - Run integration tests only
- `poetry run pytest --cov-report=html` - Generate coverage report
- `poetry run black src tests` - Format code
- `poetry run isort src tests` - Sort imports
- `poetry run flake8 src tests` - Lint code
- `poetry run mypy src` - Type checking

### Project Setup
- `./scripts/setup.sh` - Automated development environment setup
- `./scripts/healthcheck.sh` - Check service health
- `python scripts/check_services.py` - Comprehensive service status check

## Project Architecture

This project follows **Domain-Driven Design (DDD)** with **Clean Architecture** principles and uses **dependency-injector** for IoC.

### Core Architecture Layers

```
src/
├── domain/                    # 🏛️ Domain Layer - Core business logic
│   ├── entities/             # Business entities (User, Order, Product)
│   ├── value_objects/        # Immutable value objects (Money, UserProfile)
│   ├── repositories/         # Repository interfaces
│   ├── services/             # Domain services
│   └── events/               # Domain events
├── application/              # 🔧 Application Layer - Use cases
│   ├── commands/             # Command handlers (CQRS)
│   ├── queries/              # Query handlers (CQRS)
│   ├── handlers/             # Event handlers
│   └── services/             # Application services
├── infrastructure/           # 🔌 Infrastructure Layer - Technical implementation
│   ├── database/             # SQLAlchemy models, repositories, migrations
│   ├── external/             # Payment gateways, analytics
│   ├── background_tasks/     # APScheduler background tasks
│   ├── configuration/        # Settings management
│   └── notifications/        # Telegram notifications
├── presentation/             # 🖥️ Presentation Layer - User interfaces
│   ├── telegram/             # Telegram bot handlers and middleware
│   ├── web/                  # FastAPI admin panel
│   └── webhooks/             # Payment webhook handlers
├── shared/                   # 🔄 Shared utilities
│   ├── events/               # Event bus system
│   ├── exceptions/           # Custom exceptions
│   └── utils/                # Common utilities
└── core/                     # 🏗️ Core framework
    └── containers.py         # Dependency injection container
```

### Key Architectural Patterns

- **Domain-Driven Design**: Clear business boundaries and ubiquitous language
- **Clean Architecture**: Dependency inversion with layers pointing inward
- **CQRS**: Separate command and query responsibilities
- **Event-Driven Architecture**: Asynchronous event bus for loose coupling
- **Dependency Injection**: `dependency-injector` framework for IoC
- **Repository Pattern**: Abstracted data access
- **Unit of Work**: Transaction management across repositories

### Dependency Injection System

The project uses `dependency-injector` framework with the main container in `src/core/containers.py`:

#### Key Container Components
- **ApplicationContainer**: Main DI container managing all services
- **Factory Functions**: Lazy initialization to avoid circular dependencies
- **@inject Decorator**: Automatic dependency injection in handlers
- **Provide Annotations**: Explicit dependency declarations

#### Usage Example
```python
from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer

@inject
async def my_handler(
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    # Services automatically injected
    user = await user_service.get_user_by_id("123")
    order = await order_service.create_order(...)
```

### Core Services

#### Application Services
- **UserApplicationService**: User management and authentication
- **OrderApplicationService**: Order processing and fulfillment
- **ProductApplicationService**: Product catalog management
- **PaymentApplicationService**: Payment processing coordination
- **ReferralApplicationService**: Multi-level referral system
- **PromocodeApplicationService**: Discount code management
- **TrialApplicationService**: Trial subscription handling
- **ProductLoaderService**: JSON product catalog loading

#### Infrastructure Services
- **PaymentGatewayFactory**: Multi-gateway payment processing
- **NotificationService**: Admin and user messaging
- **AnalyticsService**: Usage analytics and tracking
- **DatabaseManager**: Database connection and session management
- **EventBus**: Asynchronous event distribution

### Database Layer

#### Models (Infrastructure Layer)
Located in `src/infrastructure/database/models/`:
- **User**: Central user entity with relationships
- **Order**: Order transactions and status
- **Product**: Digital product catalog
- **Promocode**: Discount codes system
- **Referral**: Multi-level referral tracking

#### Repositories
Repository pattern with interface in domain layer and implementation in infrastructure:
- Domain interfaces: `src/domain/repositories/`
- SQLAlchemy implementations: `src/infrastructure/database/repositories/`

#### Migrations
- Migration files: `src/infrastructure/database/migrations/`
- Custom migration manager with automatic schema detection
- Support for both SQLite (dev) and PostgreSQL (prod)

### Configuration Management

#### Settings System
- Main config: `config/settings.yml`
- Security config: `config/settings.security.yml` (for sensitive data)
- Pydantic-based settings validation in `src/infrastructure/configuration/settings.py`

#### Key Configuration Sections
- **Bot**: Telegram bot token, admins, domain
- **Database**: Connection settings with driver flexibility
- **Shop**: Business logic settings (trial, referral rates)
- **Payments**: Gateway configurations (Cryptomus, Telegram Stars)
- **Products**: Catalog file path and categories

### Payment System

#### Multi-Gateway Architecture
- **Base Gateway**: Abstract payment gateway interface
- **Supported Gateways**: Telegram Stars, Cryptomus
- **Factory Pattern**: Dynamic gateway selection
- **Webhook Integration**: Automatic payment status updates

#### Gateway Implementation
1. Inherit from `PaymentGateway` base class
2. Implement required methods (`create_payment`, `handle_callback`)
3. Register in `PaymentGatewayFactory`
4. Add webhook routes if needed

### Background Tasks

#### Scheduler System
- **APScheduler**: Async job scheduling
- **Cleanup Tasks**: Auto-cancel expired transactions
- **Notification Tasks**: Automated messaging
- **Payment Tasks**: Transaction status monitoring

#### Task Management
- Main scheduler: `src/infrastructure/background_tasks/scheduler_main.py`
- Task definitions: `src/infrastructure/background_tasks/`
- Configurable intervals and retry policies

### Product System

#### JSON-Based Catalog
- Product definitions in `data/products.json`
- Categories: software, gaming, subscription, digital, education
- Delivery types: license_key, account_info, download_link, api_access
- Stock management and dynamic pricing
- Template-based key generation

### Testing Strategy

#### Test Structure
- Unit tests: `tests/unit/` - Domain and application logic
- Integration tests: `tests/integration/` - Full workflow testing
- Test configuration: `tests/conftest.py`

#### Test Dependencies
- **pytest**: Test framework with async support
- **factory-boy**: Test data factories
- **fakeredis**: Redis mocking
- **aioresponses**: HTTP mocking

### Development Workflow

#### Adding New Features
1. **Domain Layer**: Define entities and value objects in `src/domain/`
2. **Application Layer**: Implement use cases in `src/application/services/`
3. **Infrastructure Layer**: Add persistence in `src/infrastructure/database/`
4. **Presentation Layer**: Create handlers in `src/presentation/telegram/handlers/`
5. **Dependency Registration**: Wire services in `src/core/containers.py`
6. **Handler Wiring**: Add module to container wiring in `src/main.py`

#### Database Changes
1. Modify domain entities in `src/domain/entities/`
2. Update SQLAlchemy models in `src/infrastructure/database/models/`
3. Create migration: `poetry run python -m src.infrastructure.database.migrations.migration_manager create "description"`
4. Apply migration: `poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade`

### Deployment Architecture

#### Docker Services
- **bot**: Main Telegram bot application
- **admin**: Web-based admin panel
- **scheduler**: Background task processor
- **postgres**: Primary database
- **redis**: Caching and session storage
- **traefik**: Reverse proxy with SSL termination

#### Production Features
- **Zero-downtime deployment**: Via Traefik load balancing
- **Health checks**: All services have health endpoints
- **SSL termination**: Automatic Let's Encrypt certificates
- **Monitoring**: Optional Prometheus + Grafana stack
- **Logging**: Optional Loki + Promtail for log aggregation

### Monitoring and Observability

#### Health Checking
- Service health endpoints
- Database connectivity checks
- Redis availability monitoring
- Automatic service restart on failure

#### Logging
- Structured logging with configurable levels
- File rotation and archiving
- Console and file output
- Error tracking and admin notifications

This is a production-ready Telegram e-commerce bot with sophisticated architecture supporting multi-gateway payments, referral systems, and enterprise-scale deployment patterns.