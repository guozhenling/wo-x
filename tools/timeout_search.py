"""
search_timeout_events - 搜索搜推广（搜索、推荐、广告）超时事件

从 JSONL 文件中读取超时事件日志
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def search_timeout_events(
    time_range: int = 60,
    service: Optional[str] = None,
    min_timeout_ms: int = 0,
    status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    搜索搜推广超时事件

    Args:
        time_range: 查询最近多少分钟，默认 60
        service: 服务名称（search/recommendation/ad），不指定则查所有
        min_timeout_ms: 最小超时时间（毫秒），默认 0（查所有）
        status: 状态过滤（timeout/success），不指定则查所有
        limit: 返回记录数量，默认 20

    Returns:
        超时事件列表
    """
    # 读取超时事件日志文件
    log_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "mock_timeout_events.jsonl"
    )

    timeout_events = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    timeout_events.append(json.loads(line))
    except FileNotFoundError:
        return {
            "total": 0,
            "time_range_minutes": time_range,
            "service_filter": service,
            "events": [],
            "summary": {
                "affected_services": [],
                "total_timeouts": 0,
                "avg_timeout_ms": 0,
                "max_timeout_ms": 0,
                "most_timeout_stage": None
            },
            "error": "超时事件日志文件不存在"
        }

    # 过滤：时间范围
    cutoff_time = datetime.now() - timedelta(minutes=time_range)
    filtered = []

    for event in timeout_events:
        try:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time >= cutoff_time:
                # 过滤：服务名称
                if service and event.get("service") != service:
                    continue
                # 过滤：状态
                if status and event.get("status") != status:
                    continue
                # 过滤：超时时间
                if event.get("actual_ms", 0) >= min_timeout_ms:
                    filtered.append(event)
        except (KeyError, ValueError):
            continue

    # 按时间倒序排序（最新的在前）
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)

    # 限制数量
    filtered = filtered[:limit]

    # 统计信息
    if filtered:
        affected_services = list(set(e["service"] for e in filtered))
        total_timeouts = sum(1 for e in filtered if e.get("status") == "timeout")
        total_success = sum(1 for e in filtered if e.get("status") == "success")
        avg_timeout_ms = round(sum(e.get("actual_ms", 0) for e in filtered) / len(filtered), 2)
        max_timeout_ms = max(e.get("actual_ms", 0) for e in filtered)

        # 找出最容易超时的阶段
        stage_counts = {}
        for e in filtered:
            stage = e.get("stage", "unknown")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        most_timeout_stage = max(stage_counts.items(), key=lambda x: x[1])[0] if stage_counts else None
    else:
        affected_services = []
        total_timeouts = 0
        total_success = 0
        avg_timeout_ms = 0
        max_timeout_ms = 0
        most_timeout_stage = None

    return {
        "total": len(filtered),
        "time_range_minutes": time_range,
        "service_filter": service,
        "status_filter": status,
        "events": filtered,
        "summary": {
            "affected_services": affected_services,
            "total_events": len(filtered),
            "total_timeouts": total_timeouts,
            "total_success": total_success,
            "avg_timeout_ms": avg_timeout_ms,
            "max_timeout_ms": max_timeout_ms,
            "most_timeout_stage": most_timeout_stage
        }
    }
