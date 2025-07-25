# Docker 重启脚本集合

这个目录包含了用于重启Docker服务时保持Traefik容器运行的脚本集合。这些脚本特别适用于生产环境，确保反向代理服务不会中断。

## 脚本概览

### 1. `quick_restart.sh` - 快速重启脚本 ⚡

最简单的重启脚本，适用于开发和测试环境。

```bash
# 快速重启所有服务（保持Traefik运行）
./scripts/quick_restart.sh
```

**特点:**
- 一键重启所有非Traefik服务
- 无需参数，开箱即用
- 显示重启前后的状态对比

### 2. `restart_without_traefik.sh` - 标准重启脚本 🔄

功能丰富的重启脚本，支持多种选项和服务组合。

```bash
# 重启所有服务（除Traefik）
./scripts/restart_without_traefik.sh --all

# 只重启应用服务
./scripts/restart_without_traefik.sh --app

# 重启数据库服务
./scripts/restart_without_traefik.sh --db

# 重启监控服务
./scripts/restart_without_traefik.sh --monitoring

# 重新构建并重启应用服务
./scripts/restart_without_traefik.sh --app --build
```

**支持的选项:**
- `--all`: 重启所有服务（除Traefik）
- `--app`: 重启应用服务 (bot, admin, scheduler)
- `--db`: 重启数据库服务 (postgres, redis)
- `--monitoring`: 重启监控服务 (prometheus, grafana, loki, promtail)
- `--build`: 重新构建Docker镜像
- `--help`: 显示帮助信息

**特点:**
- 支持服务分组重启
- 健康检查和状态监控
- 详细的日志输出
- 操作确认机制

### 3. `docker_manager.sh` - 高级管理脚本 🚀

最功能完整的Docker服务管理脚本，支持多种重启策略和维护操作。

```bash
# 标准重启
./scripts/docker_manager.sh restart --app

# 滚动重启（逐个重启服务）
./scripts/docker_manager.sh rolling --all --build

# 零停机重启（需要Traefik运行）
./scripts/docker_manager.sh zero-downtime --app

# 显示详细状态
./scripts/docker_manager.sh status

# 备份Traefik配置
./scripts/docker_manager.sh backup

# 清理和维护
./scripts/docker_manager.sh cleanup
```

**支持的命令:**
- `restart`: 标准重启（保持Traefik）
- `rolling`: 滚动重启（逐个重启服务）
- `zero-downtime`: 零停机重启（需要Traefik）
- `status`: 显示详细状态
- `backup`: 备份Traefik和配置
- `cleanup`: 清理和维护
- `help`: 显示帮助

**支持的选项:**
- `--all`: 操作所有服务（除Traefik）
- `--app`: 仅应用服务 (bot, admin, scheduler)
- `--db`: 仅数据库服务 (postgres, redis)
- `--monitoring`: 仅监控服务 (prometheus, grafana)
- `--build`: 重新构建镜像
- `--include-traefik`: 包含Traefik（谨慎使用）
- `--debug`: 启用调试输出

**高级特性:**
- 🔄 滚动重启：逐个重启服务，最小化停机时间
- ⚡ 零停机重启：通过负载均衡实现零停机部署
- 💾 自动备份：重启前自动备份Traefik配置和证书
- 📊 详细监控：显示容器状态、资源使用、网络信息
- 🧹 自动清理：清理未使用的容器、镜像、网络
- 📝 完整日志：所有操作都记录到日志文件

## 使用场景

### 开发环境
```bash
# 快速重启进行测试
./scripts/quick_restart.sh
```

### 生产环境
```bash
# 标准重启（安全可靠）
./scripts/restart_without_traefik.sh --app

# 零停机部署
./scripts/docker_manager.sh zero-downtime --app --build
```

### 维护操作
```bash
# 查看系统状态
./scripts/docker_manager.sh status

# 备份配置
./scripts/docker_manager.sh backup

# 清理系统
./scripts/docker_manager.sh cleanup
```

## 安全注意事项

1. **Traefik保护**: 所有脚本默认都会保护Traefik容器不被重启
2. **操作确认**: 关键操作前会要求用户确认
3. **自动备份**: 重启前自动备份重要配置
4. **健康检查**: 等待服务健康检查通过才完成重启

## 环境变量

### `docker_manager.sh` 支持的环境变量:
```bash
# 启用调试模式
export DEBUG=true

# 清理时包含Docker卷（谨慎使用）
export PRUNE_VOLUMES=true
```

## 日志和备份

- **日志文件**: `logs/docker_manager.log`
- **备份目录**: `backups/containers/`
- **自动清理**: 保留最近7天的备份文件

## 故障排除

### 1. 权限问题
```bash
chmod +x scripts/*.sh
```

### 2. Docker未运行
```bash
sudo systemctl start docker
```

### 3. Compose命令问题
脚本会自动检测并使用可用的compose命令：
- `docker compose` (推荐)
- `docker-compose` (兼容)

### 4. 健康检查超时
```bash
# 检查容器日志
docker logs <container_name>

# 手动检查服务状态
docker ps
```

## 最佳实践

1. **生产环境**: 使用 `docker_manager.sh` 的零停机或滚动重启
2. **开发环境**: 使用 `quick_restart.sh` 快速测试
3. **定期维护**: 定期运行 `docker_manager.sh cleanup`
4. **监控状态**: 使用 `docker_manager.sh status` 监控系统健康
5. **备份策略**: 重要操作前运行 `docker_manager.sh backup`

## 脚本选择指南

| 需求 | 推荐脚本 | 命令示例 |
|------|----------|----------|
| 快速开发测试 | `quick_restart.sh` | `./scripts/quick_restart.sh` |
| 生产环境重启 | `restart_without_traefik.sh` | `./scripts/restart_without_traefik.sh --app` |
| 零停机部署 | `docker_manager.sh` | `./scripts/docker_manager.sh zero-downtime --app` |
| 系统维护 | `docker_manager.sh` | `./scripts/docker_manager.sh cleanup` |
| 状态监控 | `docker_manager.sh` | `./scripts/docker_manager.sh status` |

---

**注意**: 这些脚本专为保护Traefik容器而设计。如果需要重启Traefik，请使用 `--include-traefik` 选项（仅限 `docker_manager.sh`）或手动操作。