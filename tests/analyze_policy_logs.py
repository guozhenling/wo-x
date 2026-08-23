#!/usr/bin/env python3
"""
Policy 日志分析工具

功能：
    分析 Policy 监控日志，生成统计报告

使用：
    python analyze_policy_logs.py logs/policy.log

    # 定时生成报告（cron）
    0 9 * * * python analyze_policy_logs.py /var/log/policy.log > daily_report.txt

输出指标：
    - 总检查次数、违反次数、违反率
    - 规则触发排行（Top N）
    - 规则级别分布（CRITICAL/HIGH/MEDIUM/LOW）
    - 严重度修正统计（P2->P1, P1->P0）
    - CRITICAL 告警详情
    - 执行性能（平均/最大耗时）
    - 分析建议（自动识别异常）

分析建议：
    - 违反率 >50%: 模型质量问题或规则过严
    - CRITICAL 触发过多: 检查模型配置
    - 执行耗时 >10ms: 优化规则逻辑
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any


def analyze_policy_logs(log_file: str) -> Dict[str, Any]:
    """分析 Policy 日志文件"""

    # 统计数据
    total_checks = 0
    total_violations = 0
    violations_by_policy = defaultdict(int)
    violations_by_level = defaultdict(int)
    severity_corrections = defaultdict(int)
    critical_violations = []
    durations = []

    # 读取日志
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                log = json.loads(line)
                event = log.get('event')

                if event == 'policy_violations':
                    total_checks += 1
                    total_violations += log.get('total_violations', 0)
                    durations.append(log.get('duration_ms', 0))

                    # 统计各规则触发次数
                    for v in log.get('violations', []):
                        policy_name = v['policy_name']
                        level = v['level']
                        violations_by_policy[policy_name] += 1
                        violations_by_level[level] += 1

                    # 统计严重度修正
                    changes = log.get('changes', {})
                    if changes.get('severity', {}).get('changed'):
                        original = changes['severity']['original']
                        final = changes['severity']['final']
                        key = f"{original} -> {final}"
                        severity_corrections[key] += 1

                elif event == 'critical_policy_violation':
                    critical_violations.append(log)

                elif event == 'policy_check_no_violation':
                    total_checks += 1
                    durations.append(log.get('duration_ms', 0))

            except json.JSONDecodeError:
                continue

    # 计算统计指标
    violation_rate = (total_violations / total_checks * 100) if total_checks > 0 else 0
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    return {
        "summary": {
            "total_checks": total_checks,
            "total_violations": total_violations,
            "violation_rate": round(violation_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "max_duration_ms": round(max_duration, 2),
            "critical_count": len(critical_violations)
        },
        "by_policy": dict(violations_by_policy),
        "by_level": dict(violations_by_level),
        "severity_corrections": dict(severity_corrections),
        "critical_violations": critical_violations
    }


def print_report(analysis: Dict[str, Any]):
    """打印分析报告"""

    summary = analysis['summary']

    print("=" * 80)
    print("Policy 监控分析报告")
    print("=" * 80)
    print()

    # 概览
    print("📊 概览")
    print("-" * 80)
    print(f"总检查次数:     {summary['total_checks']}")
    print(f"总违反次数:     {summary['total_violations']}")
    print(f"违反率:         {summary['violation_rate']}%")
    print(f"平均执行耗时:   {summary['avg_duration_ms']} ms")
    print(f"最大执行耗时:   {summary['max_duration_ms']} ms")
    print(f"CRITICAL 触发:  {summary['critical_count']} 次")
    print()

    # 按规则统计
    print("📋 规则触发排行")
    print("-" * 80)
    by_policy = analysis['by_policy']
    sorted_policies = sorted(by_policy.items(), key=lambda x: x[1], reverse=True)
    for i, (policy, count) in enumerate(sorted_policies, 1):
        percentage = count / summary['total_violations'] * 100 if summary['total_violations'] > 0 else 0
        print(f"{i}. {policy:<40} {count:>5} 次 ({percentage:>5.1f}%)")
    print()

    # 按级别统计
    print("🎯 规则级别分布")
    print("-" * 80)
    by_level = analysis['by_level']
    for level in ['critical', 'high', 'medium', 'low']:
        count = by_level.get(level, 0)
        percentage = count / summary['total_violations'] * 100 if summary['total_violations'] > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"{level.upper():<10} {bar:<50} {count:>5} ({percentage:>5.1f}%)")
    print()

    # 严重度修正
    print("🔄 严重度修正统计")
    print("-" * 80)
    corrections = analysis['severity_corrections']
    if corrections:
        for correction, count in sorted(corrections.items(), key=lambda x: x[1], reverse=True):
            print(f"{correction:<20} {count:>5} 次")
    else:
        print("无严重度修正")
    print()

    # CRITICAL 告警
    if summary['critical_count'] > 0:
        print("⚠️  CRITICAL 告警详情")
        print("-" * 80)
        for i, alert in enumerate(analysis['critical_violations'][:5], 1):
            print(f"{i}. 时间: {alert.get('timestamp')}")
            print(f"   规则: {', '.join(alert.get('policies', []))}")
            print(f"   修正: {alert.get('severity_change')}")
            print()

    # 分析建议
    print("💡 分析建议")
    print("-" * 80)

    if summary['violation_rate'] > 50:
        print("⚠️  违反率过高 (>50%)，可能问题:")
        print("   • 模型输出质量下降")
        print("   • 规则过于严格")
        print("   • 需要重新训练或调整规则")
        print()

    if summary['critical_count'] > summary['total_checks'] * 0.3:
        print("⚠️  CRITICAL 规则触发过多，需要关注:")
        print("   • 检查模型是否正确设置 needs_human_review")
        print("   • 检查收入影响规则的阈值是否合理")
        print()

    if summary['avg_duration_ms'] > 10:
        print("⚠️  Policy 执行耗时较高 (>10ms):")
        print("   • 检查规则逻辑复杂度")
        print("   • 优化正则表达式匹配")
        print()

    if summary['violation_rate'] < 5:
        print("✓ 违反率很低，模型表现良好")
        print()

    print("=" * 80)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python analyze_policy_logs.py <log_file>")
        print()
        print("示例:")
        print("  python analyze_policy_logs.py policy.log")
        print("  python analyze_policy_logs.py /var/log/app/policy.log")
        sys.exit(1)

    log_file = sys.argv[1]

    try:
        analysis = analyze_policy_logs(log_file)
        print_report(analysis)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
