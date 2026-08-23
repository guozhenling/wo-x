#!/usr/bin/env python3
"""调试 OOM 工具调用问题"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_v2 import IncidentAgentV2

agent = IncidentAgentV2()

# 测试两种描述
test_descriptions = [
    "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次",
    "recommendation 服务 Pod 内存溢出，重启 5 次"
]

for description in test_descriptions:
    print("=" * 80)
    print(f"测试: {description}")
    print("=" * 80)

for description in test_descriptions:
    print("=" * 80)
    print(f"测试: {description}")
    print("=" * 80)

    # 测试快速分类
    print("\n【Step 1: 快速分类】")
    initial = agent._quick_classify(description)
    print(f"分类: severity={initial['severity']}, category={initial['category']}")

    # 测试关键词匹配
    print("\n【Step 2: 关键词匹配】")
    keywords = ["oom", "内存", "重启", "killed", "crash", "pod"]
    desc_lower = description.lower()
    print(f"描述(小写): {desc_lower}")
    for keyword in keywords:
        match = keyword in desc_lower
        print(f"  '{keyword}': {'✓ 匹配' if match else '✗ 不匹配'}")

    # 测试工具规划
    print("\n【Step 3: 工具规划】")
    from tools.tool_coordinator import ToolCoordinator
    coordinator = ToolCoordinator(agent)
    plan = coordinator.plan_tool_calls(description, initial)

    print(f"规划了 {len(plan)} 个工具:")
    for i, step in enumerate(plan, 1):
        print(f"  {i}. {step['tool']} - {step['reason']}")

    # 检查是否有 OOM 工具
    has_oom_tool = any(step['tool'] == 'search_oom_events' for step in plan)
    print(f"\n{'✓' if has_oom_tool else '✗'} {'有' if has_oom_tool else '没有'} OOM 工具")

    if not has_oom_tool:
        print("\n【问题分析】")
        print("可能的原因:")
        print("  1. 关键词未匹配")
        print("  2. 规则逻辑有问题")

    print()

