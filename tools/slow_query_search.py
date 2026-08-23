"""
search_slow_queries - 搜索数据库慢查询

从 JSONL 文件中读取慢查询日志
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


def search_slow_queries(
    time_range: int = 60,
    min_duration: float = 1.0,
    limit: int = 10
) -> Dict[str, Any]:
    """
    搜索数据库慢查询

    Args:
        time_range: 查询最近多少分钟，默认 60
        min_duration: 最小执行时间（秒），默认 1.0
        limit: 返回记录数量，默认 10

    Returns:
        慢查询列表
    """
    # 读取慢查询日志文件
    log_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "mock_slow_queries.jsonl"
    )

    slow_queries = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    slow_queries.append(json.loads(line))
    except FileNotFoundError:
        # 如果文件不存在，返回空结果
        return {
            "total": 0,
            "time_range_minutes": time_range,
            "min_duration_seconds": min_duration,
            "queries": [],
            "summary": {
                "avg_duration": 0,
                "max_duration": 0,
                "total_lock_time": 0
            },
            "error": "慢查询日志文件不存在"
        }

    # 过滤：时间范围和最小执行时间
    cutoff_time = datetime.now() - timedelta(minutes=time_range)
    filtered = []

    for q in slow_queries:
        try:
            query_time = datetime.fromisoformat(q["timestamp"])
            if query_time >= cutoff_time and q["duration"] >= min_duration:
                filtered.append(q)
        except (KeyError, ValueError):
            continue

    # 按时间倒序排序（最新的在前）
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)

    # 限制数量
    filtered = filtered[:limit]

    # 计算统计信息
    if filtered:
        avg_duration = round(sum(q["duration"] for q in filtered) / len(filtered), 2)
        max_duration = max(q["duration"] for q in filtered)
        total_lock_time = round(sum(q["lock_time"] for q in filtered), 2)
    else:
        avg_duration = 0
        max_duration = 0
        total_lock_time = 0

    return {
        "total": len(filtered),
        "time_range_minutes": time_range,
        "min_duration_seconds": min_duration,
        "queries": filtered,
        "summary": {
            "avg_duration": avg_duration,
            "max_duration": max_duration,
            "total_lock_time": total_lock_time
        }
    }
