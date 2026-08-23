#!/usr/bin/env python3
"""测试工具协调器的规划逻辑"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.tool_coordinator import ToolCoordinator, ToolPriority


class MockAgent:
    """模拟 Agent"""
    pass


def test_coordinator_planning():
    """测试工具协调器的规划"""

    agent = MockAgent()
    coordinator = ToolCoordinator(agent)

    test_cases = [
        {
            "description": "支付接口 5xx 错误率从 0.1% 升到 35%",
            "classification": {"severity": "P0", "category": "availability"}
        },
        {
            "description": "MySQL 报 1205 死锁错误，影响订单创建",
            "classification": {"severity": "P1", "category": "database"}
        },
        {
            "description": "部署后 payment 服务 CPU 使用率 100%",
            "classification": {"severity": "P0", "category": "deployment"}
        },
        {
            "description": "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次",
            "classification": {"severity": "P1", "category": "availability"}
        },
        {
            "description": "推荐系统 P99 延迟从 500ms 升至 2 秒",
            "classification": {"severity": "P1", "category": "latency"}
        },
        {
            "description": "搜索接口超时率从 1% 升至 15%",
            "classification": {"severity": "P1", "category": "latency"}
        },
    ]

    print("=" * 80)
    print("工具协调器规划测试")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case['description']}")
        print(f"分类: severity={case['classification']['severity']}, category={case['classification']['category']}")

        # 规划工具调用
        plan = coordinator.plan_tool_calls(
            case['description'],
            case['classification']
        )

        print(f"\n规划了 {len(plan)} 个工具调用:")
        for j, step in enumerate(plan, 1):
            print(f"  {j}. {step['tool']} (优先级: {step['priority'].value})")
            print(f"     参数: {step['arguments']}")
            print(f"     原因: {step['reason']}")

        print("-" * 80)

    print("\n✅ 测试完成！")


def test_specific_rules():
    """测试特定规则"""

    print("\n" + "=" * 80)
    print("特定规则测试")
    print("=" * 80)

    agent = MockAgent()
    coordinator = ToolCoordinator(agent)

    # 测试 1: OOM 关键词识别
    print("\n【测试 1】OOM 关键词识别:")
    keywords = ["OOMKilled", "内存溢出", "Pod 重启", "容器 crash"]
    for keyword in keywords:
        plan = coordinator.plan_tool_calls(
            f"服务出现 {keyword}",
            {"severity": "P1", "category": "availability"}
        )
        has_oom_tool = any(step['tool'] == 'search_oom_events' for step in plan)
        print(f"  '{keyword}' → {'✓ 触发 OOM 工具' if has_oom_tool else '✗ 未触发'}")

    # 测试 2: 超时工具 + 服务识别
    print("\n【测试 2】超时工具 + 服务识别:")
    test_cases = [
        ("推荐系统延迟升高", "recommendation"),
        ("搜索接口超时", "search"),
        ("广告服务响应慢", "ad"),
        ("API 延迟问题", None),
    ]

    for description, expected_service in test_cases:
        plan = coordinator.plan_tool_calls(
            description,
            {"severity": "P1", "category": "latency"}
        )
        timeout_step = next((s for s in plan if s['tool'] == 'search_timeout_events'), None)

        if timeout_step:
            actual_service = timeout_step['arguments'].get('service')
            match = "✓" if actual_service == expected_service else "✗"
            print(f"  '{description}' → {match} service={actual_service} (期望: {expected_service})")
        else:
            print(f"  '{description}' → ✗ 未触发超时工具")

    print("\n✅ 特定规则测试完成！")


if __name__ == "__main__":
    test_coordinator_planning()
    test_specific_rules()
