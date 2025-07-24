# Digital Store Bot v2

🤖 **高性能 Telegram 数字商店机器人** - 基于领域驱动设计的企业级电商解决方案

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Poetry](https://img.shields.io/badge/Poetry-1.7+-green.svg)](https://python-poetry.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](docker-compose.yml)

## ✨ 特性概览

🏪 **完整电商功能** | 🔄 **自动化交付** | 💳 **多支付网关** | 🌐 **多语言支持**

- **数字产品销售** - 自动化库存管理和交付系统
- **多支付网关** - Cryptomus、Telegram Stars 等
- **推荐系统** - 智能推荐和分佣管理
- **试用系统** - 灵活的试用期管理
- **管理面板** - 功能完整的 Web 管理界面
- **高可用部署** - Docker Compose 一键部署

## 🏗️ 架构优势

基于 **Domain-Driven Design (DDD)** 和 **Clean Architecture** 原则构建：

| 核心模式 | 说明 | 优势 |
|---------|------|------|
| **领域驱动设计** | 清晰的业务边界和实体模型 | 业务逻辑清晰，维护性强 |
| **依赖注入** | 自动依赖解析和生命周期管理 | 高度解耦，便于测试 |
| **事件驱动** | 异步事件总线通信 | 松耦合，高性能 |
| **CQRS 模式** | 命令查询职责分离 | 读写分离，性能优化 |
| **六边形架构** | 端口适配器模式 | 技术栈无关，易扩展 |

## 🚀 快速开始

### 方法 1: 一键安装脚本

```bash
# 下载并运行安装脚本
./scripts/setup.sh

# 编辑配置文件
nano config/settings.yml

# 启动服务
poetry run python -m src.main
```

### 方法 2: 手动安装

```bash
# 1. 克隆项目
git clone https://github.com/your-org/digital-store-bot-v2.git
cd digital-store-bot-v2

# 2. 安装依赖
poetry install

# 3. 配置环境
cp config/settings.example.yml config/settings.yml
# 编辑 config/settings.yml，设置 bot.token 和其他必要配置

# 4. 运行数据库迁移
poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade

# 5. 启动服务
poetry run python -m src.main
```

### 方法 3: Docker 部署

```bash
# 1. 克隆项目
git clone https://github.com/your-org/digital-store-bot-v2.git
cd digital-store-bot-v2

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动所有服务
docker compose up -d

# 4. 查看日志
docker compose logs -f bot
```

## 📁 项目结构

```
src/
├── domain/                    # 🏛️ 领域层 - 业务核心逻辑
│   ├── entities/             # 实体对象 (User, Order, Product)
│   ├── value_objects/        # 值对象 (Money, UserProfile)
│   ├── repositories/         # 仓储接口
│   ├── services/             # 领域服务
│   └── events/               # 领域事件
├── application/              # 🔧 应用层 - 业务流程编排
│   ├── commands/             # 命令处理器
│   ├── queries/              # 查询处理器
│   ├── handlers/             # 事件处理器
│   └── services/             # 应用服务
├── infrastructure/           # 🔌 基础设施层 - 技术实现
│   ├── database/             # 数据库和迁移
│   ├── external/             # 支付网关集成
│   ├── background_tasks/     # 后台任务调度
│   └── configuration/        # 配置管理
├── presentation/             # 🖥️ 表现层 - 用户接口
│   ├── telegram/             # Telegram 机器人界面
│   ├── web/                  # Web 管理面板
│   └── webhooks/             # 支付回调处理
└── shared/                   # 🔄 共享组件
    ├── dependency_injection/ # DI 容器
    ├── events/               # 事件总线
    └── exceptions/           # 异常处理
```

## 🛠️ 开发指南

### 常用命令

```bash
# 开发环境运行
poetry run python -m src.main --dev

# 运行测试
poetry run pytest                    # 完整测试
poetry run pytest -m unit           # 单元测试
poetry run pytest -m integration    # 集成测试

# 代码质量检查
poetry run black src tests          # 代码格式化
poetry run isort src tests          # 导入排序
poetry run flake8 src tests         # 代码检查
poetry run mypy src                  # 类型检查

# 数据库操作
poetry run python -m src.infrastructure.database.migrations.migration_manager create "描述"
poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade
```

### 添加新功能

1. **创建领域模型** - 在 `src/domain/` 中定义实体和值对象
2. **定义应用服务** - 在 `src/application/` 中实现业务流程
3. **实现基础设施** - 在 `src/infrastructure/` 中集成外部服务
4. **添加用户界面** - 在 `src/presentation/` 中实现交互逻辑
5. **注册依赖** - 在 `src/main.py` 中配置 DI 容器

## 🔧 配置说明

核心配置文件位于 `config/settings.yml`：

```yaml
bot:
  token: "YOUR_BOT_TOKEN"        # 必需：Telegram Bot Token
  admin_ids: [12345678]          # 必需：管理员用户ID列表

database:
  url: "sqlite+aiosqlite:///data/store.db"  # 数据库连接

payments:
  cryptomus:
    merchant_id: "your_merchant_id"
    api_key: "your_api_key"
    
shop:
  default_currency: "USD"
  trial_period_days: 3
  referral_rate: 0.1
```

详细配置说明请参考 [配置文档](docs/configuration/CONFIG_DOCUMENTATION.md)

## 🚢 部署指南

### 生产环境部署

```bash
# 使用 Docker Compose 部署
docker compose --profile production up -d

# 包含监控的完整部署
docker compose --profile monitoring up -d
```

### 健康检查

```bash
# 检查服务状态
./scripts/healthcheck.sh

# 检查所有组件
./scripts/check_services.py
```

完整部署指南请参考 [部署文档](docs/deployment/DEPLOYMENT_GUIDE.md)

## 📊 监控和维护

- **日志系统** - 结构化日志记录和轮转
- **健康检查** - 自动服务监控和恢复
- **性能监控** - Prometheus + Grafana (可选)
- **错误追踪** - 详细的错误日志和分析工具

## 🧪 测试

```bash
# 运行所有测试
poetry run pytest

# 测试覆盖率报告
poetry run pytest --cov-report=html

# 性能测试
poetry run pytest -m "not slow"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📚 文档导航

- 📖 [完整文档中心](docs/README.md) - 所有文档的入口
- 🚀 [安装指南](docs/setup/installation.md) - 详细安装步骤  
- 👤 [用户指南](docs/setup/user-guide.md) - 功能使用手册
- 👨‍💼 [管理员指南](docs/setup/admin-guide.md) - 系统管理指南
- 🛠️ [开发指南](docs/development/CLAUDE.md) - 开发环境和规范
- ❓ [常见问题](docs/setup/faq.md) - 问题解答和故障排除

## 🆘 支持

- 🐛 [问题反馈](https://github.com/your-org/digital-store-bot-v2/issues)
- 💬 [讨论区](https://github.com/your-org/digital-store-bot-v2/discussions)

---

⭐ 如果这个项目对你有帮助，请给个 Star！