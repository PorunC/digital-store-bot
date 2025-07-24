# 代码规范和最佳实践

本文档定义了 Digital Store Bot v2 项目的代码规范和开发最佳实践。

## 🐍 Python 代码规范

### 代码格式化

项目使用以下工具进行代码格式化：

```bash
# 代码格式化
poetry run black src tests

# 导入排序
poetry run isort src tests

# 代码检查
poetry run flake8 src tests

# 类型检查
poetry run mypy src
```

### 代码风格

- **行长度**: 最大 100 字符
- **缩进**: 4 个空格，不使用 Tab
- **引号**: 优先使用双引号 `"`
- **命名约定**:
  - 类名：`PascalCase`
  - 函数名：`snake_case`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有方法：`_leading_underscore`

### 类型注解

所有公共函数和方法必须有类型注解：

```python
# ✅ 正确
async def create_user(
    user_data: CreateUserCommand,
    user_repo: UserRepository
) -> User:
    return await user_repo.create(user_data)

# ❌ 错误
async def create_user(user_data, user_repo):
    return await user_repo.create(user_data)
```

## 🏗️ 架构规范

### Domain-Driven Design (DDD)

#### 领域层 (Domain)

```python
# 实体 (Entities)
@dataclass
class User(Entity):
    telegram_id: str
    username: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def change_username(self, new_username: str) -> None:
        self.username = new_username
        self.add_domain_event(UserUpdated.create(user_id=self.id))

# 值对象 (Value Objects)
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

# 领域事件 (Domain Events)
@dataclass(frozen=True)
class UserCreated(DomainEvent):
    user_id: str
    telegram_id: str
```

#### 应用层 (Application)

```python
# 命令 (Commands)
@dataclass
class CreateUserCommand:
    telegram_id: str
    username: Optional[str] = None

# 查询 (Queries)  
@dataclass
class GetUserQuery:
    user_id: str

# 应用服务 (Application Services)
class UserApplicationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
    
    @inject
    async def create_user(self, command: CreateUserCommand) -> User:
        async with self._uow:
            # 业务逻辑
            user = User.create(command.telegram_id, command.username)
            await self._uow.users.add(user)
            await self._uow.commit()
            return user
```

### 依赖注入规范

使用 `@inject` 装饰器进行依赖注入：

```python
# ✅ 正确的依赖注入
@inject
async def handler(
    user_service: UserApplicationService,
    product_service: ProductApplicationService
) -> None:
    # 处理逻辑
    pass

# ❌ 避免手动创建依赖
async def handler() -> None:
    user_service = UserApplicationService()  # 不推荐
```

## 🧪 测试规范

### 测试结构

```
tests/
├── unit/                 # 单元测试
│   ├── domain/          # 领域层测试
│   ├── application/     # 应用层测试
│   └── infrastructure/  # 基础设施测试
├── integration/         # 集成测试
└── conftest.py         # 测试配置
```

### 测试命名

测试方法使用描述性命名：

```python
class TestUser:
    def test_create_user_with_valid_data_should_succeed(self) -> None:
        # 测试逻辑
        pass
    
    def test_create_user_with_invalid_telegram_id_should_raise_error(self) -> None:
        # 测试逻辑
        pass
```

### 测试标记

使用 pytest 标记分类测试：

```python
@pytest.mark.unit
def test_user_creation() -> None:
    pass

@pytest.mark.integration
@pytest.mark.requires_db
def test_user_repository() -> None:
    pass

@pytest.mark.slow
def test_payment_flow() -> None:
    pass
```

## 📝 文档规范

### 代码注释

```python
class PaymentService:
    """支付服务，处理各种支付网关的交互。
    
    该服务封装了支付相关的业务逻辑，包括创建支付、
    验证支付状态和处理支付回调。
    """
    
    async def create_payment(
        self, 
        amount: Money, 
        order_id: str
    ) -> Payment:
        """创建支付订单。
        
        Args:
            amount: 支付金额和货币
            order_id: 关联的订单ID
            
        Returns:
            创建的支付对象
            
        Raises:
            PaymentGatewayError: 支付网关错误
            ValidationError: 参数验证错误
        """
        # 实现逻辑
        pass
```

### README 文档

