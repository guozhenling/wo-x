#!/usr/bin/env python3
"""
测试 Policy 监控埋点

验证 src/policy.py 的结构化日志输出是否正确。

运行测试：
    python test_policy_monitoring.py

生成测试日志：
    python test_policy_monitoring.py 2>&1 | grep '^{' > sample_policy.log

分析日志：
    python analyze_policy_logs.py sample_policy.log

测试场景：
    1. P0 未标记人工审核 -> 触发 CRITICAL 规则
    2. 支付高错误率 35% -> 触发收入影响规则，P1->P0
    3. 正确分类 -> 无规则违反
    4. 低错误率支付 3% -> 不触发规则（验证阈值优化）
"""

import sys
import json
import logging
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from policy import PolicyEngine

# 配置日志输出到控制台（JSON 格式）
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # 只输出消息本身（JSON）
    handlers=[logging.StreamHandler()]
)


def test_policy_monitoring():
    """测试 Policy 监控埋点"""
    print("=" * 80)
    print("测试 Policy 监控埋点")
    print("=" * 80)
    print()

    policy = PolicyEngine()

    # 测试案例 1: 触发 CRITICAL 级别规则
    print("测试 1: P0 级别但未标记人工审核（触发 CRITICAL 规则）")
    print("-" * 80)
    result1 = {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": False,
        "rationale": "支付接口完全不可用"
    }
    policy.check_and_enforce("支付接口 500 错误率 100%", result1)
    print()

    # 测试案例 2: 触发收入影响规则（错误率 >= 20%）
    print("测试 2: 支付高错误率（触发收入影响规则）")
    print("-" * 80)
    result2 = {
        "severity": "P1",
        "category": "availability",
        "needs_human_review": True,
        "rationale": "支付接口错误率升高"
    }
    policy.check_and_enforce("支付接口 5xx 从 0.1% 升到 35%", result2)
    print()

    # 测试案例 3: 无规则违反
    print("测试 3: 正确的分类（无规则违反）")
    print("-" * 80)
    result3 = {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": True,
        "rationale": "核心服务完全不可用"
    }
    policy.check_and_enforce("主站完全无法访问，所有用户返回 502", result3)
    print()

    # 测试案例 4: 低错误率支付问题（不触发规则）
    print("测试 4: 低错误率支付问题（错误率 3%，不触发规则）")
    print("-" * 80)
    result4 = {
        "severity": "P2",
        "category": "availability",
        "needs_human_review": False,
        "rationale": "第三方支付渠道偶尔超时，有降级处理"
    }
    policy.check_and_enforce("第三方支付渠道偶尔超时，整体成功率 97%", result4)
    print()

    print("=" * 80)
    print("监控埋点测试完成")
    print("=" * 80)
    print()
    print("日志格式说明:")
    print("  • event: 事件类型")
    print("  • timestamp: 时间戳")
    print("  • duration_ms: 执行耗时")
    print("  • violations: 规则违反详情")
    print("  • changes: 字段修改情况")
    print()
    print("生产环境使用:")
    print("  1. 日志输出到文件: policy.log")
    print("  2. 使用 Filebeat/Fluentd 收集")
    print("  3. 发送到 Elasticsearch/Splunk")
    print("  4. 在 Kibana/Grafana 中可视化")
    print()
    print("简单统计命令:")
    print("  # 统计各规则触发次数")
    print("  cat policy.log | jq -r '.violations[].policy_name' | sort | uniq -c")
    print()
    print("  # 统计 CRITICAL 级别触发")
    print("  cat policy.log | jq 'select(.violations[].level==\"critical\")'")
    print()
    print("  # 统计严重度修正")
    print("  cat policy.log | jq 'select(.changes.severity.changed==true)'")
    print()


if __name__ == "__main__":
    test_policy_monitoring()
