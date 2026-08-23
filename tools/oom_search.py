"""
search_oom_events - 搜索 OOM（内存溢出）事件

从 JSONL 文件中读取 OOM 事件日志
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def search_oom_events(
    time_range: int = 60,
    service: Optional[str] = None,
    min_restart_count: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
    """
    搜索 OOM 事件

    Args:
        time_range: 查询最近多少分钟，默认 60
        service: 服务名称，不指定则查所有服务
        min_restart_count: 最小重启次数，默认 0（查所有）
        limit: 返回记录数量，默认 20

    Returns:
        OOM 事件列表
    """
    # 读取 OOM 事件日志文件
    log_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "mock_oom_events.jsonl"
    )

    oom_events = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    oom_events.append(json.loads(line))
    except FileNotFoundError:
        return {
            "total": 0,
            "time_range_minutes": time_range,
            "service_filter": service,
            "events": [],
            "summary": {
                "affected_services": [],
                "total_kills": 0,
                "max_restart_count": 0,
                "most_affected_service": None
            },
            "error": "OOM 事件日志文件不存在"
        }

    # 过滤：时间范围
    cutoff_time = datetime.now() - timedelta(minutes=time_range)
    filtered = []

    for event in oom_events:
        try:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time >= cutoff_time:
                # 过滤：服务名称
                if service and event.get("service") != service:
                    continue
                # 过滤：重启次数
                if event.get("restart_count", 0) >= min_restart_count:
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
        total_kills = len(filtered)
        max_restart_count = max(e.get("restart_count", 0) for e in filtered)

        # 找出最受影响的服务
        service_counts = {}
        for e in filtered:
            svc = e["service"]
            service_counts[svc] = service_counts.get(svc, 0) + 1
        most_affected_service = max(service_counts.items(), key=lambda x: x[1])[0] if service_counts else None
    else:
        affected_services = []
        total_kills = 0
        max_restart_count = 0
        most_affected_service = None

    return {
        "total": len(filtered),
        "time_range_minutes": time_range,
        "service_filter": service,
        "events": filtered,
        "summary": {
            "affected_services": affected_services,
            "total_kills": total_kills,
            "max_restart_count": max_restart_count,
            "most_affected_service": most_affected_service
        }
    }
