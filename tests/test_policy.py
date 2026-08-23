#!/usr/bin/env python3
"""
测试 Policy 规则引擎

验证确定性规则能够正确识别和修正模型的错误输出
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from policy import PolicyEngine, PolicyLevel, PolicyAction


def test_policy_engine():
    """测试 Policy 引擎的各项规则"""

    print("=" * 80)
    print("Policy 规则引擎测试")
    print("=" * 80)
    print()

    engine = PolicyEngine()

    # 测试 1: 高优先级必须人工复核
    print("测试 1: 高优先级必须人工复核")
    print("-" * 80)
    result = {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": False,  # 错误：P0 必须人工审核
        "rationale": "支付接口错误率 35%"
    }
    corrected = engine.check_and_enforce("支付接口错误率 35%", result)
    print(f"原始: needs_human_review = {result['needs_human_review']}")
    print(f"修正: needs_human_review = {corrected['needs_human_review']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 2: 未知原因谦逊原则
    print("测试 2: 未知原因谦逊原则")
    print("-" * 80)
    result = {
        "severity": "P2",
        "category": "database",  # 错误：描述说"原因不明"应该是 unknown
        "needs_human_review": False,
        "rationale": "数据库连接问题"
    }
    corrected = engine.check_and_enforce("数据库偶发连接失败，原因不明", result)
    print(f"原始: category = {result['category']}")
    print(f"修正: category = {corrected['category']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 3: 收入影响高优先级
    print("测试 3: 收入影响高优先级")
    print("-" * 80)
    result = {
        "severity": "P2",  # 错误：支付相关至少 P1
        "category": "availability",
        "needs_human_review": False,
        "rationale": "支付接口错误"
    }
    corrected = engine.check_and_enforce("支付接口错误率 15%", result)
    print(f"原始: severity = {result['severity']}")
    print(f"修正: severity = {corrected['severity']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 4: 内部工具优先级限制
    print("测试 4: 内部工具优先级限制")
    print("-" * 80)
    result = {
        "severity": "P1",  # 错误：内部工具最高 P2
        "category": "latency",
        "needs_human_review": True,
        "rationale": "管理后台慢"
    }
    corrected = engine.check_and_enforce("内部管理后台响应慢", result)
    print(f"原始: severity = {result['severity']}")
    print(f"修正: severity = {corrected['severity']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 5: 核心服务宕机必须 P0
    print("测试 5: 核心服务宕机必须 P0")
    print("-" * 80)
    result = {
        "severity": "P1",  # 错误：支付完全宕机必须 P0
        "category": "availability",
        "needs_human_review": True,
        "rationale": "支付服务不可用"
    }
    corrected = engine.check_and_enforce("支付服务完全宕机", result)
    print(f"原始: severity = {result['severity']}")
    print(f"修正: severity = {corrected['severity']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 6: 数据安全必须审核
    print("测试 6: 数据安全必须审核")
    print("-" * 80)
    result = {
        "severity": "P2",
        "category": "unknown",
        "needs_human_review": False,  # 错误：安全相关必须审核
        "rationale": "发现权限漏洞"
    }
    corrected = engine.check_and_enforce("发现用户数据泄露风险", result)
    print(f"原始: needs_human_review = {result['needs_human_review']}")
    print(f"修正: needs_human_review = {corrected['needs_human_review']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 7: 高错误率阈值
    print("测试 7: 高错误率阈值")
    print("-" * 80)
    result = {
        "severity": "P3",  # 错误：错误率 60% 至少 P1
        "category": "availability",
        "needs_human_review": False,
        "rationale": "接口错误率高"
    }
    corrected = engine.check_and_enforce("接口错误率 60%", result)
    print(f"原始: severity = {result['severity']}")
    print(f"修正: severity = {corrected['severity']}")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    if engine.violations:
        for v in engine.violations:
            print(f"  - {v.policy_name}: {v.message}")
    print()

    # 测试 8: 无违反的情况
    print("测试 8: 无违反的正常情况")
    print("-" * 80)
    result = {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": True,
        "rationale": "支付接口错误率 35%，直接影响收入"
    }
    corrected = engine.check_and_enforce("支付接口错误率 35%", result)
    print(f"结果: 无修正")
    print(f"✓ 规则违反: {len(engine.violations)} 项")
    print()

    print("=" * 80)
    print("✅ Policy 规则引擎测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_policy_engine()
