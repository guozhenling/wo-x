#!/usr/bin/env python3
"""
性能测试脚本 - Day 13

测量系统性能并生成报告
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from src.incident_classifier_v1 import IncidentClassifierV1


class PerformanceTester:
    """性能测试器"""

    def __init__(self):
        self.classifier = IncidentClassifierV1(trace_dir="traces/perf")
        self.results = []

    def run_test_case(self, description: str, label: str) -> Dict[str, Any]:
        """
        运行单个测试案例

        Args:
            description: 故障描述
            label: 测试标签

        Returns:
            性能指标
        """
        print(f"\n测试案例: {label}")
        print(f"描述: {description}")
        print("-" * 60)

        start_time = time.time()
        result = self.classifier.classify(description)
        duration = time.time() - start_time

        metrics = {
            "label": label,
            "description": description,
            "duration": round(duration, 3),
            "success": result['success'],
            "severity": result['classification']['severity'],
            "category": result['classification']['category'],
            "tool_calls": result['performance']['tool_calls'],
            "success_rate": result['performance']['success_rate'],
            "cache_hit_rate": result['performance']['cache_hit_rate'],
            "avg_tool_time": result['performance']['avg_tool_time']
        }

        self.results.append(metrics)

        print(f"✓ 完成")
        print(f"  耗时: {metrics['duration']}s")
        print(f"  工具调用: {metrics['tool_calls']}")
        print(f"  成功率: {metrics['success_rate']:.1%}")
        print(f"  缓存命中率: {metrics['cache_hit_rate']:.1%}")

        return metrics

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有测试案例"""
        print("=" * 80)
        print("性能测试 - Day 13")
        print("=" * 80)

        test_cases = [
            ("支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟", "P0-支付故障"),
            ("推荐系统 P99 延迟从 500ms 升至 2 秒，超时率 15%", "P1-延迟问题"),
            ("MySQL 报 1205 死锁错误，影响订单创建，每分钟 20 次", "P1-数据库死锁"),
            ("recommendation 服务 Pod 频繁 OOMKilled，重启 5 次", "P1-OOM问题"),
            ("用户头像上传偶尔失败，错误率 2%", "P2-小故障"),
            ("日志中发现少量 404 错误，错误率 0.5%，已恢复", "P3-低错误率"),
            ("搜索接口超时率 20%，影响用户体验", "P1-搜索超时"),
            ("广告服务响应缓慢，P95 延迟 3 秒", "P1-广告延迟"),
            ("订单服务部署后错误率上升到 5%", "P1-部署问题"),
            ("数据库慢查询数量激增，最慢查询 10 秒", "P1-慢查询"),
        ]

        for description, label in test_cases:
            try:
                self.run_test_case(description, label)
            except Exception as e:
                print(f"✗ 测试失败: {e}")
                self.results.append({
                    "label": label,
                    "description": description,
                    "duration": 0,
                    "success": False,
                    "error": str(e)
                })

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        print("\n" + "=" * 80)
        print("性能报告")
        print("=" * 80)

        if not self.results:
            print("无测试结果")
            return {}

        # 统计
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get('success', False))
        failed_tests = total_tests - successful_tests

        durations = [r['duration'] for r in self.results if r.get('success', False)]
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        tool_calls = [r['tool_calls'] for r in self.results if r.get('success', False)]
        avg_tool_calls = sum(tool_calls) / len(tool_calls) if tool_calls else 0

        success_rates = [r['success_rate'] for r in self.results if r.get('success', False)]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

        cache_hit_rates = [r['cache_hit_rate'] for r in self.results if r.get('success', False)]
        avg_cache_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates) if cache_hit_rates else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": round(successful_tests / total_tests, 3) if total_tests > 0 else 0
            },
            "performance": {
                "avg_duration": round(avg_duration, 3),
                "min_duration": round(min_duration, 3),
                "max_duration": round(max_duration, 3),
                "avg_tool_calls": round(avg_tool_calls, 1),
                "avg_tool_success_rate": round(avg_success_rate, 3),
                "avg_cache_hit_rate": round(avg_cache_hit_rate, 3)
            },
            "details": self.results
        }

        # 输出报告
        print(f"\n总体统计:")
        print(f"  测试总数: {report['summary']['total_tests']}")
        print(f"  成功: {report['summary']['successful_tests']}")
        print(f"  失败: {report['summary']['failed_tests']}")
        print(f"  成功率: {report['summary']['success_rate']:.1%}")

        print(f"\n性能指标:")
        print(f"  平均耗时: {report['performance']['avg_duration']:.3f}s")
        print(f"  最快: {report['performance']['min_duration']:.3f}s")
        print(f"  最慢: {report['performance']['max_duration']:.3f}s")
        print(f"  平均工具调用: {report['performance']['avg_tool_calls']:.1f}")
        print(f"  平均工具成功率: {report['performance']['avg_tool_success_rate']:.1%}")
        print(f"  平均缓存命中率: {report['performance']['avg_cache_hit_rate']:.1%}")

        print(f"\n详细结果:")
        print(f"{'标签':<20} {'耗时(s)':<10} {'工具调用':<10} {'成功率':<10} {'缓存命中':<10}")
        print("-" * 80)
        for r in self.results:
            if r.get('success', False):
                print(f"{r['label']:<20} {r['duration']:<10.3f} {r['tool_calls']:<10} "
                      f"{r['success_rate']:<10.1%} {r['cache_hit_rate']:<10.1%}")

        return report

    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        report_dir = Path("reports/performance")
        report_dir.mkdir(parents=True, exist_ok=True)

        filepath = report_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 报告已保存: {filepath}")
        return str(filepath)


def main():
    """主函数"""
    tester = PerformanceTester()

    # 运行测试
    results = tester.run_all_tests()

    # 生成报告
    report = tester.generate_report()

    # 保存报告
    tester.save_report(report)

    print("\n" + "=" * 80)
    print("性能测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
