#!/usr/bin/env python3
"""
对比 Agent V1 和 V2 的性能

V1: LLM Tool-Calling Loop（让 LLM 自己决定调用哪些工具）
V2: ToolCoordinator（规则决定调用哪些工具）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from src.agent import IncidentAgent as AgentV1
from src.agent_v2 import IncidentAgentV2 as AgentV2


def compare_agents():
    """对比两个版本的 Agent"""

    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "MySQL 报 1205 死锁错误，影响订单创建",
        "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次"
    ]

    print("=" * 80)
    print("Agent V1 vs V2 对比测试")
    print("=" * 80)
    print("\nV1: LLM Tool-Calling Loop（LLM 自己决定）")
    print("V2: ToolCoordinator（规则决定）")
    print("=" * 80)

    agent_v1 = AgentV1()
    agent_v2 = AgentV2()

    results = []

    for i, description in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"案例 {i}: {description}")
        print("=" * 80)

        # 测试 V1
        print("\n【V1 - LLM Tool-Calling】")
        start_v1 = time.time()
        result_v1 = agent_v1.analyze(description)
        time_v1 = time.time() - start_v1

        print(f"  分类: {result_v1['classification']['severity']}, {result_v1['classification']['category']}")
        print(f"  工具调用: {len(result_v1['evidence'])} 次")
        print(f"  耗时: {time_v1:.2f}s")

        # 测试 V2
        print("\n【V2 - ToolCoordinator】")
        start_v2 = time.time()
        result_v2 = agent_v2.analyze(description)
        time_v2 = time.time() - start_v2

        print(f"  分类: {result_v2['classification']['severity']}, {result_v2['classification']['category']}")
        print(f"  工具调用: {len(result_v2['evidence'])} 次")
        print(f"  调用工具: {', '.join([ev['tool'] for ev in result_v2['evidence']])}")
        print(f"  耗时: {time_v2:.2f}s")

        # 对比
        print("\n【对比】")
        if result_v1['classification']['severity'] == result_v2['classification']['severity']:
            print(f"  ✓ Severity 一致: {result_v1['classification']['severity']}")
        else:
            print(f"  ✗ Severity 不一致: V1={result_v1['classification']['severity']}, V2={result_v2['classification']['severity']}")

        if result_v1['classification']['category'] == result_v2['classification']['category']:
            print(f"  ✓ Category 一致: {result_v1['classification']['category']}")
        else:
            print(f"  ✗ Category 不一致: V1={result_v1['classification']['category']}, V2={result_v2['classification']['category']}")

        speedup = time_v1 / time_v2 if time_v2 > 0 else 0
        print(f"  速度: V2 {'快' if speedup > 1 else '慢'} {abs(speedup - 1) * 100:.1f}% ({speedup:.2f}x)")

        results.append({
            "description": description,
            "v1": {
                "severity": result_v1['classification']['severity'],
                "category": result_v1['classification']['category'],
                "tools": len(result_v1['evidence']),
                "time": time_v1
            },
            "v2": {
                "severity": result_v2['classification']['severity'],
                "category": result_v2['classification']['category'],
                "tools": len(result_v2['evidence']),
                "time": time_v2
            }
        })

    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)

    severity_match = sum(1 for r in results if r['v1']['severity'] == r['v2']['severity'])
    category_match = sum(1 for r in results if r['v1']['category'] == r['v2']['category'])
    avg_time_v1 = sum(r['v1']['time'] for r in results) / len(results)
    avg_time_v2 = sum(r['v2']['time'] for r in results) / len(results)

    print(f"\nSeverity 一致性: {severity_match}/{len(results)} ({severity_match/len(results)*100:.1f}%)")
    print(f"Category 一致性: {category_match}/{len(results)} ({category_match/len(results)*100:.1f}%)")
    print(f"\n平均耗时:")
    print(f"  V1: {avg_time_v1:.2f}s")
    print(f"  V2: {avg_time_v2:.2f}s")
    print(f"  V2 相对 V1: {(1 - avg_time_v2/avg_time_v1)*100:.1f}% {'快' if avg_time_v2 < avg_time_v1 else '慢'}")

    # V2 的优势
    print("\n【V2 (ToolCoordinator) 的优势】")
    print("✅ 确定性: 同样的故障一定调用相同的工具")
    print("✅ 可控性: 通过规则精确控制工具调用")
    print("✅ 可测试: 规则逻辑清晰，易于单元测试")
    print("✅ 成本: 只调用 2 次 LLM（快速分类 + 最终分类），不是 N 轮")

    print("\n【V1 (LLM Tool-Calling) 的优势】")
    print("✅ 灵活性: LLM 可以根据上下文动态决定")
    print("✅ 适应性: 可以处理规则未覆盖的情况")
    print("❌ 不确定性: 同样的故障可能调用不同的工具")
    print("❌ 成本高: 每轮都调用 LLM API")


if __name__ == "__main__":
    compare_agents()
