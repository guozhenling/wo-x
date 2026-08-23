"""
get_deployment_history - 查询部署历史

从 JSONL 文件中读取部署记录
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def get_deployment_history(
    hours: int = 24,
    service: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    查询部署历史

    Args:
        hours: 查询最近多少小时，默认 24
        service: 服务名称，不指定则查所有服务
        limit: 返回记录数量，默认 20

    Returns:
        部署历史记录
    """
    # 读取部署历史文件
    log_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "mock_deployments.jsonl"
    )

    deployments = []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    deployments.append(json.loads(line))
    except FileNotFoundError:
        # 如果文件不存在，返回空结果
        return {
            "total": 0,
            "time_range_hours": hours,
            "service_filter": service,
            "deployments": [],
            "summary": {
                "services_deployed": [],
                "successful_deployments": 0,
                "rollback_count": 0,
                "avg_duration_seconds": 0
            },
            "error": "部署历史文件不存在"
        }

    # 过滤：时间范围
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered = []

    for d in deployments:
        try:
            deploy_time = datetime.fromisoformat(d["timestamp"])
            if deploy_time >= cutoff_time:
                filtered.append(d)
        except (KeyError, ValueError):
            continue

    # 过滤：服务名称
    if service:
        filtered = [d for d in filtered if d.get("service") == service]

    # 按时间倒序排序（最新的在前）
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)

    # 限制数量
    filtered = filtered[:limit]

    # 统计信息
    if filtered:
        services_deployed = list(set(d["service"] for d in filtered))
        rollback_count = sum(1 for d in filtered if d.get("status") == "rollback")
        successful_deployments = len(filtered) - rollback_count
        avg_duration = round(sum(d.get("duration_seconds", 0) for d in filtered) / len(filtered), 2)
    else:
        services_deployed = []
        rollback_count = 0
        successful_deployments = 0
        avg_duration = 0

    return {
        "total": len(filtered),
        "time_range_hours": hours,
        "service_filter": service,
        "deployments": filtered,
        "summary": {
            "services_deployed": services_deployed,
            "successful_deployments": successful_deployments,
            "rollback_count": rollback_count,
            "avg_duration_seconds": avg_duration
        }
    }
