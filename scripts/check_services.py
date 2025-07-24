#!/usr/bin/env python3
"""
服务状态检查脚本
检查Docker服务和数据库连接状态
"""

import subprocess
import sys
import time
from typing import Dict, Any


def run_command(cmd: str) -> Dict[str, Any]:
    """运行shell命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }


def check_docker_status():
    """检查Docker服务状态"""
    print("🐳 检查Docker服务状态...")
    
    # 检查Docker是否运行
    result = run_command("docker --version")
    if not result['success']:
        print("❌ Docker未安装或未运行")
        return False
    
    print(f"✅ Docker版本: {result['stdout']}")
    
    # 检查Docker Compose服务
    result = run_command("docker compose ps")
    if result['success']:
        print("📋 Docker Compose服务状态:")
        lines = result['stdout'].split('\n')
        for line in lines[1:]:  # 跳过表头
            if line.strip():
                print(f"  {line}")
    else:
        print("❌ 无法获取Docker Compose状态")
        print(f"错误: {result['stderr']}")
    
    return True


def check_database_connection():
    """检查数据库连接"""
    print("\n🗄️  检查数据库连接...")
    
    # 尝试连接PostgreSQL容器
    pg_cmd = """docker exec digital-store-bot-postgres-1 psql -U postgres -d digital_store_bot -c "SELECT version();" """
    
    result = run_command(pg_cmd)
    if result['success']:
        print("✅ 数据库连接成功")
        version_line = result['stdout'].split('\n')[2] if len(result['stdout'].split('\n')) > 2 else "Unknown"
        print(f"📊 数据库版本: {version_line.strip()}")
        return True
    else:
        print("❌ 数据库连接失败")
        print(f"错误: {result['stderr']}")
        
        # 尝试启动服务
        print("🔄 尝试启动数据库服务...")
        start_result = run_command("docker compose up -d postgres")
        if start_result['success']:
            print("✅ 数据库服务启动命令执行完成")
            print("⏳ 等待数据库启动...")
            time.sleep(5)
            
            # 重新检查连接
            retry_result = run_command(pg_cmd)
            if retry_result['success']:
                print("✅ 数据库重新连接成功")
                return True
            else:
                print("❌ 数据库仍然无法连接")
                return False
        else:
            print("❌ 无法启动数据库服务")
            return False


def check_migration_status():
    """检查迁移状态"""
    print("\n📋 检查数据库迁移状态...")
    
    query_cmd = """docker exec digital-store-bot-postgres-1 psql -U postgres -d digital_store_bot -c "SELECT id, success, error_message FROM schema_migrations ORDER BY applied_at DESC LIMIT 3;" """
    
    result = run_command(query_cmd)
    if result['success']:
        print("📊 最近的迁移记录:")
        lines = result['stdout'].split('\n')
        for line in lines[2:-1]:  # 跳过表头和底部
            if line.strip() and not line.startswith('-'):
                print(f"  {line}")
        return True
    else:
        print("❌ 无法查询迁移状态")
        print(f"错误: {result['stderr']}")
        return False


def check_error_logs():
    """检查错误日志"""
    print("\n📝 检查最近的错误日志...")
    
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        log_path = "logs/log.log"
        tail_cmd = f"tail -20 {log_path}"
        
        result = run_command(tail_cmd)
        if result['success']:
            print("📋 最近20行日志:")
            for line in result['stdout'].split('\n')[-10:]:
                if 'ERROR' in line or 'error' in line:
                    print(f"  ❌ {line}")
                elif line.strip():
                    print(f"  ℹ️  {line}")
        else:
            print("❌ 无法读取日志文件")


def main():
    """主函数"""
    print("🔍 Digital Store Bot 服务状态检查")
    print("=" * 50)
    
    checks = [
        ("Docker服务", check_docker_status),
        ("数据库连接", check_database_connection),
        ("迁移状态", check_migration_status),
        ("错误日志", check_error_logs)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} 检查失败: {e}")
            all_passed = False
        
        print()  # 空行分隔
    
    print("=" * 50)
    if all_passed:
        print("🎉 所有检查通过！")
        print("\n💡 建议下一步:")
        print("  1. 运行数据库修复脚本: python3 scripts/fix_database_errors.py")
        print("  2. 重新启动应用: docker compose up -d")
    else:
        print("⚠️  发现问题，请检查上述错误信息")
        print("\n💡 常见解决方案:")
        print("  1. 启动Docker服务: sudo systemctl start docker")
        print("  2. 启动应用服务: docker compose up -d")
        print("  3. 查看详细日志: docker compose logs")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 用户中断检查")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 检查过程异常: {e}")
        sys.exit(1)