每个主要模块都应该有 README.md：

```markdown
# 支付模块

此模块处理所有支付相关功能。

## 功能特性

- 多支付网关支持
- 异步支付处理
- 支付状态跟踪

## 使用示例

\`\`\`python
payment_service = PaymentService()
payment = await payment_service.create_payment(
    amount=Money(Decimal("9.99"), "USD"),
    order_id="order_123"
)
\`\`\`
```

## 🔒 安全规范

### 敏感信息处理

```python
# ✅ 正确：使用环境变量
bot_token = settings.bot.token

# ❌ 错误：硬编码敏感信息
bot_token = "123456:ABC-DEF..."
```

### 输入验证

```python
# ✅ 正确：验证用户输入
def validate_telegram_id(telegram_id: str) -> None:
    if not telegram_id.isdigit():
        raise ValidationError("Invalid telegram ID format")
    
    if len(telegram_id) > 20:
        raise ValidationError("Telegram ID too long")

# ❌ 错误：直接使用用户输入
user = User(telegram_id=raw_input)
```

### SQL 注入防护

```python
# ✅ 正确：使用参数化查询
async def get_user_by_id(user_id: str) -> Optional[User]:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# ❌ 错误：字符串拼接
query = f"SELECT * FROM users WHERE id = '{user_id}'"
```

## 🚀 性能规范

### 数据库查询优化

```python
# ✅ 正确：使用预加载避免 N+1 查询
users = await session.execute(
    select(User).options(
        selectinload(User.orders),
        selectinload(User.referrals)
    )
)

# ❌ 错误：可能导致 N+1 查询
users = await session.execute(select(User))
for user in users:
    await user.awaitable_attrs.orders  # 单独查询
```

### 异步操作

```python
# ✅ 正确：使用 asyncio.gather 并发执行
user_task = user_service.get_user(user_id)
orders_task = order_service.get_user_orders(user_id)
user, orders = await asyncio.gather(user_task, orders_task)

# ❌ 错误：顺序执行
user = await user_service.get_user(user_id)
orders = await order_service.get_user_orders(user_id)
```

## 🐛 错误处理规范

### 异常处理

```python
# ✅ 正确：具体的异常类型
try:
    user = await user_service.create_user(command)
except UserAlreadyExistsError:
    logger.warning(f"User {command.telegram_id} already exists")
    raise
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise InternalServerError("User creation failed")

# ❌ 错误：捕获所有异常
try:
    user = await user_service.create_user(command)
except Exception:
    pass  # 不处理异常
```

### 日志记录

```python
# ✅ 正确：结构化日志
logger.info(
    "User created successfully",
    extra={
        "user_id": user.id,
        "telegram_id": user.telegram_id,
        "operation": "create_user"
    }
)

# ❌ 错误：简单字符串日志
logger.info(f"User {user.id} created")
```

## 📦 依赖管理

### Poetry 依赖

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.12"
aiogram = "^3.15.0"  # 指定具体版本范围

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^24.0.0"
```

### 导入规范

```python
# 标准库导入
import asyncio
import logging
from datetime import datetime
from typing import Optional, List

# 第三方库导入
from aiogram import Bot, Dispatcher
from sqlalchemy import select

# 本地导入
from src.domain.entities.user import User
from src.application.services.user_service import UserService
```

## ✅ Git 提交规范

### 提交消息格式

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### 提交类型

- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式修改
- `refactor`: 重构代码
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

### 示例

```
feat(payment): add Cryptomus payment gateway support

- Implement PaymentGateway interface
- Add webhook handling for payment callbacks
- Include payment status validation

Closes #123
```

## 🔄 代码审查清单

提交代码前请检查：

- [ ] 代码遵循项目规范
- [ ] 所有测试通过
- [ ] 代码覆盖率满足要求
- [ ] 无安全漏洞
- [ ] 性能影响评估
- [ ] 文档已更新
- [ ] 依赖项合理

## 📚 参考资源

- [PEP 8 - Python 代码风格指南](https://peps.python.org/pep-0008/)
- [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)
- [Domain-Driven Design Reference](https://domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

💡 **提示**: 使用 pre-commit hooks 自动检查代码规范，确保每次提交都符合标准！