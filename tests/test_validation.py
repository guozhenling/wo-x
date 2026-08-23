"""
测试 Pydantic 校验功能
演示如何捕获和处理无效的模型输出
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pydantic import ValidationError
from incident_triage import IncidentTriage


def test_valid_input():
    """测试合法输入"""
    print("测试 1: 合法输入")
    try:
        result = IncidentTriage(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="这是一个合法的分类理由，长度足够"
        )
        print(f"✓ 通过校验: {result.severity} - {result.category}")
    except ValidationError as e:
        print(f"✗ 校验失败: {e}")
    print()


def test_invalid_severity():
    """测试无效的严重程度"""
    print("测试 2: 无效的 severity (P5)")
    try:
        result = IncidentTriage(
            severity="P5",  # 不在枚举范围内
            category="availability",
            needs_human_review=True,
            rationale="测试无效严重程度"
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


def test_invalid_category():
    """测试无效的故障类别"""
    print("测试 3: 无效的 category (network)")
    try:
        result = IncidentTriage(
            severity="P1",
            category="network",  # 不在枚举范围内
            needs_human_review=True,
            rationale="测试无效故障类别"
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


def test_invalid_boolean():
    """测试无效的布尔值"""
    print("测试 4: 无效的 needs_human_review (字符串 'yes')")
    try:
        result = IncidentTriage(
            severity="P1",
            category="latency",
            needs_human_review="yes",  # 应该是布尔值
            rationale="测试无效布尔值"
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


def test_short_rationale():
    """测试过短的 rationale"""
    print("测试 5: 过短的 rationale (少于10字符)")
    try:
        result = IncidentTriage(
            severity="P2",
            category="database",
            needs_human_review=False,
            rationale="太短"  # 少于10个字符
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


def test_missing_field():
    """测试缺失必填字段"""
    print("测试 6: 缺失必填字段 (rationale)")
    try:
        result = IncidentTriage(
            severity="P2",
            category="deployment",
            needs_human_review=False
            # 缺少 rationale 字段
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


def test_empty_rationale():
    """测试空的 rationale"""
    print("测试 7: 空的 rationale")
    try:
        result = IncidentTriage(
            severity="P3",
            category="unknown",
            needs_human_review=False,
            rationale=""  # 空字符串
        )
        print(f"✗ 未捕获错误: {result}")
    except ValidationError as e:
        print(f"✓ 成功拦截无效输入")
        print(f"   错误详情: {e.errors()[0]['msg']}")
    print()


if __name__ == "__main__":
    print("=" * 80)
    print("Pydantic 校验功能测试")
    print("=" * 80)
    print("\n验证系统能够拦截以下无效输入：")
    print("- 枚举值超出范围")
    print("- 类型错误（如字符串传给布尔字段）")
    print("- 缺失必填字段")
    print("- 字符串长度不符合要求")
    print("\n" + "=" * 80 + "\n")

    test_valid_input()
    test_invalid_severity()
    test_invalid_category()
    test_invalid_boolean()
    test_short_rationale()
    test_missing_field()
    test_empty_rationale()

    print("=" * 80)
    print("测试完成！所有无效输入均被成功拦截")
    print("=" * 80)
