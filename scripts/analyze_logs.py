#!/usr/bin/env python3
"""
简化的日志分析脚本 - 专门针对常见错误类型
"""

import re
from collections import Counter
from pathlib import Path


def analyze_log_errors(log_file: str):
    """分析日志文件中的错误"""
    
    print(f"📊 分析日志文件: {log_file}")
    print("=" * 60)
    
    # 错误统计
    postgres_errors = []
    migration_errors = []
    foreign_key_errors = []
    all_errors = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 检查是否为错误行
                if any(keyword in line.upper() for keyword in ['ERROR', 'CRITICAL', 'FATAL']):
                    all_errors.append((line_num, line))
                    
                    # 分类错误
                    if 'postgres' in line and 'ERROR:' in line:
                        postgres_errors.append(line)
                    
                    if 'migration' in line.lower() and 'error' in line.lower():
                        migration_errors.append(line)
                    
                    if 'foreign key' in line.lower():
                        foreign_key_errors.append(line)
    
    except FileNotFoundError:
        print(f"❌ 文件不存在: {log_file}")
        return
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")
        return
    
    # 统计结果
    print(f"📈 错误统计:")
    print(f"  总错误数: {len(all_errors)}")
    print(f"  PostgreSQL错误: {len(postgres_errors)}")
    print(f"  数据库迁移错误: {len(migration_errors)}")
    print(f"  外键约束错误: {len(foreign_key_errors)}")
    print()
    
    # 分析PostgreSQL错误
    if postgres_errors:
        print("🔍 PostgreSQL错误详情:")
        postgres_error_types = Counter()
        for error in postgres_errors:
            if 'foreign key constraint' in error:
                postgres_error_types['外键约束错误'] += 1
            elif 'transaction is aborted' in error:
                postgres_error_types['事务中止错误'] += 1
            else:
                postgres_error_types['其他数据库错误'] += 1
        
        for error_type, count in postgres_error_types.items():
            print(f"  {error_type}: {count}次")
        print()
    
    # 分析最频繁的错误
    if foreign_key_errors:
        print("🚨 外键约束错误分析:")
        fk_patterns = Counter()
        for error in foreign_key_errors:
            # 提取外键名称
            match = re.search(r'foreign key constraint "([^"]+)"', error)
            if match:
                fk_name = match.group(1)
                fk_patterns[fk_name] += 1
        
        print("  问题外键:")
        for fk_name, count in fk_patterns.most_common(5):
            print(f"    {fk_name}: {count}次")
        print()
    
    # 显示最近的几个错误
    if all_errors:
        print("📋 最近的错误 (最后5条):")
        for i, (line_num, error) in enumerate(all_errors[-5:], 1):
            error_preview = error[:100] + "..." if len(error) > 100 else error
            print(f"  {i}. 行{line_num}: {error_preview}")
        print()
    
    # 给出修复建议
    print("💡 修复建议:")
    if foreign_key_errors:
        print("  1. 外键约束错误:")
        print("     - 检查用户表的referrer_id字段定义")
        print("     - 确保外键引用的表和字段存在且类型匹配")
        print("     - 可能需要重新设计数据库迁移脚本")
    
    if migration_errors:
        print("  2. 数据库迁移错误:")
        print("     - 停止当前迁移进程")
        print("     - 检查数据库连接状态")
        print("     - 清理失败的迁移记录")
        print("     - 重新运行迁移")
    
    print("  3. 通用建议:")
    print("     - 备份数据库后重置迁移状态")
    print("     - 检查数据库模型定义的一致性")
    print("     - 运行数据库完整性检查")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python3 analyze_logs.py <日志文件路径>")
        print("示例: python3 analyze_logs.py logs/log.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    analyze_log_errors(log_file)


if __name__ == '__main__':
    main()