# Scripts Directory

项目工具脚本目录，包含部署、监控和维护相关的实用工具。

## 📁 脚本列表

### 🚀 部署和安装

- **`setup.sh`** - 自动安装脚本，设置开发环境
- **`docker_deploy.sh`** - Docker 容器化部署脚本
- **`start.sh`** - 容器启动脚本（Docker 内部使用）

### 🔍 监控和健康检查

- **`healthcheck.sh`** - 服务健康检查脚本
- **`check_services.py`** - 全面的服务状态检查工具

### 🗃️ 数据库

- **`init-db.sql`** - 数据库初始化脚本

## 🛠️ 使用说明

### 开发环境设置

```bash
# 一键设置开发环境
./scripts/setup.sh
```

### 生产环境部署

```bash
# Docker 部署
./scripts/docker_deploy.sh
```

### 服务监控

```bash
# 健康检查
./scripts/healthcheck.sh

# 详细服务状态
python3 scripts/check_services.py
```

## ⚠️ 注意事项

- 所有脚本都应在项目根目录执行
- 确保具有适当的执行权限：`chmod +x scripts/*.sh`
- 生产环境部署前请仔细检查配置文件

## 🔧 脚本维护

如需添加新的脚本，请遵循以下规范：

1. **命名规范**：使用描述性的名称，如 `action_target.sh`
2. **文档说明**：在脚本头部添加清晰的注释说明
3. **错误处理**：使用 `set -e` 确保错误时退出
4. **日志输出**：提供清晰的进度和错误信息
5. **更新README**：添加新脚本后更新此文档