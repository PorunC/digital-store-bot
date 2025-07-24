#!/usr/bin/env python3
"""
日志错误过滤和分析脚本
用于从日志文件中提取、分类和统计错误信息
"""

import re
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class LogError:
    """表示一个日志错误条目"""
    
    def __init__(self, timestamp: str, level: str, source: str, message: str, line_number: int):
        self.timestamp = timestamp
        self.level = level.upper()
        self.source = source
        self.message = message
        self.line_number = line_number
        self._normalized_message = None
        
    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.level} ({self.source}): {self.message}"
    
    def get_normalized_message(self) -> str:
        """获取标准化的错误消息（去掉时间戳和动态内容）"""
        if self._normalized_message is None:
            self._normalized_message = self._normalize_message(self.message)
        return self._normalized_message
    
    def _normalize_message(self, message: str) -> str:
        """标准化错误消息，去掉时间戳、ID、数值等动态内容"""
        normalized = message
        
        # 去掉时间戳 (YYYY-MM-DD HH:MM:SS.mmm)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\s+\w+)?', '[TIMESTAMP]', normalized)
        
        # 去掉各种ID格式
        normalized = re.sub(r'\[\d+\]', '[ID]', normalized)  # [123]
        normalized = re.sub(r'\bid:\s*\d+\b', 'id: [ID]', normalized, flags=re.IGNORECASE)  # id: 123
        normalized = re.sub(r'\buuid:\s*[a-f0-9-]+\b', 'uuid: [UUID]', normalized, flags=re.IGNORECASE)
        
        # 去掉数值
        normalized = re.sub(r'\b\d+\b', '[NUM]', normalized)
        
        # 去掉文件路径中的具体路径
        normalized = re.sub(r'/[/\w.-]+/', '/[PATH]/', normalized)
        
        # 去掉SQL参数
        normalized = re.sub(r'\[parameters:\s*\([^)]+\)\]', '[parameters: [...]]', normalized)
        
        # 去掉具体的datetime对象
        normalized = re.sub(r'datetime\.datetime\([^)]+\)', 'datetime.datetime([...])', normalized)
        
        # 去掉具体的异常地址
        normalized = re.sub(r'0x[a-f0-9]+', '0x[ADDR]', normalized)
        
        # 去掉SQLAlchemy具体错误URL
        normalized = re.sub(r'https://sqlalche\.me/e/\w+/\w+', 'https://sqlalche.me/e/[CODE]/[ID]', normalized)
        
        # 标准化空白字符
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def get_deduplication_key(self) -> str:
        """获取用于去重的键"""
        return f"{self.level}|{self.source}|{self.get_normalized_message()}"
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'source': self.source,
            'message': self.message,
            'normalized_message': self.get_normalized_message(),
            'line_number': self.line_number
        }


