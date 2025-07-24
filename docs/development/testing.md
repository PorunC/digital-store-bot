# 测试指南

本文档介绍了 Digital Store Bot v2 的测试策略、工具和最佳实践。

## 🧪 测试策略

### 测试金字塔

```
        🔺 E2E Tests
       🔺🔺 Integration Tests  
    🔺🔺🔺🔺 Unit Tests
```

- **单元测试 (70%)**: 测试单个组件的功能
- **集成测试 (20%)**: 测试组件间的交互
- **端到端测试 (10%)**: 测试完整的用户流程

### 测试分类

使用 pytest 标记对测试进行分类：

```python
@pytest.mark.unit
def test_user_creation():
    """单元测试 - 快速、独立"""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
def test_user_repository():
    """集成测试 - 需要数据库"""
    pass

@pytest.mark.e2e
@pytest.mark.slow
def test_complete_purchase_flow():
    """端到端测试 - 较慢、完整流程"""
    pass

@pytest.mark.requires_external
def test_payment_gateway():
    """需要外部服务的测试"""
    pass
```

## 🏗️ 测试结构

### 目录结构

```
tests/
├── conftest.py              # 全局测试配置
├── unit/                    # 单元测试
│   ├── domain/             # 领域层测试
│   │   ├── entities/       # 实体测试
│   │   ├── value_objects/  # 值对象测试
│   │   └── services/       # 领域服务测试
│   ├── application/        # 应用层测试
│   │   ├── services/       # 应用服务测试
│   │   └── handlers/       # 事件处理器测试
│   └── infrastructure/     # 基础设施测试
├── integration/            # 集成测试
│   ├── database/          # 数据库集成测试
│   ├── external/          # 外部服务集成测试
│   └── api/               # API 集成测试
├── e2e/                   # 端到端测试
├── fixtures/              # 测试数据和固件
└── factories/             # 测试数据工厂
```

### 命名规范

测试文件和方法命名应该清晰描述测试内容：

```python
# 文件命名
test_user_entity.py
test_payment_service.py
test_order_repository.py

# 测试方法命名
def test_create_user_with_valid_data_should_succeed():
    pass

def test_create_user_with_duplicate_telegram_id_should_raise_error():
    pass

def test_calculate_order_total_with_discount_should_return_correct_amount():
    pass
```

## 🛠️ 测试工具

### 主要测试框架

```bash
# 安装测试依赖
poetry install --with dev

# 核心测试工具
pytest              # 测试框架
pytest-asyncio      # 异步测试支持
pytest-cov          # 覆盖率报告
pytest-mock         # Mock 支持
factory-boy         # 测试数据工厂
fakeredis           # Redis 模拟
aioresponses        # HTTP 请求模拟
freezegun           # 时间模拟
```

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定类型的测试
poetry run pytest -m unit           # 单元测试
poetry run pytest -m integration    # 集成测试
poetry run pytest -m "not slow"     # 跳过慢测试

# 运行特定文件或目录
poetry run pytest tests/unit/domain/
poetry run pytest tests/unit/domain/test_user.py

# 运行特定测试方法
poetry run pytest tests/unit/domain/test_user.py::TestUser::test_create_user

# 运行匹配模式的测试
poetry run pytest -k "test_payment"

# 详细输出
poetry run pytest -v -s

# 生成覆盖率报告
poetry run pytest --cov=src --cov-report=html
```

## 🧩 单元测试

### 领域层测试

测试业务逻辑和领域规则：

```python
# tests/unit/domain/entities/test_user.py
import pytest
from datetime import datetime
from src.domain.entities.user import User
from src.domain.events.user_events import UserCreated

