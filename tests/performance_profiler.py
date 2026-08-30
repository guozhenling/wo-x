"""
性能分析器

分析系统性能瓶颈，生成优化建议
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from tests.test_cases import EvaluationTestCase
from tests.evaluation_framework import EvaluationReport


@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 延迟统计
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    p50_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0

    # API 调用统计
    total_api_calls: int = 0
    avg_api_calls: float = 0.0

    # 瓶颈分析
    bottleneck: str = ""
    bottleneck_duration: float = 0.0
    bottleneck_percentage: float = 0.0


class PerformanceProfiler:
    """
    性能分析器

    分析系统性能，识别瓶颈，生成优化建议
    """

    def __init__(self):
        self.metrics_history = []

    def profile_from_report(
        self,
        report: EvaluationReport
    ) -> Dict[str, Any]:
        """
        从评测报告分析性能

        Args:
            report: 评测报告

        Returns:
            性能分析结果
        """
        # 提取延迟数据
        durations = [r.duration for r in report.results]
        durations.sort()

        n = len(durations)

        # 计算指标
        metrics = PerformanceMetrics(
            total_duration=sum(durations),
            avg_duration=sum(durations) / n if n > 0 else 0,
            min_duration=min(durations) if durations else 0,
            max_duration=max(durations) if durations else 0,
            p50_duration=durations[int(n * 0.5)] if durations else 0,
            p95_duration=durations[int(n * 0.95)] if durations else 0,
            p99_duration=durations[int(n * 0.99)] if durations else 0,
            total_api_calls=0,  # 从报告中提取
            avg_api_calls=0,
        )

        # 识别瓶颈
        bottleneck = self._identify_bottleneck(metrics, report)

        # 生成优化建议
        suggestions = self._generate_performance_suggestions(metrics, bottleneck)

        return {
            "report_id": report.report_id,
            "metrics": {
                "latency": {
                    "avg": metrics.avg_duration,
                    "p50": metrics.p50_duration,
                    "p95": metrics.p95_duration,
                    "p99": metrics.p99_duration,
                    "min": metrics.min_duration,
                    "max": metrics.max_duration,
                },
                "api_usage": {
                    "total_calls": metrics.total_api_calls,
                    "avg_calls_per_request": metrics.avg_api_calls,
                }
            },
            "bottleneck": bottleneck,
            "suggestions": suggestions,
            "summary": self._generate_performance_summary(metrics, bottleneck)
        }

    def _identify_bottleneck(
        self,
        metrics: PerformanceMetrics,
        report: EvaluationReport
    ) -> Dict[str, Any]:
        """识别性能瓶颈"""
        bottleneck = {
            "type": "unknown",
            "description": "",
            "impact": "",
            "severity": "low"
        }

        # 检查 P95 延迟
        if metrics.p95_duration > 30:
            bottleneck = {
                "type": "high_latency",
                "description": f"P95 延迟过高 ({metrics.p95_duration:.1f}s)",
                "impact": "95% 的请求超过 30 秒，用户体验差",
                "severity": "high"
            }
        elif metrics.p95_duration > 20:
            bottleneck = {
                "type": "high_latency",
                "description": f"P95 延迟偏高 ({metrics.p95_duration:.1f}s)",
                "impact": "用户等待时间较长",
                "severity": "medium"
            }

        # 检查最大延迟
        if metrics.max_duration > metrics.avg_duration * 3:
            if bottleneck["severity"] != "high":
                bottleneck = {
                    "type": "outlier",
                    "description": f"存在异常慢的请求 (最大 {metrics.max_duration:.1f}s, 平均 {metrics.avg_duration:.1f}s)",
                    "impact": "部分请求超时或极慢",
                    "severity": "medium"
                }

        return bottleneck

    def _generate_performance_suggestions(
        self,
        metrics: PerformanceMetrics,
        bottleneck: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成性能优化建议"""
        suggestions = []

        # 基于瓶颈类型生成建议
        if bottleneck["type"] == "high_latency":
            if metrics.p95_duration > 30:
                suggestions.append({
                    "priority": 1,
                    "category": "延迟优化",
                    "title": "P95 延迟过高，需要优化",
                    "current": f"P95 = {metrics.p95_duration:.1f}s",
                    "target": "P95 < 20s",
                    "methods": [
                        "增加结果缓存（相同查询直接返回）",
                        "优化工具并发（增加 max_workers）",
                        "增加超时保护（跳过慢工具）",
                        "使用更快的模型（如果准确率允许）"
                    ]
                })
            elif metrics.p95_duration > 20:
                suggestions.append({
                    "priority": 2,
                    "category": "延迟优化",
                    "title": "P95 延迟偏高，建议优化",
                    "current": f"P95 = {metrics.p95_duration:.1f}s",
                    "target": "P95 < 15s",
                    "methods": [
                        "检查是否有慢工具（增加缓存）",
                        "优化 LLM 调用次数（合并步骤）",
                        "调整工具超时时间（当前 5s）"
                    ]
                })

        if bottleneck["type"] == "outlier":
            suggestions.append({
                "priority": 2,
                "category": "稳定性",
                "title": "存在异常慢的请求",
                "current": f"最大 {metrics.max_duration:.1f}s, 平均 {metrics.avg_duration:.1f}s",
                "target": "最大延迟 < 平均延迟的 2 倍",
                "methods": [
                    "增加超时保护（防止单个请求过慢）",
                    "检查是否有特定类型的查询慢（优化工具）",
                    "增加降级机制（超时后返回缓存或默认结果）"
                ]
            })

        # 通用建议
        if metrics.avg_duration > 15:
            suggestions.append({
                "priority": 3,
                "category": "整体优化",
                "title": "平均延迟较高",
                "current": f"平均 = {metrics.avg_duration:.1f}s",
                "target": "平均 < 15s",
                "methods": [
                    "减少 LLM 调用次数（当前 3 次：初步分类、工具规划、综合分析）",
                    "增加缓存覆盖率（当前可能较低）",
                    "优化提示词长度（减少 token 消耗）"
                ]
            })

        return suggestions

    def _generate_performance_summary(
        self,
        metrics: PerformanceMetrics,
        bottleneck: Dict[str, Any]
    ) -> str:
        """生成性能摘要"""
        lines = []

        lines.append(f"平均延迟: {metrics.avg_duration:.1f}s")
        lines.append(f"P95 延迟: {metrics.p95_duration:.1f}s")

        if bottleneck["severity"] == "high":
            lines.append(f"\n⚠️ 严重性能问题: {bottleneck['description']}")
        elif bottleneck["severity"] == "medium":
            lines.append(f"\n⚠️ 性能瓶颈: {bottleneck['description']}")
        else:
            lines.append(f"\n✅ 性能表现正常")

        return "\n".join(lines)

    def print_profile(self, profile: Dict[str, Any]):
        """打印性能分析报告"""
        print("\n" + "=" * 60)
        print("性能分析报告")
        print("=" * 60)

        print(f"\n报告 ID: {profile['report_id']}")

        # 延迟统计
        latency = profile["metrics"]["latency"]
        print(f"\n延迟统计:")
        print(f"  平均: {latency['avg']:.2f}s")
        print(f"  P50:  {latency['p50']:.2f}s")
        print(f"  P95:  {latency['p95']:.2f}s")
        print(f"  P99:  {latency['p99']:.2f}s")
        print(f"  范围: {latency['min']:.2f}s - {latency['max']:.2f}s")

        # 瓶颈分析
        bottleneck = profile["bottleneck"]
        if bottleneck["severity"] != "low":
            print(f"\n性能瓶颈:")
            print(f"  类型: {bottleneck['type']}")
            print(f"  描述: {bottleneck['description']}")
            print(f"  影响: {bottleneck['impact']}")
            print(f"  严重程度: {bottleneck['severity']}")
        else:
            print(f"\n✅ 未发现明显性能瓶颈")

        # 优化建议
        if profile["suggestions"]:
            print(f"\n优化建议:")
            for suggestion in profile["suggestions"]:
                print(f"\n  {suggestion['priority']}. [{suggestion['category']}] {suggestion['title']}")
                print(f"     当前: {suggestion['current']}")
                print(f"     目标: {suggestion['target']}")
                print(f"     方法:")
                for method in suggestion["methods"]:
                    print(f"       - {method}")

        print("\n" + "=" * 60)

    def save_profile_json(
        self,
        profile: Dict[str, Any],
        filepath: str
    ):
        """保存性能分析结果"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        print(f"\n性能分析已保存到: {filepath}")


if __name__ == "__main__":
    """
    使用示例
    """
    print("性能分析器使用示例:")
    print("\nfrom tests.performance_profiler import PerformanceProfiler")
    print("from tests.evaluation_framework import EvaluationFramework")
    print("")
    print("# 1. 运行评测")
    print("framework = EvaluationFramework(agent)")
    print("report = framework.run_evaluation()")
    print("")
    print("# 2. 性能分析")
    print("profiler = PerformanceProfiler()")
    print("profile = profiler.profile_from_report(report)")
    print("")
    print("# 3. 查看分析结果")
    print("profiler.print_profile(profile)")
    print("")
    print("# 4. 保存分析结果")
    print("profiler.save_profile_json(profile, 'outputs/performance/profile.json')")
