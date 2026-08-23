"""
search_slow_queries - 搜索数据库慢查询

模拟数据库慢查询日志
"""
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
    # 模拟慢查询数据
    slow_queries = [
        {
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "query": "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE status = 'active') AND created_at > '2024-01-01'",
            "duration": 3.45,
            "lock_time": 0.12,
            "rows_examined": 125000,
            "rows_sent": 850,
            "database": "order_db",
            "user": "app_user"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=12)).isoformat(),
            "query": "UPDATE orders SET status = 'processing' WHERE id IN (SELECT order_id FROM payments WHERE status = 'pending')",
            "duration": 5.23,
            "lock_time": 2.15,
            "rows_examined": 8500,
            "rows_sent": 0,
            "database": "order_db",
            "user": "app_user"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=18)).isoformat(),
            "query": "SELECT u.*, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING order_count > 10",
            "duration": 2.87,
            "lock_time": 0.05,
            "rows_examined": 45000,
            "rows_sent": 234,
            "database": "user_db",
            "user": "app_user"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=25)).isoformat(),
            "query": "DELETE FROM sessions WHERE last_active < DATE_SUB(NOW(), INTERVAL 7 DAY)",
            "duration": 4.12,
            "lock_time": 1.23,
            "rows_examined": 15000,
            "rows_sent": 0,
            "database": "session_db",
            "user": "cleanup_job"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "query": "SELECT * FROM products WHERE category_id IN (SELECT id FROM categories WHERE parent_id IS NULL) ORDER BY price DESC",
            "duration": 1.95,
            "lock_time": 0.08,
            "rows_examined": 28000,
            "rows_sent": 500,
            "database": "product_db",
            "user": "app_user"
        }
    ]

    # 过滤：时间范围和最小执行时间
    cutoff_time = datetime.now() - timedelta(minutes=time_range)
    filtered = [
        q for q in slow_queries
        if datetime.fromisoformat(q["timestamp"]) >= cutoff_time
        and q["duration"] >= min_duration
    ]

    # 限制数量
    filtered = filtered[:limit]

    return {
        "total": len(filtered),
        "time_range_minutes": time_range,
        "min_duration_seconds": min_duration,
        "queries": filtered,
        "summary": {
            "avg_duration": round(sum(q["duration"] for q in filtered) / len(filtered), 2) if filtered else 0,
            "max_duration": max(q["duration"] for q in filtered) if filtered else 0,
            "total_lock_time": round(sum(q["lock_time"] for q in filtered), 2) if filtered else 0
        }
    }