class TestUser:
    def test_create_user_with_valid_data_should_succeed(self):
        # Arrange
        telegram_id = "123456789"
        username = "test_user"
        
        # Act
        user = User.create(telegram_id=telegram_id, username=username)
        
        # Assert
        assert user.telegram_id == telegram_id
        assert user.username == username
        assert isinstance(user.created_at, datetime)
        assert len(user.get_domain_events()) == 1
        assert isinstance(user.get_domain_events()[0], UserCreated)

    def test_create_user_with_invalid_telegram_id_should_raise_error(self):
        # Arrange
        invalid_telegram_id = ""
        
        # Act & Assert
        with pytest.raises(ValueError, match="Telegram ID cannot be empty"):
            User.create(telegram_id=invalid_telegram_id)
```

### 值对象测试

```python
# tests/unit/domain/value_objects/test_money.py
import pytest
from decimal import Decimal
from src.domain.value_objects.money import Money

class TestMoney:
    def test_create_money_with_valid_amount_should_succeed(self):
        # Arrange & Act
        money = Money(amount=Decimal("10.50"), currency="USD")
        
        # Assert
        assert money.amount == Decimal("10.50")
        assert money.currency == "USD"

    def test_create_money_with_negative_amount_should_raise_error(self):
        # Act & Assert
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Money(amount=Decimal("-5.00"), currency="USD")

    def test_add_money_with_same_currency_should_return_sum(self):
        # Arrange
        money1 = Money(amount=Decimal("10.00"), currency="USD")
        money2 = Money(amount=Decimal("5.50"), currency="USD")
        
        # Act
        result = money1.add(money2)
        
        # Assert
        assert result.amount == Decimal("15.50")
        assert result.currency == "USD"
```

### 应用服务测试

```python
# tests/unit/application/services/test_user_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.application.services.user_service import UserApplicationService
from src.application.commands.user_commands import CreateUserCommand
from src.domain.entities.user import User

class TestUserApplicationService:
    @pytest.fixture
    def mock_uow(self):
        uow = Mock()
        uow.users = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def user_service(self, mock_uow):
        return UserApplicationService(uow=mock_uow)

    @pytest.mark.asyncio
    async def test_create_user_should_save_to_repository(self, user_service, mock_uow):
        # Arrange
        command = CreateUserCommand(
            telegram_id="123456789",
            username="test_user"
        )
        
        # Act
        user = await user_service.create_user(command)
        
        # Assert
        assert user.telegram_id == command.telegram_id
        assert user.username == command.username
        mock_uow.users.add.assert_called_once_with(user)
        mock_uow.commit.assert_called_once()
```

## 🔗 集成测试

### 数据库集成测试

```python
# tests/integration/database/test_user_repository.py
import pytest
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.domain.entities.user import User
from tests.factories.user_factory import UserFactory

@pytest.mark.integration
@pytest.mark.requires_db
class TestSqlAlchemyUserRepository:
    @pytest.fixture
    async def user_repository(self, db_session):
        return SqlAlchemyUserRepository(session=db_session)

    @pytest.mark.asyncio
    async def test_add_user_should_persist_to_database(self, user_repository, db_session):
        # Arrange
        user = UserFactory.build()
        
        # Act
        await user_repository.add(user)
        await db_session.commit()
        
        # Assert
        saved_user = await user_repository.get_by_id(user.id)
        assert saved_user is not None
        assert saved_user.telegram_id == user.telegram_id

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_should_return_correct_user(self, user_repository):
        # Arrange
        user = UserFactory.create()
        await user_repository.add(user)
        
        # Act
        found_user = await user_repository.get_by_telegram_id(user.telegram_id)
        
        # Assert
        assert found_user is not None
        assert found_user.id == user.id
```

### 外部服务集成测试

```python
# tests/integration/external/test_cryptomus_gateway.py
import pytest
from aioresponses import aioresponses
from src.infrastructure.external.payment_gateways.cryptomus import CryptomusGateway
from src.domain.value_objects.money import Money

