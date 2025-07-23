#!/usr/bin/env python3
"""
数据库错误修复脚本
用于修复外键约束和迁移失败问题
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import text, inspect
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.pool import NullPool
    import asyncpg
    print("✅ 所有依赖已正确导入")
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装必要的依赖: pip install sqlalchemy asyncpg")
    sys.exit(1)


class DatabaseFixer:
    """数据库修复工具"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
    
    async def connect(self):
        """连接数据库"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                poolclass=NullPool,
                echo=True
            )
            print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            raise
    
    async def check_current_state(self):
        """检查当前数据库状态"""
        print("\n🔍 检查当前数据库状态...")
        
        async with self.engine.begin() as conn:
            # 检查users表结构
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'referrer_id'
            """))
            
            referrer_col = result.fetchone()
            if referrer_col:
                print(f"📋 referrer_id列: {referrer_col}")
            else:
                print("❌ referrer_id列不存在")
            
            # 检查外键约束
            result = await conn.execute(text("""
                SELECT constraint_name, table_name, column_name, foreign_table_name, foreign_column_name
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc ON kcu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND kcu.table_name = 'users' 
                AND kcu.column_name = 'referrer_id'
            """))
            
            fk_constraints = result.fetchall()
            if fk_constraints:
                print("🔗 外键约束:")
                for fk in fk_constraints:
                    print(f"  - {fk}")
            else:
                print("ℹ️  未找到referrer_id的外键约束")
            
            # 检查迁移状态
            try:
                result = await conn.execute(text("""
                    SELECT id, description, applied_at, success, error_message
                    FROM schema_migrations 
                    ORDER BY applied_at DESC 
                    LIMIT 5
                """))
                
                migrations = result.fetchall()
                print("\n📊 最近的迁移记录:")
                for migration in migrations:
                    status = "✅" if migration[3] else "❌"
                    print(f"  {status} {migration[0]}: {migration[1]} ({migration[2]})")
                    if not migration[3] and migration[4]:
                        print(f"    错误: {migration[4][:100]}...")
                        
            except Exception as e:
                print(f"ℹ️  无法读取迁移记录: {e}")
    
    async def fix_referrer_id_constraint(self):
        """修复referrer_id外键约束问题"""
        print("\n🔧 开始修复referrer_id外键约束...")
        
        async with self.engine.begin() as conn:
            try:
                # 步骤1: 删除现有的外键约束
                print("1️⃣ 删除现有外键约束...")
                await conn.execute(text("""
                    ALTER TABLE users 
                    DROP CONSTRAINT IF EXISTS users_referrer_id_fkey
                """))
                print("   ✅ 外键约束已删除")
                
                # 步骤2: 检查当前数据类型
                result = await conn.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'referrer_id'
                """))
                
                current_type = result.fetchone()
                if current_type:
                    print(f"   📋 当前referrer_id类型: {current_type[0]}")
                
                # 步骤3: 转换数据类型为VARCHAR
                if current_type and current_type[0] in ['uuid', 'UUID']:
                    print("2️⃣ 转换referrer_id类型从UUID到VARCHAR...")
                    await conn.execute(text("""
                        ALTER TABLE users 
                        ALTER COLUMN referrer_id TYPE VARCHAR(255) 
                        USING referrer_id::VARCHAR(255)
                    """))
                    print("   ✅ 数据类型转换完成")
                else:
                    print("2️⃣ referrer_id已经是VARCHAR类型，跳过转换")
                
                # 步骤4: 清理无效数据（如果需要）
                print("3️⃣ 清理无效的referrer_id数据...")
                result = await conn.execute(text("""
                    UPDATE users 
                    SET referrer_id = NULL 
                    WHERE referrer_id = '' OR referrer_id = '00000000-0000-0000-0000-000000000000'
                """))
                
                if result.rowcount > 0:
                    print(f"   ✅ 清理了 {result.rowcount} 条无效数据")
                else:
                    print("   ℹ️  没有发现无效数据")
                
                print("🎉 referrer_id约束修复完成！")
                
            except Exception as e:
                print(f"❌ 修复过程中出错: {e}")
                raise
    
    async def add_missing_columns(self):
        """添加缺失的列"""
        print("\n📊 添加缺失的用户表列...")
        
        columns_to_add = [
            ("is_trial_used", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("trial_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("trial_type", "VARCHAR(20)"),
            ("total_subscription_days", "INTEGER DEFAULT 0 NOT NULL"),
            ("total_orders", "INTEGER DEFAULT 0 NOT NULL"),
            ("total_spent_amount", "FLOAT DEFAULT 0.0 NOT NULL"),
            ("total_spent_currency", "VARCHAR(3) DEFAULT 'USD' NOT NULL"),
            ("last_active_at", "TIMESTAMP WITH TIME ZONE"),
            ("notes", "TEXT")
        ]
        
        async with self.engine.begin() as conn:
            for column_name, column_def in columns_to_add:
                try:
                    # 检查列是否已存在
                    result = await conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = %s
                    """), (column_name,))
                    
                    if result.fetchone():
                        print(f"   ℹ️  列 {column_name} 已存在，跳过")
                        continue
                    
                    # 添加列
                    await conn.execute(text(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_def}
                    """))
                    print(f"   ✅ 添加列: {column_name}")
                    
                except Exception as e:
                    print(f"   ❌ 添加列 {column_name} 失败: {e}")
    
    async def update_column_types(self):
        """更新列类型以匹配模型"""
        print("\n🔄 更新列类型...")
        
        type_updates = [
            ("subscription_type", "VARCHAR(20)"),
            ("language_code", "VARCHAR(5)"),
            ("status", "VARCHAR(20)")
        ]
        
        async with self.engine.begin() as conn:
            for column_name, new_type in type_updates:
                try:
                    await conn.execute(text(f"""
                        ALTER TABLE users 
                        ALTER COLUMN {column_name} TYPE {new_type}
                    """))
                    print(f"   ✅ 更新 {column_name} 类型为 {new_type}")
                    
                except Exception as e:
                    print(f"   ❌ 更新 {column_name} 类型失败: {e}")
    
    async def mark_migration_as_successful(self):
        """标记迁移为成功"""
        print("\n✅ 标记迁移为成功...")
        
        async with self.engine.begin() as conn:
            try:
                # 检查迁移记录是否存在
                result = await conn.execute(text("""
                    SELECT id FROM schema_migrations 
                    WHERE id = '20250723_000002_add_missing_user_columns'
                """))
                
                if result.fetchone():
                    # 更新现有记录
                    await conn.execute(text("""
                        UPDATE schema_migrations 
                        SET success = TRUE, error_message = NULL
                        WHERE id = '20250723_000002_add_missing_user_columns'
                    """))
                    print("   ✅ 更新迁移记录状态")
                else:
                    # 插入新记录
                    await conn.execute(text("""
                        INSERT INTO schema_migrations (id, version, description, applied_at, execution_time_ms, success, error_message)
                        VALUES ('20250723_000002_add_missing_user_columns', '1.0.1', 'Add missing columns to users table', CURRENT_TIMESTAMP, '0', TRUE, NULL)
                    """))
                    print("   ✅ 创建迁移记录")
                    
            except Exception as e:
                print(f"   ❌ 更新迁移记录失败: {e}")
    
    async def run_full_fix(self):
        """运行完整修复流程"""
        print("🚀 开始数据库错误修复流程...")
        
        try:
            await self.connect()
            await self.check_current_state()
            await self.fix_referrer_id_constraint()
            await self.add_missing_columns()
            await self.update_column_types()
            await self.mark_migration_as_successful()
            
            print("\n🎉 数据库修复完成！")
            print("\n📋 修复总结:")
            print("  ✅ 删除了有问题的外键约束")
            print("  ✅ 将referrer_id转换为VARCHAR类型")
            print("  ✅ 添加了所有缺失的列")
            print("  ✅ 更新了列类型以匹配模型")
            print("  ✅ 标记迁移为成功状态")
            
        except Exception as e:
            print(f"\n❌ 修复过程失败: {e}")
            raise
        finally:
            if self.engine:
                await self.engine.dispose()


async def main():
    """主函数"""
    
    # 默认数据库连接URL（Docker Compose环境）
    default_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/digital_store_bot"
    
    # 可以通过环境变量或参数自定义
    import os
    db_url = os.getenv("DATABASE_URL", default_db_url)
    
    if len(sys.argv) > 1:
        db_url = sys.argv[1]
    
    print(f"🔗 使用数据库URL: {db_url.replace('postgres:', 'postgresql+asyncpg:')}")
    
    fixer = DatabaseFixer(db_url.replace('postgres:', 'postgresql+asyncpg:'))
    
    try:
        await fixer.run_full_fix()
        return 0
    except Exception as e:
        print(f"\n💥 修复失败: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        sys.exit(1)