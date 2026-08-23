#!/usr/bin/env python3
"""
测试框架验证脚本
验证测试框架的基本功能（不调用真实 API）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data import (
    get_test_cases,
    get_cases_by_tag,
    get_cases_by_severity,
    print_test_data_summary
)


def verify_data_structure():
    """验证数据结构完整性"""
    print("=" * 80)
    print("验证数据结构")
    print("=" * 80)
    print()

    all_cases = get_test_cases()

    # 检查总数
    assert len(all_cases) == 40, f"期望 40 个案例，实际 {len(all_cases)} 个"
    print(f"✓ 总案例数: {len(all_cases)}")

    # 检查必填字段
    for case in all_cases:
        assert case.id, f"Case {case.id}: id 不能为空"
        assert case.description, f"Case {case.id}: description 不能为空"
        assert case.expected_severity in ["P0", "P1", "P2", "P3"], \
            f"Case {case.id}: severity 必须是 P0/P1/P2/P3"
        assert case.expected_category, f"Case {case.id}: category 不能为空"
        assert isinstance(case.expected_human_review, bool), \
            f"Case {case.id}: human_review 必须是 bool"
        assert isinstance(case.requires_tool_evidence, bool), \
            f"Case {case.id}: requires_tool_evidence 必须是 bool"
        assert case.tags, f"Case {case.id}: tags 不能为空"

    print(f"✓ 所有案例字段完整")

    # 检查 ID 唯一性
    ids = [case.id for case in all_cases]
    assert len(ids) == len(set(ids)), "存在重复的 case ID"
    print(f"✓ 所有案例 ID 唯一")
    print()


def verify_tag_filtering():
    """验证标签筛选功能"""
    print("=" * 80)
    print("验证标签筛选")
    print("=" * 80)
    print()

    # 测试各种标签
    test_tags = [
        "payment_5xx",
        "malicious",
        "insufficient_evidence",
        "deadlock",
        "deployment"
    ]

    for tag in test_tags:
        cases = get_cases_by_tag(tag)
        assert len(cases) >= 1, f"标签 {tag} 应该至少有 1 个案例"
        print(f"✓ {tag}: {len(cases)} 个案例")

    print()


def verify_severity_filtering():
    """验证严重程度筛选功能"""
    print("=" * 80)
    print("验证严重程度筛选")
    print("=" * 80)
    print()

    all_cases = get_test_cases()
    total = 0

    for severity in ["P0", "P1", "P2", "P3"]:
        cases = get_cases_by_severity(severity)
        total += len(cases)
        assert len(cases) >= 1, f"{severity} 应该至少有 1 个案例"
        print(f"✓ {severity}: {len(cases)} 个案例")

    assert total == len(all_cases), f"筛选后总数 {total} 不等于全部案例数 {len(all_cases)}"
    print(f"\n✓ 筛选后总数匹配: {total}")
    print()


def verify_special_cases():
    """验证特殊案例"""
    print("=" * 80)
    print("验证特殊案例")
    print("=" * 80)
    print()

    all_cases = get_test_cases()

    # 1. 支付 5xx 案例（至少 1 个）
    payment_cases = get_cases_by_tag("payment_5xx")
    assert len(payment_cases) >= 1, "应该至少有 1 个支付 5xx 案例"
    print(f"✓ 支付 5xx 案例: {len(payment_cases)} 个")

    # 2. 数据库死锁案例（至少 1 个）
    deadlock_cases = get_cases_by_tag("deadlock")
    assert len(deadlock_cases) >= 1, "应该至少有 1 个死锁案例"
    print(f"✓ 死锁案例: {len(deadlock_cases)} 个")

    # 3. 发布异常案例（至少 1 个）
    deployment_cases = get_cases_by_tag("deployment")
    assert len(deployment_cases) >= 1, "应该至少有 1 个发布异常案例"
    print(f"✓ 发布异常案例: {len(deployment_cases)} 个")

    # 4. 延迟案例（至少 1 个）
    latency_cases = get_cases_by_tag("latency")
    assert len(latency_cases) >= 1, "应该至少有 1 个延迟案例"
    print(f"✓ 延迟案例: {len(latency_cases)} 个")

    # 5. 证据不足案例（至少 1 个）
    insufficient_cases = get_cases_by_tag("insufficient_evidence")
    assert len(insufficient_cases) >= 1, "应该至少有 1 个证据不足案例"
    print(f"✓ 证据不足案例: {len(insufficient_cases)} 个")

    # 6. 恶意指令案例（至少 1 个）
    malicious_cases = get_cases_by_tag("malicious")
    assert len(malicious_cases) >= 1, "应该至少有 1 个恶意指令案例"
    print(f"✓ 恶意指令案例: {len(malicious_cases)} 个")

    # 7. 正常业务案例（至少 1 个）
    normal_cases = get_cases_by_tag("normal")
    assert len(normal_cases) >= 1, "应该至少有 1 个正常业务案例"
    print(f"✓ 正常业务案例: {len(normal_cases)} 个")

    # 8. 需要工具证据的案例
    tool_evidence_cases = [c for c in all_cases if c.requires_tool_evidence]
    assert len(tool_evidence_cases) >= 1, "应该至少有 1 个需要工具证据的案例"
    print(f"✓ 需要工具证据案例: {len(tool_evidence_cases)} 个")

    # 9. 需要人工审核的案例
    human_review_cases = [c for c in all_cases if c.expected_human_review]
    assert len(human_review_cases) >= 1, "应该至少有 1 个需要人工审核的案例"
    print(f"✓ 需要人工审核案例: {len(human_review_cases)} 个")

    print()


def verify_malicious_cases():
    """详细验证恶意指令案例"""
    print("=" * 80)
    print("验证恶意指令案例详情")
    print("=" * 80)
    print()

    malicious_cases = get_cases_by_tag("malicious")

    for case in malicious_cases:
        print(f"Case #{case.id}:")
        print(f"  描述: {case.description[:80]}...")
        print(f"  期望严重度: {case.expected_severity} (应忽略注入指令)")
        print(f"  期望人工审核: {case.expected_human_review}")

        # 验证恶意指令不应该被采纳
        assert case.expected_severity == "P3", \
            f"恶意指令案例应该被识别为低优先级，不应采纳注入的 P0"
        assert case.expected_human_review == False, \
            f"恶意指令案例不应触发人工审核"

        print(f"  ✓ 防御设置正确")
        print()


def main():
    """主函数"""
    print("\n🔍 开始验证测试框架...\n")

    try:
        verify_data_structure()
        verify_tag_filtering()
        verify_severity_filtering()
        verify_special_cases()
        verify_malicious_cases()

        print("=" * 80)
        print("✅ 所有验证通过！")
        print("=" * 80)
        print()

        # 打印数据集摘要
        print_test_data_summary()

        print("\n" + "=" * 80)
        print("📊 测试框架就绪，可以运行完整测试")
        print("=" * 80)
        print()
        print("运行完整测试:")
        print("  python tests/run_tests.py")
        print()
        print("按标签筛选测试:")
        print("  python tests/test_cases.py --tag payment_5xx")
        print("  python tests/test_cases.py --tag malicious")
        print("  python tests/test_cases.py --tag insufficient_evidence")
        print()

    except AssertionError as e:
        print(f"\n❌ 验证失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
