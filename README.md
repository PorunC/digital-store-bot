# Digital Store Bot v2

一个基于领域驱动设计的高解耦Telegram电商机器人。

## 🏗️ 架构特点

- **领域驱动设计 (DDD)**: 清晰的业务边界
- **依赖注入**: 控制反转，便于测试
- **事件驱动**: 松耦合的服务通信
- **仓储模式**: 数据访问抽象
- **CQRS**: 命令查询分离
- **六边形架构**: 端口适配器模式

## 📁 项目结构

```
digital-store-bot-v2/
├── src/
│   ├── domain/                    # 领域层
│   │   ├── entities/             # 实体
│   │   ├── value_objects/        # 值对象
│   │   ├── repositories/         # 仓储接口
│   │   ├── services/             # 领域服务
│   │   └── events/               # 领域事件
│   ├── application/              # 应用层
│   │   ├── commands/             # 命令处理器
│   │   ├── queries/              # 查询处理器
│   │   ├── handlers/             # 事件处理器
│   │   └── services/             # 应用服务
│   ├── infrastructure/           # 基础设施层
│   │   ├── database/             # 数据库实现
│   │   ├── external/             # 外部服务
│   │   ├── messaging/            # 消息系统
│   │   └── configuration/        # 配置管理
│   ├── presentation/             # 表现层
│   │   ├── telegram/             # Telegram适配器
│   │   ├── web/                  # Web API
│   │   └── cli/                  # 命令行接口
│   └── shared/                   # 共享内核
│       ├── events/               # 事件基础设施
│       ├── dependency_injection/ # DI容器
│       └── exceptions/           # 异常处理
├── tests/                        # 测试
├── config/                       # 配置文件
└── scripts/                      # 工具脚本
```

## 🚀 核心功能

- ✅ 数字产品销售
- ✅ 多支付网关
- ✅ 推荐系统
- ✅ 试用系统
- ✅ 多语言支持
- ✅ 管理面板

## 快速开始

```bash
# 安装依赖
poetry install

# 配置环境
cp config/settings.example.yml config/settings.yml

# 运行测试
pytest

# 启动服务
python -m src.main
```