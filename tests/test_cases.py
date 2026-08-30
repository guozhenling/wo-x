"""
结构化测试案例集

定义全面的测试案例，用于评测故障分类器的准确性
"""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class EvaluationTestCase:
    """单个测试案例"""
    id: str                          # 案例 ID
    description: str                 # 故障描述
    expected_severity: str           # 期望严重程度
    expected_category: str           # 期望类别
    acceptable_severities: List[str] # 可接受的严重程度范围
    notes: str = ""                  # 说明


# ============================================================================
# P0 案例 - 核心收入/数据安全（必须准确）
# ============================================================================
P0_CASES = [
    EvaluationTestCase(
        id="P0-001",
        description="支付接口完全不可用，所有请求返回 500，持续 15 分钟",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="核心收入，必须 P0"
    ),
    EvaluationTestCase(
        id="P0-002",
        description="订单创建成功率从 99.9% 降到 60%，影响所有用户",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="影响核心收入"
    ),
    EvaluationTestCase(
        id="P0-003",
        description="用户登录接口 5xx 错误率 30%，大量用户无法登录",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="用户无法登录"
    ),
    EvaluationTestCase(
        id="P0-004",
        description="支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P0-005",
        description="数据库发现未授权访问，疑似数据泄露",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="数据安全问题"
    ),
    EvaluationTestCase(
        id="P0-006",
        description="Redis 集群完全宕机，所有缓存失效，核心服务受影响",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="影响核心服务"
    ),
    EvaluationTestCase(
        id="P0-007",
        description="订单数据库主库宕机，所有写操作失败",
        expected_severity="P0",
        expected_category="database",
        acceptable_severities=["P0"],
        notes="核心数据库故障"
    ),
]


