#!/usr/bin/env python3
"""
测试 Policy 规则 3 的修复
验证收入影响规则的错误率阈值逻辑
"""

import sys
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from policy import PolicyEngine


def test_revenue_impact_policy():
    """测试收入影响规则"""
    print("=" * 80)
    print("测试规则 3: 收入影响高优先级（错误率阈值）")
    print("=" * 80)
    print()

    policy = PolicyEngine()

    test_cases = [
        # Case 1: 高错误率 >= 20%，必须 P0
        {
            "name": "支付高错误率 35%",
            "description": "支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟",
            "initial": {"severity": "P1", "needs_human_review": True},
            "expected": {"severity": "P0", "needs_human_review": True},
        },
        # Case 2: 中等错误率 >= 5%，至少 P1
        {
            "name": "支付中等错误率 8%",
            "description": "支付接口 P99 延迟从 500ms 升至 8 秒，5% 用户支付超时",
            "initial": {"severity": "P2", "needs_human_review": False},
            "expected": {"severity": "P1", "needs_human_review": True},
        },
        # Case 3: 低错误率 < 5%，可以是 P2
        {
            "name": "支付低错误率 3%",
            "description": "第三方支付渠道偶尔超时，切换备用渠道后成功，整体成功率 97%",
            "initial": {"severity": "P2", "needs_human_review": False},
            "expected": {"severity": "P2", "needs_human_review": False},  # 不应该被强制提升
        },
        # Case 4: 无错误率信息，不强制提升
        {
            "name": "支付问题但无错误率",
            "description": "支付系统响应缓慢，用户反馈",
            "initial": {"severity": "P2", "needs_human_review": False},
            "expected": {"severity": "P2", "needs_human_review": False},  # 不应该被强制提升
        },
        # Case 5: 非收入相关，不触发规则
        {
            "name": "非收入相关高错误率",
            "description": "推荐系统错误率 30%，但不影响核心功能",
            "initial": {"severity": "P2", "needs_human_review": False},
            "expected": {"severity": "P2", "needs_human_review": False},
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"测试 {i}: {test['name']}")
        print(f"  描述: {test['description'][:60]}...")

        # 执行规则检查
        result = test["initial"].copy()
        result = policy.check_and_enforce(test["description"], result)

        # 验证结果
        expected = test["expected"]
        severity_match = result["severity"] == expected["severity"]
        review_match = result["needs_human_review"] == expected["needs_human_review"]

        passed = severity_match and review_match

        if passed:
            print(f"  ✓ 通过")
        else:
            print(f"  ✗ 失败")
            if not severity_match:
                print(f"    - 严重度: 期望 {expected['severity']}, 实际 {result['severity']}")
            if not review_match:
                print(f"    - 人工审核: 期望 {expected['needs_human_review']}, 实际 {result['needs_human_review']}")

        # 显示规则违反
        if policy.violations:
            print(f"  规则违反: {len(policy.violations)} 个")
            for v in policy.violations:
                print(f"    - {v.policy_name}: {v.message}")

        print()
        results.append((test["name"], passed))

    # 汇总结果
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")

    print()
    print(f"通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.0f}%)")

    return passed_count == total_count


def test_case_30_specifically():
    """专门测试 case 30"""
    print("\n" + "=" * 80)
    print("专门测试 Case 30")
    print("=" * 80)
    print()

    policy = PolicyEngine()

    description = "第三方支付渠道偶尔超时，切换备用渠道后成功，整体成功率 97%"
    result = {
        "severity": "P2",
        "category": "availability",
        "needs_human_review": False,
        "rationale": "第三方支付渠道降级，整体成功率仍然较高"
    }

    print(f"描述: {description}")
    print(f"初始结果: severity={result['severity']}, needs_human_review={result['needs_human_review']}")
    print()

    # 执行规则检查
    result = policy.check_and_enforce(description, result)

    print(f"规则检查后: severity={result['severity']}, needs_human_review={result['needs_human_review']}")

    if policy.violations:
        print(f"\n规则违反: {len(policy.violations)} 个")
        for v in policy.violations:
            print(f"  - [{v.level.value}] {v.policy_name}")
            print(f"    {v.message}")
    else:
        print("\n✓ 没有规则违反")

    print()

    # 验证期望
    if result["severity"] == "P2" and result["needs_human_review"] == False:
        print("✓ Case 30 测试通过！")
        print("  规则已正确优化，低错误率（3%）的支付问题不再被强制提升为 P1")
        return True
    else:
        print("✗ Case 30 测试失败")
        print(f"  期望: P2, needs_human_review=False")
        print(f"  实际: {result['severity']}, needs_human_review={result['needs_human_review']}")
        return False


def main():
    """主函数"""
    print("\n🔍 Policy 规则 3 修复验证\n")

    # 测试 1: 全面测试规则 3
    test1_passed = test_revenue_impact_policy()

    # 测试 2: 专门测试 case 30
    test2_passed = test_case_30_specifically()

    # 总结
    print("=" * 80)
    print("最终结果")
    print("=" * 80)

    if test1_passed and test2_passed:
        print("🎉 所有测试通过！")
        print()
        print("规则 3 已优化:")
        print("  • 错误率 >= 20%: 必须 P0")
        print("  • 错误率 >= 5%:  至少 P1")
        print("  • 错误率 < 5%:   可以是 P2（不强制提升）")
        print()
        print("Case 30 现在可以正确分类为 P2")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
