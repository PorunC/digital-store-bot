#!/bin/bash
# Docker部署脚本 - 适用于全新或现有环境

set -e  # 遇到错误立即退出

echo "🚀 Digital Store Bot Docker 部署开始..."
echo "================================================"

# 检查Docker和Docker Compose是否可用
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装或不可用"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose 未安装或不可用"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 停止现有服务（如果有）
echo "🛑 停止现有服务..."
docker compose down --remove-orphans || true

# 清理旧的容器和网络（可选）
echo "🧹 清理旧资源..."
docker compose rm -f || true

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs data config

# 复制配置文件（如果不存在）
if [ ! -f "config/settings.yml" ]; then
    if [ -f "config/settings.example.yml" ]; then
        echo "⚙️ 复制配置文件模板..."
        cp config/settings.example.yml config/settings.yml
        echo "⚠️  请编辑 config/settings.yml 文件，设置你的机器人令牌和其他配置"
    else
        echo "⚠️  配置文件模板不存在，请手动创建 config/settings.yml"
    fi
fi

# 构建并启动服务
echo "🏗️ 构建并启动服务..."
docker compose up -d --build

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 15

# 检查数据库连接
echo "🔍 检查数据库连接..."
max_attempts=12
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker exec digital-store-bot-postgres-1 pg_isready -U postgres -d digital_store_bot &> /dev/null; then
        echo "✅ 数据库连接成功"
        break
    else
        echo "⏳ 等待数据库启动... (尝试 $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ 数据库启动超时"
    echo "📋 查看数据库日志:"
    docker compose logs postgres
    exit 1
fi

# 运行数据库迁移
echo "🗄️ 运行数据库迁移..."
if docker compose exec -T bot python -c "
import asyncio
import sys
sys.path.append('/app')

async def run_migrations():
    try:
        from src.infrastructure.database.migrations.migration_manager import MigrationManager
        from src.infrastructure.configuration.settings import Settings
        
        settings = Settings()
        manager = MigrationManager(settings.database.url)
        
        print('开始运行迁移...')
        result = await manager.upgrade()
        
        if result['errors'] == 0:
            print(f'✅ 迁移完成: {result[\"applied\"]} 个迁移已应用')
            return True
        else:
            print(f'❌ 迁移失败: {result[\"errors\"]} 个错误')
            for migration_result in result['results']:
                if migration_result['status'] == 'error':
                    print(f'错误的迁移: {migration_result[\"migration\"]}')
                    print(f'错误信息: {migration_result[\"error\"]}')
            return False
    except Exception as e:
        print(f'❌ 迁移过程异常: {e}')
        return False

if __name__ == '__main__':
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
" 2>/dev/null; then
    echo "✅ 数据库迁移完成"
else
    echo "⚠️ 迁移可能有问题，检查服务状态..."
fi

# 检查服务状态
echo "📊 检查服务状态..."
docker compose ps

# 检查应用日志
echo "📝 最近的应用日志:"
docker compose logs bot --tail=10

# 输出连接信息
echo ""
echo "🎉 部署完成！"
echo "================================================"
echo "📋 服务状态:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "💡 有用的命令:"
echo "  查看所有日志: docker compose logs"
echo "  查看机器人日志: docker compose logs bot -f"
echo "  查看数据库日志: docker compose logs postgres -f"
echo "  重启服务: docker compose restart"
echo "  停止服务: docker compose down"
echo "  进入容器: docker compose exec bot bash"
echo ""

# 检查是否有错误
if docker compose ps | grep -q "unhealthy\|exited"; then
    echo "⚠️ 发现服务问题，请检查日志:"
    docker compose logs --tail=50
    exit 1
else
    echo "✅ 所有服务运行正常"
fi

echo "🚀 Digital Store Bot 部署完成！"