# ============================================================================
# P1 案例 - 核心服务明显故障（重要准确）
# ============================================================================
P1_CASES = [
    EvaluationTestCase(
        id="P1-001",
        description="推荐系统 P99 延迟从 500ms 升至 2 秒，超时率 15%",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P0", "P1"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P1-002",
        description="MySQL 报 1205 死锁错误，影响订单创建，每分钟 20 次",
        expected_severity="P1",
        expected_category="database",
        acceptable_severities=["P0", "P1"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P1-003",
        description="搜索服务超时率从 1% 升到 15%，用户体验明显下降",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P1"],
        notes="核心服务延迟"
    ),
    EvaluationTestCase(
        id="P1-004",
        description="API Gateway 频繁 OOM，平均每 10 分钟重启一次",
        expected_severity="P1",
        expected_category="availability",
        acceptable_severities=["P0", "P1"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P1-005",
        description="新版本部署后，错误日志暴增 10 倍，5xx 错误率 8%",
        expected_severity="P1",
        expected_category="deployment",
        acceptable_severities=["P0", "P1"],
        notes="部署引入问题"
    ),
    EvaluationTestCase(
        id="P1-006",
        description="推荐服务 p99 延迟从 100ms 升到 3s，影响首页加载",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P0", "P1"],
        notes="核心服务延迟严重"
    ),
    EvaluationTestCase(
        id="P1-007",
        description="数据库连接池耗尽，新请求无法获取连接，等待超时",
        expected_severity="P1",
        expected_category="database",
        acceptable_severities=["P0", "P1"],
        notes="数据库连接问题"
    ),
    EvaluationTestCase(
        id="P1-008",
        description="广告服务响应时间从 200ms 升到 5s，超时率 20%",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P1", "P2"],
        notes="核心服务但非关键路径"
    ),
]


# ============================================================================
# P2 案例 - 非核心或部分影响（允许误差）
# ============================================================================
P2_CASES = [
    EvaluationTestCase(
        id="P2-001",
        description="用户头像上传偶尔失败，错误率 2%",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P1", "P2"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P2-002",
        description="消息推送延迟 30 秒，但最终都能送达",
        expected_severity="P2",
        expected_category="latency",
        acceptable_severities=["P2"],
        notes="延迟但不影响核心"
    ),
    EvaluationTestCase(
        id="P2-003",
        description="后台管理系统加载慢，打开需要 5 秒",
        expected_severity="P2",
        expected_category="latency",
        acceptable_severities=["P2", "P3"],
        notes="内部系统"
    ),
    EvaluationTestCase(
        id="P2-004",
        description="部分地区 CDN 节点故障，已切换备用，用户无感知",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P2"],
        notes="已有降级"
    ),
    EvaluationTestCase(
        id="P2-005",
        description="埋点数据采集失败率 10%，不影响业务功能",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P2", "P3"],
        notes="数据分析，非实时"
    ),
    EvaluationTestCase(
        id="P2-006",
        description="评论功能偶发 500 错误，错误率 3%",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P2"],
        notes="非核心功能"
    ),
    EvaluationTestCase(
        id="P2-007",
        description="图片上传成功但处理慢，需要等待 10 秒才能看到缩略图",
        expected_severity="P2",
        expected_category="latency",
        acceptable_severities=["P2", "P3"],
        notes="异步处理，不阻塞主流程"
    ),
]


# ============================================================================
# P3 案例 - 低影响观察（允许误差）
# ============================================================================
P3_CASES = [
    EvaluationTestCase(
        id="P3-001",
        description="某个低频 API 偶发 500 错误，错误率 0.5%",
        expected_severity="P3",
        expected_category="availability",
        acceptable_severities=["P2", "P3"],
        notes="来自已有 E2E 测试"
    ),
    EvaluationTestCase(
        id="P3-002",
        description="日志中发现少量慢查询（<1%），响应时间 1-2 秒",
        expected_severity="P3",
        expected_category="database",
        acceptable_severities=["P3"],
        notes="偶发，无影响"
    ),
    EvaluationTestCase(
        id="P3-003",
        description="测试环境数据库连接池满，但生产环境正常",
        expected_severity="P3",
        expected_category="database",
        acceptable_severities=["P3"],
        notes="非生产环境"
    ),
    EvaluationTestCase(
        id="P3-004",
        description="某个低频功能响应时间略有上升，从 100ms 到 200ms",
        expected_severity="P3",
        expected_category="latency",
        acceptable_severities=["P3"],
        notes="低流量"
    ),
    EvaluationTestCase(
        id="P3-005",
        description="监控告警发现一个节点 CPU 使用率偏高，但服务正常",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P3"],
        notes="单节点，无影响"
    ),
    EvaluationTestCase(
        id="P3-006",
        description="某个统计任务执行时间从 5 分钟增加到 8 分钟",
        expected_severity="P3",
        expected_category="latency",
        acceptable_severities=["P3"],
        notes="后台任务，非实时"
    ),
]


# ============================================================================
# 边界案例 - 测试鲁棒性（模糊、冲突、极端）
# ============================================================================
EDGE_CASES = [
    EvaluationTestCase(
        id="EDGE-001",
        description="有点慢",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P2", "P3"],
        notes="描述极度模糊"
    ),
    EvaluationTestCase(
        id="EDGE-002",
        description="错误率 20%，但已通过回滚恢复，当前错误率 0.1%",
        expected_severity="P2",
        expected_category="deployment",
        acceptable_severities=["P1", "P2"],
        notes="已恢复，降级处理"
    ),
    EvaluationTestCase(
        id="EDGE-003",
        description="",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P3"],
        notes="空输入"
    ),
    EvaluationTestCase(
        id="EDGE-004",
        description="所有服务都挂了，网站完全不可用，用户无法访问任何功能",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="灾难性故障"
    ),
    EvaluationTestCase(
        id="EDGE-005",
        description="支付接口错误率 8%，但只影响特定支付方式",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0", "P1"],
        notes="接近阈值，部分影响"
    ),
    EvaluationTestCase(
        id="EDGE-006",
        description="数据库慢查询很多，但都在 1 秒以内，用户无感知",
        expected_severity="P3",
        expected_category="database",
        acceptable_severities=["P2", "P3"],
        notes="有问题但影响小"
    ),
    EvaluationTestCase(
        id="EDGE-007",
        description="新功能上线后，相关接口 QPS 暴增 10 倍，但服务正常",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P3"],
        notes="流量增长但非故障"
    ),
]


# ============================================================================
# 完整案例集
# ============================================================================
ALL_TEST_CASES = (
    P0_CASES + P1_CASES + P2_CASES + P3_CASES + EDGE_CASES
)


# ============================================================================
# 工具函数
# ============================================================================
def get_test_cases_by_priority(priority: str) -> List[EvaluationTestCase]:
    """
    按优先级获取测试案例

    Args:
        priority: 优先级（P0/P1/P2/P3/EDGE）

    Returns:
        测试案例列表
    """
    case_map = {
        "P0": P0_CASES,
        "P1": P1_CASES,
        "P2": P2_CASES,
        "P3": P3_CASES,
        "EDGE": EDGE_CASES,
    }
    return case_map.get(priority, [])


def get_all_cases() -> List[EvaluationTestCase]:
    """
    获取所有测试案例

    Returns:
        所有测试案例列表
    """
    return ALL_TEST_CASES


def get_cases_by_category(category: str) -> List[EvaluationTestCase]:
    """
    按类别获取测试案例

    Args:
        category: 类别（availability/latency/database/deployment/unknown）

    Returns:
        测试案例列表
    """
    return [
        case for case in ALL_TEST_CASES
        if case.expected_category == category
    ]


def get_statistics() -> Dict[str, Any]:
    """
    获取案例集统计信息

    Returns:
        统计信息
    """
    return {
        "total": len(ALL_TEST_CASES),
        "by_priority": {
            "P0": len(P0_CASES),
            "P1": len(P1_CASES),
            "P2": len(P2_CASES),
            "P3": len(P3_CASES),
            "EDGE": len(EDGE_CASES),
        },
        "by_category": {
            "availability": len(get_cases_by_category("availability")),
            "latency": len(get_cases_by_category("latency")),
            "database": len(get_cases_by_category("database")),
            "deployment": len(get_cases_by_category("deployment")),
            "unknown": len(get_cases_by_category("unknown")),
        }
    }


def print_statistics():
    """打印案例集统计"""
    stats = get_statistics()

    print("\n" + "=" * 60)
    print("测试案例集统计")
    print("=" * 60)

    print(f"\n总案例数: {stats['total']}")

    print(f"\n按优先级分布:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority}: {count} 个")

    print(f"\n按类别分布:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count} 个")


if __name__ == "__main__":
    # 打印统计信息
    print_statistics()

    # 打印部分案例示例
    print("\n" + "=" * 60)
    print("P0 案例示例")
    print("=" * 60)
    for case in P0_CASES[:3]:
        print(f"\n{case.id}: {case.description}")
        print(f"  期望: {case.expected_severity} / {case.expected_category}")
        print(f"  可接受: {case.acceptable_severities}")
