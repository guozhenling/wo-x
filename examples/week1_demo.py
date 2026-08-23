#!/usr/bin/env python3
"""
Day 7: 第一周总结 - 完整的故障分析系统

整合 Day 1-6 的所有功能，展示完整的工作流程。

系统能力：
- Day 1: Structured Output - 稳定的 JSON 输出
- Day 2: Policy 规则 - 安全兜底
- Day 3: 日志搜索 - 查证据
- Day 4: Tool-Calling Loop - 主动决策
- Day 5: Runbook 检索 - 推荐方案
- Day 6: 调用轨迹 - 完整记录
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import IncidentAgent
from src.models import IncidentResult


def demo_complete_system():
    """演示完整系统"""

    print("="*80)
    print("第一周总结：完整的故障分析系统")
    print("="*80)
    print()

    # 创建 Agent
    agent = IncidentAgent()

    # 测试案例
    test_cases = [
        {
            "description": "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
            "expect": {
                "severity": ["P0", "P1"],
                "tools": ["search_logs", "search_runbooks"],
                "review": True
            }
        },
        {
            "description": "推荐系统 P99 延迟从 500ms 升至 2 秒",
            "expect": {
                "severity": ["P2", "P3"],
                "tools": [],  # 可能不需要工具
                "review": False
            }
        },
        {
            "description": "MySQL 报 1205 死锁错误，影响订单创建",
            "expect": {
                "severity": ["P1", "P2"],
                "tools": ["search_logs", "search_runbooks"],
                "review": True
            }
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"案例 {i}: {case['description']}")
        print(f"{'='*80}")

        # 运行分析
        result = agent.analyze(case['description'])

        # 显示结果
        classification = result['classification']

        print(f"\n【Day 1: Structured Output】")
        print(f"  ✓ 返回结构化 JSON")
        print(f"  severity: {classification['severity']}")
        print(f"  category: {classification['category']}")
        print(f"  needs_human_review: {classification['needs_human_review']}")

        print(f"\n【Day 2: Policy 规则】")
        if agent.policy.get_violations():
            print(f"  ✓ 触发了 {len(agent.policy.get_violations())} 条规则:")
            for v in agent.policy.get_violations():
                print(f"    - {v.policy_name}")
        else:
            print(f"  ✓ 无需 Policy 修正")

        print(f"\n【Day 3-5: 工具调用】")
        if result['evidence']:
            print(f"  ✓ 调用了 {len(result['evidence'])} 个工具:")
            for ev in result['evidence']:
                tool_name = ev['tool']
                print(f"    - {tool_name}")
                if tool_name == 'search_logs':
                    logs = ev.get('result', [])
                    print(f"      → 返回 {len(logs)} 条日志")
                elif tool_name == 'search_runbooks':
                    runbooks = ev.get('result', [])
                    if runbooks:
                        print(f"      → 找到 {len(runbooks)} 个 Runbook")
                        print(f"      → 最佳匹配: {runbooks[0].get('title', 'N/A')}")
        else:
            print(f"  ✓ 信息充分，无需调用工具")

        print(f"\n【Day 6: 调用轨迹】")
        print(f"  ✓ 轨迹已保存: {result['trace_file']}")
        trace_summary = result.get('trace_summary', '')
        if trace_summary:
            print(f"  {trace_summary}")

        print(f"\n【最终判断】")
        print(f"  严重程度: {classification['severity']}")
        print(f"  判断依据: {classification['rationale'][:100]}...")

        # 验证预期
        print(f"\n【验证】")
        if classification['severity'] in case['expect']['severity']:
            print(f"  ✓ 严重程度符合预期")
        else:
            print(f"  ⚠️  严重程度: 预期 {case['expect']['severity']}, "
                  f"实际 {classification['severity']}")

        if classification['needs_human_review'] == case['expect']['review']:
            print(f"  ✓ 审核标记符合预期")
        else:
            print(f"  ⚠️  审核标记: 预期 {case['expect']['review']}, "
                  f"实际 {classification['needs_human_review']}")

        print(f"\n{'='*80}")

        # 暂停一下
        if i < len(test_cases):
            import time
            time.sleep(1)

    print(f"\n{'='*80}")
    print("第一周完成！")
    print("="*80)
    print()
    print("系统能力总结：")
    print("  ✓ 能理解故障描述（自然语言）")
    print("  ✓ 能主动查日志（查证据）")
    print("  ✓ 能检索 Runbook（找方案）")
    print("  ✓ 能基于证据分析（有依据）")
    print("  ✓ 能应用规则修正（保安全）")
    print("  ✓ 能记录完整轨迹（可审计）")
    print()
    print("下一步：Day 8-14（第二周）")
    print("  - 多工具协同")
    print("  - 错误处理与降级")
    print("  - 端到端优化")


if __name__ == "__main__":
    demo_complete_system()