@pytest.mark.integration
@pytest.mark.requires_external
class TestCryptomusGateway:
    @pytest.fixture
    def payment_gateway(self):
        return CryptomusGateway(
            merchant_id="test_merchant",
            api_key="test_key"
        )

    @pytest.mark.asyncio
    async def test_create_payment_should_return_payment_url(self, payment_gateway):
        # Arrange
        amount = Money(amount=Decimal("10.00"), currency="USD")
        order_id = "order_123"
        
        mock_response = {
            "state": 0,
            "result": {
                "url": "https://pay.cryptomus.com/pay/uuid",
                "uuid": "payment_uuid"
            }
        }
        
        # Act
        with aioresponses() as m:
            m.post(
                "https://api.cryptomus.com/v1/payment",
                payload=mock_response
            )
            
            payment = await payment_gateway.create_payment(amount, order_id)
            
        # Assert
        assert payment.url == "https://pay.cryptomus.com/pay/uuid"
        assert payment.payment_id == "payment_uuid"
```

## 🏁 端到端测试

### 完整流程测试

```python
# tests/e2e/test_purchase_flow.py
import pytest
from unittest.mock import AsyncMock
from aiogram.methods import SendMessage
from tests.conftest import MockBot

@pytest.mark.e2e
@pytest.mark.slow
class TestPurchaseFlow:
    @pytest.mark.asyncio
    async def test_complete_purchase_flow_should_succeed(self, mock_bot, db_session):
        # Arrange
        user_id = "123456789"
        product_id = "premium_1month"
        
        # Step 1: User starts bot
        await mock_bot.send_command("/start", user_id)
        
        # Step 2: User browses products
        await mock_bot.send_callback("shop", user_id)
        await mock_bot.send_callback(f"product_{product_id}", user_id)
        
        # Step 3: User initiates purchase
        await mock_bot.send_callback(f"buy_{product_id}", user_id)
        
        # Step 4: User completes payment
        await mock_bot.send_callback("pay_telegram_stars", user_id)
        
        # Assert payment and delivery
        messages = mock_bot.get_sent_messages(user_id)
        assert any("支付成功" in msg.text for msg in messages)
        assert any("产品已发货" in msg.text for msg in messages)
```

## 🏭 测试工厂

### 使用 Factory Boy 创建测试数据

```python
# tests/factories/user_factory.py
import factory
from factory import fuzzy
from datetime import datetime
from src.domain.entities.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Faker('uuid4')
    telegram_id = factory.Sequence(lambda n: str(1000000 + n))
    username = factory.Faker('user_name')
    created_at = factory.LazyFunction(datetime.utcnow)
    is_active = True

# tests/factories/order_factory.py
import factory
from decimal import Decimal
from src.domain.entities.order import Order
from src.domain.value_objects.money import Money
from .user_factory import UserFactory

class OrderFactory(factory.Factory):
    class Meta:
        model = Order

    id = factory.Faker('uuid4')
    user = factory.SubFactory(UserFactory)
    product_id = "premium_1month"
    amount = factory.LazyFunction(
        lambda: Money(amount=Decimal("9.99"), currency="USD")
    )
    status = "pending"
```

### 使用工厂创建测试数据

```python
# 在测试中使用工厂
def test_user_service():
    # 创建单个用户
    user = UserFactory.build()  # 不保存到数据库
    user = UserFactory.create()  # 保存到数据库（如果配置了）
    
    # 创建多个用户
    users = UserFactory.build_batch(5)
    
    # 自定义属性
    admin_user = UserFactory.build(is_admin=True)
    
    # 创建关联对象
    order = OrderFactory.build(user=user)
```

## 🎭 Mock 和存根

### Mock 外部依赖

```python
# tests/unit/application/test_payment_service.py
import pytest
from unittest.mock import AsyncMock, patch
from src.application.services.payment_service import PaymentApplicationService