class LogErrorFilter:
    """日志错误过滤器"""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = Path(log_file_path)
        self.errors: List[LogError] = []
        
        # 匹配不同格式的错误日志
        self.error_patterns = [
            # PostgreSQL 错误格式: postgres | 2025-07-23 09:06:29.346 UTC [59] ERROR: message
            re.compile(r'^(\w+)\s+\|\s+([\d-]+\s+[\d:.]+\s+\w+)\s+\[\d+\]\s+(ERROR):\s+(.+)$'),
            # 通用错误格式: [timestamp] ERROR source: message
            re.compile(r'^\[([\d-]+\s+[\d:.]+)\]\s+(ERROR|CRITICAL|FATAL)\s+(\w+):\s+(.+)$'),
            # Python 异常格式
            re.compile(r'^([\d-]+\s+[\d:.]+).*?(ERROR|Exception|Traceback).*?:\s*(.+)$'),
            # 简单错误格式: ERROR: message
            re.compile(r'^(ERROR|CRITICAL|FATAL):\s+(.+)$'),
        ]
    
    def parse_log_file(self) -> None:
        """解析日志文件，提取错误信息"""
        if not self.log_file_path.exists():
            raise FileNotFoundError(f"日志文件不存在: {self.log_file_path}")
        
        with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否包含错误关键词
                if not any(keyword in line.upper() for keyword in ['ERROR', 'CRITICAL', 'FATAL', 'EXCEPTION']):
                    continue
                
                error = self._parse_error_line(line, line_num)
                if error:
                    self.errors.append(error)
    
    def _parse_error_line(self, line: str, line_num: int) -> Optional[LogError]:
        """解析单行错误日志"""
        for pattern in self.error_patterns:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                
                if len(groups) == 4:  # PostgreSQL 格式
                    source, timestamp, level, message = groups
                    return LogError(timestamp, level, source, message, line_num)
                elif len(groups) == 4:  # 通用格式
                    timestamp, level, source, message = groups
                    return LogError(timestamp, level, source, message, line_num)
                elif len(groups) == 3:  # Python异常格式
                    timestamp, level, message = groups
                    return LogError(timestamp, level, 'python', message, line_num)
                elif len(groups) == 2:  # 简单格式
                    level, message = groups
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return LogError(timestamp, level, 'unknown', message, line_num)
        
        # 如果没有匹配到模式，但包含错误关键词，创建通用错误
        if any(keyword in line.upper() for keyword in ['ERROR', 'CRITICAL', 'FATAL']):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return LogError(timestamp, 'ERROR', 'unknown', line, line_num)
        
        return None
    
    def get_error_statistics(self) -> Dict:
        """获取错误统计信息"""
        if not self.errors:
            return {}
        
        # 按错误级别统计
        level_counts = Counter(error.level for error in self.errors)
        
        # 按来源统计
        source_counts = Counter(error.source for error in self.errors)
        
        # 按错误类型统计（基于消息关键词）
        error_types = defaultdict(int)
        for error in self.errors:
            # 提取错误类型关键词
            message_lower = error.message.lower()
            if 'foreign key' in message_lower:
                error_types['外键约束错误'] += 1
            elif 'connection' in message_lower:
                error_types['连接错误'] += 1
            elif 'permission' in message_lower or 'denied' in message_lower:
                error_types['权限错误'] += 1
            elif 'timeout' in message_lower:
                error_types['超时错误'] += 1
            elif 'not found' in message_lower:
                error_types['未找到错误'] += 1
            else:
                error_types['其他错误'] += 1
        
        # 时间分布统计
        time_distribution = defaultdict(int)
        for error in self.errors:
            try:
                # 提取小时信息进行统计
                if ':' in error.timestamp:
                    hour = error.timestamp.split()[1].split(':')[0]
                    time_distribution[f"{hour}:00"] += 1
            except (IndexError, ValueError):
                continue
        
        return {
            'total_errors': len(self.errors),
            'level_distribution': dict(level_counts),
            'source_distribution': dict(source_counts),
            'error_types': dict(error_types),
            'time_distribution': dict(sorted(time_distribution.items())),
            'top_errors': self._get_top_error_messages(10)
        }
    
    def _get_top_error_messages(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取出现频率最高的错误消息"""
        message_counts = Counter()
        
        for error in self.errors:
            # 使用标准化的错误消息进行统计
            normalized_message = error.get_normalized_message()
            message_counts[normalized_message] += 1
        
        return message_counts.most_common(limit)
    
    def deduplicate_errors(self, errors: Optional[List[LogError]] = None) -> List[LogError]:
        """对错误进行去重，保留每种错误的第一次出现"""
        errors_to_process = errors or self.errors
        
        seen_keys = set()
        deduplicated_errors = []
        duplicate_counts = Counter()
        
        for error in errors_to_process:
            dedup_key = error.get_deduplication_key()
            duplicate_counts[dedup_key] += 1
            
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                deduplicated_errors.append(error)
        
        # 为去重后的错误添加计数信息
        for error in deduplicated_errors:
            dedup_key = error.get_deduplication_key()
            error.occurrence_count = duplicate_counts[dedup_key]
        
        return deduplicated_errors
    
    def get_deduplication_statistics(self, errors: Optional[List[LogError]] = None) -> Dict:
        """获取去重统计信息"""
        errors_to_process = errors or self.errors
        deduplicated = self.deduplicate_errors(errors_to_process)
        
        # 统计重复次数分布
        occurrence_distribution = Counter()
        for error in deduplicated:
            count = getattr(error, 'occurrence_count', 1)
            occurrence_distribution[count] += 1
        
        # 找出重复次数最多的错误
        top_duplicates = []
        for error in deduplicated:
            count = getattr(error, 'occurrence_count', 1)
            if count > 1:
                top_duplicates.append((error.get_normalized_message(), count))
        
        top_duplicates.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'original_count': len(errors_to_process),
            'deduplicated_count': len(deduplicated),
            'reduction_percentage': round((1 - len(deduplicated) / len(errors_to_process)) * 100, 2) if errors_to_process else 0,
            'occurrence_distribution': dict(occurrence_distribution),
            'top_duplicates': top_duplicates[:10]
        }
    
    def filter_errors(self, 
                     level: Optional[str] = None,
                     source: Optional[str] = None,
                     keyword: Optional[str] = None,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> List[LogError]:
        """根据条件过滤错误"""
        filtered_errors = self.errors
        
        if level:
            filtered_errors = [e for e in filtered_errors if e.level.upper() == level.upper()]
        
        if source:
            filtered_errors = [e for e in filtered_errors if source.lower() in e.source.lower()]
        
        if keyword:
            filtered_errors = [e for e in filtered_errors if keyword.lower() in e.message.lower()]
        
        # 时间过滤（简单实现）
        if start_time or end_time:
            # 这里可以添加更复杂的时间过滤逻辑
            pass
        
        return filtered_errors
    
    def export_to_json(self, output_file: str, filtered_errors: Optional[List[LogError]] = None) -> None:
        """导出错误到JSON文件"""
        errors_to_export = filtered_errors or self.errors
        data = {
            'export_time': datetime.now().isoformat(),
            'total_errors': len(errors_to_export),
            'errors': [error.to_dict() for error in errors_to_export]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"错误数据已导出到: {output_file}")
    
    def print_summary(self, filtered_errors: Optional[List[LogError]] = None, show_deduplication: bool = False) -> None:
        """打印错误摘要"""
        errors_to_analyze = filtered_errors or self.errors
        
        if not errors_to_analyze:
            print("没有找到错误信息。")
            return
        
        stats = self.get_error_statistics()
        
        print(f"\n{'='*60}")
        print(f"日志错误分析报告")
        print(f"{'='*60}")
        print(f"日志文件: {self.log_file_path}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总错误数: {stats['total_errors']}")
        
        # 显示去重信息
        if show_deduplication:
            dedup_stats = self.get_deduplication_statistics(errors_to_analyze)
            print(f"\n🔄 去重统计:")
            print(f"  原始错误数: {dedup_stats['original_count']}")
            print(f"  去重后错误数: {dedup_stats['deduplicated_count']}")
            print(f"  减少百分比: {dedup_stats['reduction_percentage']}%")
            
            if dedup_stats['top_duplicates']:
                print(f"\n🔁 高频重复错误 (前5):")
                for i, (message, count) in enumerate(dedup_stats['top_duplicates'][:5], 1):
                    print(f"  {i}. [{count}次] {message[:80]}...")
        
        print(f"\n📊 错误级别分布:")
        for level, count in stats['level_distribution'].items():
            print(f"  {level}: {count}")
        
        print(f"\n🔍 错误来源分布:")
        for source, count in stats['source_distribution'].items():
            print(f"  {source}: {count}")
        
        print(f"\n📝 错误类型分布:")
        for error_type, count in stats['error_types'].items():
            print(f"  {error_type}: {count}")
        
        if stats['time_distribution']:
            print(f"\n⏰ 时间分布:")
            for time_slot, count in list(stats['time_distribution'].items())[:10]:
                print(f"  {time_slot}: {count}")
        
        print(f"\n🔥 高频错误消息 (前10):")
        for i, (message, count) in enumerate(stats['top_errors'], 1):
            print(f"  {i}. [{count}次] {message[:80]}...")
        
        print(f"\n📋 最近的错误详情 (前5条):")
        for i, error in enumerate(errors_to_analyze[-5:], 1):
            print(f"  {i}. 行{error.line_number}: {error}")


def main():
    parser = argparse.ArgumentParser(description='日志错误过滤和分析工具')
    parser.add_argument('log_file', help='日志文件路径')
    parser.add_argument('--level', help='过滤错误级别 (ERROR, CRITICAL, FATAL)')
    parser.add_argument('--source', help='过滤错误来源')
    parser.add_argument('--keyword', help='过滤包含关键词的错误')
    parser.add_argument('--export', help='导出结果到JSON文件')
    parser.add_argument('--deduplicate', '-d', action='store_true', help='对错误进行去重（去掉时间戳等动态内容）')
    parser.add_argument('--dedup-only', action='store_true', help='只导出去重后的错误')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式，只显示统计信息')
    
    args = parser.parse_args()
    
    try:
        # 创建过滤器并解析日志
        filter_obj = LogErrorFilter(args.log_file)
        print(f"正在解析日志文件: {args.log_file}")
        filter_obj.parse_log_file()
        
        # 应用过滤条件
        filtered_errors = filter_obj.filter_errors(
            level=args.level,
            source=args.source,
            keyword=args.keyword
        )
        
        # 应用去重
        if args.deduplicate or args.dedup_only:
            filtered_errors = filter_obj.deduplicate_errors(filtered_errors)
            print(f"去重后错误数: {len(filtered_errors)}")
        
        # 导出结果
        if args.export:
            # 如果使用了去重，在导出数据中添加去重信息
            if args.deduplicate or args.dedup_only:
                export_data = {
                    'export_time': datetime.now().isoformat(),
                    'original_count': len(filter_obj.errors),
                    'filtered_count': len(filtered_errors),
                    'deduplicated': True,
                    'deduplication_stats': filter_obj.get_deduplication_statistics(filtered_errors),
                    'errors': []
                }
                
                for error in filtered_errors:
                    error_dict = error.to_dict()
                    error_dict['occurrence_count'] = getattr(error, 'occurrence_count', 1)
                    export_data['errors'].append(error_dict)
                
                with open(args.export, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                filter_obj.export_to_json(args.export, filtered_errors)
            
            print(f"错误数据已导出到: {args.export}")
        
        # 显示结果
        if not args.quiet:
            show_dedup = args.deduplicate or args.dedup_only
            filter_obj.print_summary(filtered_errors, show_deduplication=show_dedup)
        else:
            stats = filter_obj.get_error_statistics()
            print(f"总错误数: {stats['total_errors']}")
            print(f"过滤后错误数: {len(filtered_errors)}")
            
            if args.deduplicate or args.dedup_only:
                dedup_stats = filter_obj.get_deduplication_statistics(filtered_errors)
                print(f"去重减少: {dedup_stats['reduction_percentage']}%")
    
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())