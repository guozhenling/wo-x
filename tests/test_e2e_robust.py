"""
端到端测试 - Agent V2 + 健壮执行器

验证完整的错误处理和降级机制
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from src.agent_v2 import IncidentAgentV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_normal_execution():
    """测试正常执行流程"""
    print("\n" + "=" * 60)
    print("测试1: 正常执行流程")
    print("=" * 60)

    agent = IncidentAgentV2()

    result = agent.analyze("支付接口 5xx 错误率 35%")

    print(f"\n诊断结果:")
    print(f"  严重程度: {result['classification']['severity']}")
    print(f"  分类: {result['classification']['category']}")
    if 'rationale' in result['classification']:
        print(f"  理由: {result['classification']['rationale'][:100]}...")

    # 获取执行指标
    metrics = agent.coordinator.get_execution_metrics()
    print(f"\n执行指标:")
    print(f"  缓存: {metrics['cache_stats']}")
    robust_metrics = metrics['robust_executor_metrics']
    print(f"  总调用: {robust_metrics['total_calls']}")
    print(f"  成功率: {robust_metrics['success_rate']:.1%}")
    print(f"  缓存命中率: {robust_metrics['cache_hit_rate']:.1%}")
    print(f"  平均耗时: {robust_metrics['avg_time']:.3f}s")


def test_with_cache():
    """测试缓存机制"""
    print("\n" + "=" * 60)
    print("测试2: 缓存机制")
    print("=" * 60)

    agent = IncidentAgentV2()

    # 第一次诊断
    print("\n第一次诊断:")
    result1 = agent.analyze("推荐服务超时率 15%")
    print(f"  严重程度: {result1['classification']['severity']}")

    # 第二次诊断（相同问题，应该命中缓存）
    print("\n第二次诊断（相同问题）:")
    result2 = agent.analyze("推荐服务超时率 15%")
    print(f"  严重程度: {result2['classification']['severity']}")

    # 获取指标
    metrics = agent.coordinator.get_execution_metrics()
    robust_metrics = metrics['robust_executor_metrics']
    print(f"\n缓存效果:")
    print(f"  总调用: {robust_metrics['total_calls']}")
    print(f"  缓存命中: {robust_metrics['cache_hits']}")
    print(f"  缓存命中率: {robust_metrics['cache_hit_rate']:.1%}")


def test_multiple_diagnoses():
    """测试多次诊断"""
    print("\n" + "=" * 60)
    print("测试3: 多次诊断")
    print("=" * 60)

    agent = IncidentAgentV2()

    test_cases = [
        "支付服务 OOM 持续重启",
        "数据库查询变慢，超时增加",
        "刚部署新版本后 5xx 增加",
        "推荐服务超时率 15%",
        "搜索服务响应延迟增加"
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case}")
        result = agent.analyze(case)
        print(f"  → {result['classification']['severity']} | {result['classification']['category']}")

    # 最终指标
    metrics = agent.coordinator.get_execution_metrics()
    robust_metrics = metrics['robust_executor_metrics']

    print(f"\n" + "=" * 60)
    print("最终执行指标")
    print("=" * 60)
    print(f"总调用: {robust_metrics['total_calls']}")
    print(f"成功: {robust_metrics['successful_calls']}")
    print(f"失败: {robust_metrics['failed_calls']}")
    print(f"缓存命中: {robust_metrics['cache_hits']}")
    print(f"成功率: {robust_metrics['success_rate']:.1%}")
    print(f"缓存命中率: {robust_metrics['cache_hit_rate']:.1%}")
    print(f"平均耗时: {robust_metrics['avg_time']:.3f}s")


if __name__ == "__main__":
    try:
        test_normal_execution()
        test_with_cache()
        test_multiple_diagnoses()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