class TestPaymentApplicationService:
    @pytest.fixture
    def mock_payment_gateway(self):
        gateway = AsyncMock()
        gateway.create_payment.return_value = Mock(
            payment_id="payment_123",
            url="https://pay.example.com/payment_123"
        )
        return gateway

    @pytest.mark.asyncio
    async def test_create_payment_should_use_gateway(self, mock_payment_gateway):
        # Arrange
        service = PaymentApplicationService(gateway=mock_payment_gateway)
        amount = Money(Decimal("10.00"), "USD")
        
        # Act
        payment = await service.create_payment(amount, "order_123")
        
        # Assert
        mock_payment_gateway.create_payment.assert_called_once_with(
            amount, "order_123"
        )
        assert payment.payment_id == "payment_123"
```

### 时间模拟

```python
# tests/unit/domain/test_trial_system.py
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta
from src.domain.entities.trial import Trial

class TestTrial:
    @freeze_time("2024-01-01 12:00:00")
    def test_trial_should_expire_after_period(self):
        # Arrange
        trial = Trial.create(user_id="user_123", days=3)
        
        # Act - 时间前进4天
        with freeze_time("2024-01-05 12:00:00"):
            is_expired = trial.is_expired()
        
        # Assert
        assert is_expired is True
```

## 📊 测试覆盖率

### 配置覆盖率

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = [
    "src/infrastructure/database/migrations/*",
    "src/shared/testing/*",
    "tests/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod"
]
```

### 生成覆盖率报告

```bash
# HTML 报告
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html

# 终端报告
poetry run pytest --cov=src --cov-report=term

# 缺失行数报告
poetry run pytest --cov=src --cov-report=term-missing

# 设置覆盖率阈值
poetry run pytest --cov=src --cov-fail-under=80
```

## 🚀 持续集成

### GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run tests
      run: |
        poetry run pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 📝 测试最佳实践

### 1. AAA 模式

```python
def test_user_creation():
    # Arrange (准备)
    telegram_id = "123456789"
    username = "test_user"
    
    # Act (执行)
    user = User.create(telegram_id, username)
    
    # Assert (断言)
    assert user.telegram_id == telegram_id
```

### 2. 一个测试一个断言

```python
# ✅ 好的做法
def test_user_creation_sets_telegram_id():
    user = User.create("123456789", "test")
    assert user.telegram_id == "123456789"

def test_user_creation_sets_username():
    user = User.create("123456789", "test")
    assert user.username == "test"

# ❌ 避免
def test_user_creation():
    user = User.create("123456789", "test")
    assert user.telegram_id == "123456789"
    assert user.username == "test"
    assert user.is_active is True
```

### 3. 测试边界条件

```python
def test_money_with_zero_amount():
    money = Money(Decimal("0"), "USD")
    assert money.amount == Decimal("0")

def test_money_with_max_precision():
    money = Money(Decimal("999999.99"), "USD")
    assert money.amount == Decimal("999999.99")
```

### 4. 使用描述性断言消息

```python
def test_user_balance_after_purchase():
    user = UserFactory.build(balance=Decimal("100.00"))
    order = OrderFactory.build(amount=Money(Decimal("30.00"), "USD"))
    
    user.process_purchase(order)
    
    assert user.balance == Decimal("70.00"), \
        f"Expected balance 70.00, got {user.balance}"
```

## 🔧 调试测试

### 使用 pytest 调试功能

```bash
# 在第一个失败处停止
poetry run pytest -x

# 显示本地变量
poetry run pytest --tb=long

# 进入调试器
poetry run pytest --pdb

# 只运行失败的测试
poetry run pytest --lf

# 详细输出
poetry run pytest -vvv
```

### 使用 pytest-xdist 并行测试

```bash
# 安装插件
poetry add --group dev pytest-xdist

# 并行运行测试
poetry run pytest -n auto
poetry run pytest -n 4  # 使用4个进程
```

## 📚 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [Factory Boy 文档](https://factoryboy.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Effective Python Testing](https://realpython.com/python-testing/)

---

🧪 **记住**: 好的测试是代码质量的保证，也是重构和维护的安全网！