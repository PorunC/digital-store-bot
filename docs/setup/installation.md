# 安装指南

本指南将详细介绍如何在不同环境中安装和配置 Digital Store Bot v2。

## 📋 系统要求

### 硬件要求
- **内存**: 最低 2GB，推荐 4GB+
- **存储**: 最低 10GB 可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **Python**: 3.12 或更高版本
- **Poetry**: 1.7 或更高版本
- **Docker**: 20.10+ (可选，用于容器部署)
- **Git**: 2.30+ (用于克隆代码)

## 🚀 安装方法

### 方法 1: 自动安装脚本 (推荐)

```bash
# 克隆项目
git clone https://github.com/your-org/digital-store-bot-v2.git
cd digital-store-bot-v2

# 运行自动安装脚本
./scripts/setup.sh
```

### 方法 2: 手动安装

#### 步骤 1: 安装 Python 依赖

```bash
# 安装 Poetry (如果未安装)
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install
```

#### 步骤 2: 配置环境

```bash
# 复制配置模板
cp config/settings.example.yml config/settings.yml

# 编辑配置文件
nano config/settings.yml
```

#### 步骤 3: 数据库设置

```bash
# 运行数据库迁移
poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade
```

#### 步骤 4: 启动服务

```bash
# 开发模式启动
poetry run python -m src.main --dev

# 生产模式启动
poetry run python -m src.main
```

### 方法 3: Docker 安装

```bash
# 克隆项目
git clone https://github.com/your-org/digital-store-bot-v2.git
cd digital-store-bot-v2

# 配置环境变量
cp .env.example .env
nano .env

# 使用 Docker Compose 启动
docker compose up -d
```

## ⚙️ 必要配置

### Bot Token 配置

1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
2. 创建新的机器人并获取 Token
3. 在 `config/settings.yml` 中设置：

```yaml
bot:
  token: "YOUR_BOT_TOKEN_HERE"
  admin_ids: [YOUR_TELEGRAM_USER_ID]
```

### 数据库配置 (可选)

默认使用 SQLite，生产环境建议使用 PostgreSQL：

```yaml
database:
  url: "postgresql+asyncpg://user:password@localhost/digital_store"
```

### 支付网关配置 (可选)

配置 Cryptomus 支付网关：

```yaml
payments:
  cryptomus:
    enabled: true
    merchant_id: "your_merchant_id"
    api_key: "your_api_key"
```

## 🧪 验证安装

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行快速测试
poetry run pytest -m "not slow"
```

### 检查服务状态

```bash
# 健康检查
./scripts/healthcheck.sh

# 详细服务检查
python3 scripts/check_services.py
```

## 🔧 常见问题

### Poetry 安装失败

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv

# macOS
brew install python@3.12
```

### 数据库连接错误

1. 检查数据库 URL 配置
2. 确保数据库服务运行中
3. 验证连接权限

### 机器人无响应

1. 验证 Bot Token 正确性
2. 检查网络连接
3. 查看日志文件 `logs/app.log`

## 📚 下一步

安装完成后，建议阅读：

- [配置文档](../configuration/CONFIG_DOCUMENTATION.md) - 详细配置说明
- [用户指南](user-guide.md) - 功能使用指南
- [管理员指南](admin-guide.md) - 管理功能说明

## 🆘 获取帮助

如果遇到安装问题：

1. 查看 [FAQ](faq.md)
2. 搜索 [Issues](https://github.com/your-org/digital-store-bot-v2/issues)
3. 在 [讨论区](https://github.com/your-org/digital-store-bot-v2/discussions) 提问