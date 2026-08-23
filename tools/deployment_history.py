"""
get_deployment_history - 查询部署历史

模拟部署记录数据
"""
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
    # 模拟部署数据
    deployments = [
        {
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "service": "payment",
            "version": "v2.3.5",
            "previous_version": "v2.3.4",
            "environment": "production",
            "deployed_by": "zhang_san",
            "status": "success",
            "changes": [
                "修复支付回调超时问题",
                "优化数据库查询性能",
                "添加更多日志"
            ],
            "duration_seconds": 180
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
            "service": "order",
            "version": "v1.8.2",
            "previous_version": "v1.8.1",
            "environment": "production",
            "deployed_by": "li_si",
            "status": "success",
            "changes": [
                "新增订单状态推送功能",
                "修复订单取消逻辑"
            ],
            "duration_seconds": 120
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
            "service": "user",
            "version": "v3.1.0",
            "previous_version": "v3.0.9",
            "environment": "production",
            "deployed_by": "wang_wu",
            "status": "success",
            "changes": [
                "用户画像功能上线",
                "优化登录流程"
            ],
            "duration_seconds": 150
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
            "service": "recommendation",
            "version": "v2.1.3",
            "previous_version": "v2.1.2",
            "environment": "production",
            "deployed_by": "zhao_liu",
            "status": "rollback",
            "changes": [
                "推荐算法优化",
                "缓存策略调整"
            ],
            "duration_seconds": 200,
            "rollback_reason": "推荐结果异常，点击率下降 30%"
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=15)).isoformat(),
            "service": "payment",
            "version": "v2.3.4",
            "previous_version": "v2.3.3",
            "environment": "production",
            "deployed_by": "zhang_san",
            "status": "success",
            "changes": [
                "支持新的支付渠道",
                "风控规则更新"
            ],
            "duration_seconds": 160
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=20)).isoformat(),
            "service": "order",
            "version": "v1.8.1",
            "previous_version": "v1.8.0",
            "environment": "production",
            "deployed_by": "li_si",
            "status": "success",
            "changes": [
                "订单列表查询优化",
                "增加订单导出功能"
            ],
            "duration_seconds": 110
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=28)).isoformat(),
            "service": "user",
            "version": "v3.0.9",
            "previous_version": "v3.0.8",
            "environment": "production",
            "deployed_by": "wang_wu",
            "status": "success",
            "changes": [
                "修复用户信息更新 bug",
                "头像上传功能优化"
            ],
            "duration_seconds": 90
        },
        {
            "timestamp": (datetime.now() - timedelta(hours=36)).isoformat(),
            "service": "recommendation",
            "version": "v2.1.2",
            "previous_version": "v2.1.1",
            "environment": "production",
            "deployed_by": "zhao_liu",
            "status": "success",
            "changes": [
                "推荐列表缓存优化",
                "AB 测试配置更新"
            ],
            "duration_seconds": 140
        }
    ]

    # 过滤：时间范围
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered = [
        d for d in deployments
        if datetime.fromisoformat(d["timestamp"]) >= cutoff_time
    ]

    # 过滤：服务名称
    if service:
        filtered = [d for d in filtered if d["service"] == service]

    # 限制数量
    filtered = filtered[:limit]

    # 统计
    services_deployed = list(set(d["service"] for d in filtered))
    rollback_count = sum(1 for d in filtered if d["status"] == "rollback")

    return {
        "total": len(filtered),
        "time_range_hours": hours,
        "service_filter": service,
        "deployments": filtered,
        "summary": {
            "services_deployed": services_deployed,
            "successful_deployments": len(filtered) - rollback_count,
            "rollback_count": rollback_count,
            "avg_duration_seconds": round(sum(d["duration_seconds"] for d in filtered) / len(filtered), 2) if filtered else 0
        }
    }
