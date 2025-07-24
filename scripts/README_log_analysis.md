# 日志分析工具使用指南

本目录包含了两个用于分析和过滤日志错误的Python脚本。

## 📁 脚本文件

### 1. `filter_errors.py` - 完整的日志错误分析工具

功能强大的日志错误分析脚本，支持多种过滤条件和导出功能。

**主要功能：**
- 解析多种格式的错误日志
- 按错误级别、来源、关键词过滤
- 统计错误分布和频率
- 导出结果到JSON文件
- 详细的错误分析报告

**使用方法：**

```bash
# 基本用法 - 分析所有错误
python3 scripts/filter_errors.py logs/log.log

# 过滤特定关键词的错误
python3 scripts/filter_errors.py logs/log.log --keyword "foreign key"

# 按错误级别过滤
python3 scripts/filter_errors.py logs/log.log --level ERROR

# 按来源过滤
python3 scripts/filter_errors.py logs/log.log --source postgres

# 导出结果到JSON文件
python3 scripts/filter_errors.py logs/log.log --export error_report.json

# 静默模式（只显示统计信息）
python3 scripts/filter_errors.py logs/log.log --quiet

# 去重功能 - 去掉时间戳等动态内容后去重
python3 scripts/filter_errors.py logs/log.log --deduplicate

# 去重并导出（包含出现次数统计）
python3 scripts/filter_errors.py logs/log.log --deduplicate --export deduplicated_errors.json

# 只导出去重后的错误
python3 scripts/filter_errors.py logs/log.log --dedup-only --export unique_errors.json

# 组合使用多个过滤条件
python3 scripts/filter_errors.py logs/log.log --keyword "migration" --level ERROR --export migration_errors.json
```

**命令行参数：**
- `log_file`: 日志文件路径（必需）
- `--level`: 过滤错误级别 (ERROR, CRITICAL, FATAL)
- `--source`: 过滤错误来源
- `--keyword`: 过滤包含关键词的错误
- `--export`: 导出结果到JSON文件
- `--deduplicate, -d`: 对错误进行去重（去掉时间戳等动态内容）
- `--dedup-only`: 只导出去重后的错误
- `--quiet`: 静默模式，只显示统计信息

### 2. `analyze_logs.py` - 简化的日志分析工具

专门针对常见错误类型的简化分析工具，更直观易用。

**主要功能：**
- 快速识别PostgreSQL错误
- 分析数据库迁移错误
- 外键约束错误专项分析
- 提供针对性的修复建议

**使用方法：**

```bash
# 分析日志文件
python3 scripts/analyze_logs.py logs/log.log
```

## 📊 输出示例

### filter_errors.py 输出示例：

```
============================================================
日志错误分析报告
============================================================
日志文件: logs/log.log
分析时间: 2025-07-23 18:47:35
总错误数: 621

📊 错误级别分布:
  ERROR: 621

🔍 错误来源分布:
  postgres: 138
  unknown: 483

📝 错误类型分布:
  外键约束错误: 276
  其他错误: 345

🔄 去重统计:
  原始错误数: 621
  去重后错误数: 9
  减少百分比: 98.5%

🔁 高频重复错误 (前5):
  1. [69次] foreign key constraint "users_referrer_id_fkey" cannot be implemented...
  2. [69次] current transaction is aborted, commands ignored until end of transaction block...

🔥 高频错误消息 (前10):
  1. [69次] foreign key constraint "users_referrer_id_fkey" cannot be implemented...
  2. [69次] current transaction is aborted, commands ignored until end of transaction block...
```

### analyze_logs.py 输出示例：

```
📊 分析日志文件: logs/log.log
============================================================
📈 错误统计:
  总错误数: 621
  PostgreSQL错误: 138
  数据库迁移错误: 345
  外键约束错误: 276

🚨 外键约束错误分析:
  问题外键:
    users_referrer_id_fkey: 69次

💡 修复建议:
  1. 外键约束错误:
     - 检查用户表的referrer_id字段定义
     - 确保外键引用的表和字段存在且类型匹配
```

## 🔧 常见用例

### 1. 快速错误概览
```bash
python3 scripts/analyze_logs.py logs/log.log
```

### 2. 深入分析特定错误
```bash
python3 scripts/filter_errors.py logs/log.log --keyword "foreign key" --export fk_errors.json
```

### 3. 监控PostgreSQL错误
```bash
python3 scripts/filter_errors.py logs/log.log --source postgres
```

### 4. 查找迁移相关错误
```bash
python3 scripts/filter_errors.py logs/log.log --keyword "migration"
```

### 5. 导出完整错误报告
```bash
python3 scripts/filter_errors.py logs/log.log --export full_error_report.json
```

### 6. 去重分析（推荐用于大量重复错误）
```bash
# 快速去重分析
python3 scripts/filter_errors.py logs/log.log --deduplicate

# 去重并导出详细统计
python3 scripts/filter_errors.py logs/log.log --deduplicate --export dedup_analysis.json
```

## 🎯 针对当前问题的建议

基于日志分析结果，当前主要问题是：

**外键约束错误：`users_referrer_id_fkey`**
- 出现频率：69次
- 影响：数据库迁移失败
- 建议修复步骤：
  1. 检查用户表结构
  2. 修复外键约束定义
  3. 重新运行数据库迁移

**使用以下命令获取详细信息：**
```bash
# 分析外键约束错误（去重版本）
python3 scripts/filter_errors.py logs/log.log --keyword "users_referrer_id_fkey" --deduplicate --export fk_analysis.json

# 快速查看去重后的错误概要
python3 scripts/filter_errors.py logs/log.log --deduplicate --quiet
```

## 📝 注意事项

1. **权限要求**：确保脚本有读取日志文件的权限
2. **内存使用**：大型日志文件可能消耗较多内存
3. **编码处理**：脚本会自动处理编码问题，忽略无法解码的字符
4. **时间格式**：支持多种时间戳格式的自动识别

## 🔄 定期使用建议

建议将这些脚本整合到日常运维流程中：

1. **每日检查**：使用 `analyze_logs.py` 快速检查错误状态
2. **详细分析**：发现问题时使用 `filter_errors.py` 深入分析
3. **趋势跟踪**：定期导出JSON报告，跟踪错误趋势
4. **自动化**：可以通过cron job等工具定期运行分析