"""
A/B 对比工具

对比两次评测结果，量化优化效果
"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Improvement:
    """改进指标"""
    metric: str
    baseline: float
    optimized: float
    delta: float
    percent_change: float
    improved: bool  # True 表示改进，False 表示退化


class ABComparator:
    """
    A/B 对比工具

    对比两次评测结果，量化优化效果
    """

    def __init__(self):
        self.metrics = [
            "accuracy",
            "acceptable_rate",
            "severity_accuracy",
            "category_accuracy",
            "p0_accuracy",
            "p1_accuracy",
        ]

        self.metric_names = {
            "accuracy": "整体准确率",
            "acceptable_rate": "可接受率",
            "severity_accuracy": "严重程度准确率",
            "category_accuracy": "类别准确率",
            "p0_accuracy": "P0 准确率",
            "p1_accuracy": "P1 准确率",
        }

    def compare_reports(
        self,
        baseline_file: str,
        optimized_file: str
    ) -> Dict[str, Any]:
        """
        对比两个评测报告

        Args:
            baseline_file: 基线报告文件（JSON）
            optimized_file: 优化后报告文件（JSON）

        Returns:
            对比结果
        """
        # 加载报告
        with open(baseline_file, 'r', encoding='utf-8') as f:
            baseline = json.load(f)

        with open(optimized_file, 'r', encoding='utf-8') as f:
            optimized = json.load(f)

        base_summary = baseline["summary"]
        opt_summary = optimized["summary"]

        # 计算改进
        improvements = {}

        for metric in self.metrics:
            base_val = base_summary.get(metric, 0)
            opt_val = opt_summary.get(metric, 0)

            if base_val > 0:
                delta = opt_val - base_val
                pct_change = (delta / base_val) * 100
            else:
                delta = opt_val
                pct_change = 0

            improvements[metric] = Improvement(
                metric=metric,
                baseline=base_val,
                optimized=opt_val,
                delta=delta,
                percent_change=pct_change,
                improved=(delta > 0)
            )

        # 对比失败案例
        base_results = {r["test_id"]: r for r in baseline["results"]}
        opt_results = {r["test_id"]: r for r in optimized["results"]}

        fixed_cases = []
        new_failures = []
        still_failing = []

        for test_id in base_results:
            base_r = base_results[test_id]
            opt_r = opt_results.get(test_id)

            if not opt_r:
                continue

            base_acceptable = base_r.get("is_acceptable", False)
            opt_acceptable = opt_r.get("is_acceptable", False)

            # 基线失败，优化后成功
            if not base_acceptable and opt_acceptable:
                fixed_cases.append({
                    "test_id": test_id,
                    "description": base_r["description"],
                    "baseline": base_r["actual"]["severity"],
                    "optimized": opt_r["actual"]["severity"],
                    "expected": base_r["expected"]["severity"]
                })

            # 基线成功，优化后失败
            elif base_acceptable and not opt_acceptable:
                new_failures.append({
                    "test_id": test_id,
                    "description": base_r["description"],
                    "baseline": base_r["actual"]["severity"],
                    "optimized": opt_r["actual"]["severity"],
                    "expected": base_r["expected"]["severity"]
                })

            # 都失败
            elif not base_acceptable and not opt_acceptable:
                still_failing.append({
                    "test_id": test_id,
                    "description": base_r["description"],
                    "baseline": base_r["actual"]["severity"],
                    "optimized": opt_r["actual"]["severity"],
                    "expected": base_r["expected"]["severity"]
                })

        # 性能对比
        base_perf = baseline.get("performance", {})
        opt_perf = optimized.get("performance", {})

        performance_comparison = {
            "avg_duration": {
                "baseline": base_perf.get("avg_duration", 0),
                "optimized": opt_perf.get("avg_duration", 0),
                "delta": opt_perf.get("avg_duration", 0) - base_perf.get("avg_duration", 0)
            },
            "p95_duration": {
                "baseline": base_perf.get("p95_duration", 0),
                "optimized": opt_perf.get("p95_duration", 0),
                "delta": opt_perf.get("p95_duration", 0) - base_perf.get("p95_duration", 0)
            }
        }

        # 生成总结
        summary = self._generate_summary(
            improvements,
            fixed_cases,
            new_failures,
            still_failing,
            performance_comparison
        )

        return {
            "baseline_report": baseline["metadata"]["report_id"],
            "optimized_report": optimized["metadata"]["report_id"],
            "improvements": improvements,
            "fixed_cases": fixed_cases,
            "new_failures": new_failures,
            "still_failing": still_failing,
            "performance": performance_comparison,
            "summary": summary,
            "recommendation": self._generate_recommendation(
                improvements,
                fixed_cases,
                new_failures
            )
        }

    def _generate_summary(
        self,
        improvements: Dict[str, Improvement],
        fixed: List[Dict],
        new_failures: List[Dict],
        still_failing: List[Dict],
        performance: Dict[str, Dict]
    ) -> str:
        """生成对比摘要"""
        lines = []

        # 整体改进
        accuracy_imp = improvements["accuracy"]
        if accuracy_imp.improved:
            lines.append(f"✅ 准确率提升 {accuracy_imp.percent_change:.1f}% ({accuracy_imp.baseline:.1%} → {accuracy_imp.optimized:.1%})")
        elif accuracy_imp.delta < 0:
            lines.append(f"⚠️ 准确率下降 {abs(accuracy_imp.percent_change):.1f}% ({accuracy_imp.baseline:.1%} → {accuracy_imp.optimized:.1%})")
        else:
            lines.append(f"→ 准确率无变化 ({accuracy_imp.baseline:.1%})")

        # P0/P1 改进
        p0_imp = improvements.get("p0_accuracy")
        p1_imp = improvements.get("p1_accuracy")

        if p0_imp and p0_imp.baseline > 0:
            if p0_imp.improved:
                lines.append(f"✅ P0 准确率提升 {p0_imp.percent_change:.1f}% ({p0_imp.baseline:.1%} → {p0_imp.optimized:.1%})")
            elif p0_imp.delta < 0:
                lines.append(f"⚠️ P0 准确率下降 {abs(p0_imp.percent_change):.1f}% ({p0_imp.baseline:.1%} → {p0_imp.optimized:.1%})")

        if p1_imp and p1_imp.baseline > 0:
            if p1_imp.improved:
                lines.append(f"✅ P1 准确率提升 {p1_imp.percent_change:.1f}% ({p1_imp.baseline:.1%} → {p1_imp.optimized:.1%})")
            elif p1_imp.delta < 0:
                lines.append(f"⚠️ P1 准确率下降 {abs(p1_imp.percent_change):.1f}% ({p1_imp.baseline:.1%} → {p1_imp.optimized:.1%})")

        # 修复的案例
        if fixed:
            lines.append(f"🔧 修复 {len(fixed)} 个失败案例")

        # 新增失败
        if new_failures:
            lines.append(f"⚠️ 引入 {len(new_failures)} 个新失败")

        # 仍然失败
        if still_failing:
            lines.append(f"📌 仍有 {len(still_failing)} 个案例失败")

        # 性能变化
        avg_delta = performance["avg_duration"]["delta"]
        if avg_delta < 0:
            lines.append(f"⚡ 平均延迟降低 {abs(avg_delta):.2f}s")
        elif avg_delta > 0:
            lines.append(f"⚠️ 平均延迟增加 {avg_delta:.2f}s")

        return "\n".join(lines)

    def _generate_recommendation(
        self,
        improvements: Dict[str, Improvement],
        fixed: List[Dict],
        new_failures: List[Dict]
    ) -> str:
        """
        生成推荐建议

        Args:
            improvements: 改进指标
            fixed: 修复的案例
            new_failures: 新增失败

        Returns:
            推荐建议
        """
        accuracy_imp = improvements["accuracy"]

        # 判断是否推荐采纳
        if accuracy_imp.delta > 0.05 and not new_failures:
            return "✅ 推荐采纳：准确率显著提升且无副作用"

        elif accuracy_imp.delta > 0 and len(new_failures) < len(fixed):
            return "✅ 推荐采纳：整体改进，新失败少于修复数"

        elif accuracy_imp.delta > 0 and new_failures:
            return "⚠️ 谨慎采纳：有改进但引入了新失败，建议分析新失败案例"

        elif accuracy_imp.delta == 0:
            if fixed and not new_failures:
                return "✅ 可以采纳：修复了部分案例且无副作用"
            elif not fixed and not new_failures:
                return "→ 无明显效果：优化未生效，建议重新分析"
            else:
                return "⚠️ 不推荐：无整体改进且引入新问题"

        else:  # accuracy_imp.delta < 0
            return "❌ 不推荐采纳：准确率下降，建议回滚重新优化"

    def print_comparison(self, comparison: Dict[str, Any]):
        """
        打印对比报告

        Args:
            comparison: 对比结果
        """
        print("\n" + "=" * 60)
        print("A/B 对比报告")
        print("=" * 60)

        print(f"\n基线版本: {comparison['baseline_report']}")
        print(f"优化版本: {comparison['optimized_report']}")

        print(f"\n摘要:")
        print(comparison["summary"])

        print(f"\n详细指标变化:")
        for metric, imp in comparison["improvements"].items():
            metric_name = self.metric_names.get(metric, metric)

            base = imp.baseline * 100
            opt = imp.optimized * 100
            delta = imp.delta * 100

            if imp.improved:
                symbol = "✅"
            elif delta < 0:
                symbol = "⚠️"
            else:
                symbol = "→"

            print(f"  {symbol} {metric_name}:")
            print(f"     基线: {base:.1f}%")
            print(f"     优化: {opt:.1f}%")
            print(f"     变化: {delta:+.1f}%")

        # 性能对比
        perf = comparison["performance"]
        print(f"\n性能对比:")
        print(f"  平均延迟:")
        print(f"    基线: {perf['avg_duration']['baseline']:.2f}s")
        print(f"    优化: {perf['avg_duration']['optimized']:.2f}s")
        print(f"    变化: {perf['avg_duration']['delta']:+.2f}s")

        print(f"  P95 延迟:")
        print(f"    基线: {perf['p95_duration']['baseline']:.2f}s")
        print(f"    优化: {perf['p95_duration']['optimized']:.2f}s")
        print(f"    变化: {perf['p95_duration']['delta']:+.2f}s")

        # 修复的案例
        if comparison["fixed_cases"]:
            print(f"\n修复的案例 ({len(comparison['fixed_cases'])} 个):")
            for case in comparison["fixed_cases"][:5]:
                print(f"  ✅ [{case['test_id']}] {case['description'][:50]}...")
                print(f"     {case['baseline']} → {case['optimized']} (期望 {case['expected']})")
            if len(comparison["fixed_cases"]) > 5:
                print(f"  ... 还有 {len(comparison['fixed_cases']) - 5} 个")

        # 新增失败
        if comparison["new_failures"]:
            print(f"\n新增失败 ({len(comparison['new_failures'])} 个):")
            for case in comparison["new_failures"]:
                print(f"  ⚠️ [{case['test_id']}] {case['description'][:50]}...")
                print(f"     {case['baseline']} → {case['optimized']} (期望 {case['expected']})")

        # 仍然失败
        if comparison["still_failing"]:
            print(f"\n仍然失败 ({len(comparison['still_failing'])} 个):")
            for case in comparison["still_failing"][:3]:
                print(f"  📌 [{case['test_id']}] {case['description'][:50]}...")
            if len(comparison["still_failing"]) > 3:
                print(f"  ... 还有 {len(comparison['still_failing']) - 3} 个")

        # 推荐
        print(f"\n推荐:")
        print(f"  {comparison['recommendation']}")

        print("\n" + "=" * 60)

    def save_comparison_json(
        self,
        comparison: Dict[str, Any],
        filepath: str
    ):
        """
        保存对比结果为 JSON

        Args:
            comparison: 对比结果
            filepath: 保存路径
        """
        # 转换 Improvement 对象为字典
        comparison_dict = {
            "baseline_report": comparison["baseline_report"],
            "optimized_report": comparison["optimized_report"],
            "improvements": {
                metric: {
                    "metric": imp.metric,
                    "baseline": imp.baseline,
                    "optimized": imp.optimized,
                    "delta": imp.delta,
                    "percent_change": imp.percent_change,
                    "improved": imp.improved
                }
                for metric, imp in comparison["improvements"].items()
            },
            "fixed_cases": comparison["fixed_cases"],
            "new_failures": comparison["new_failures"],
            "still_failing": comparison["still_failing"],
            "performance": comparison["performance"],
            "summary": comparison["summary"],
            "recommendation": comparison["recommendation"]
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comparison_dict, f, indent=2, ensure_ascii=False)

        print(f"\n对比结果已保存到: {filepath}")


if __name__ == "__main__":
    """
    使用示例
    """
    print("A/B 对比工具使用示例:")
    print("\nfrom tests.ab_comparator import ABComparator")
    print("")
    print("# 1. 创建对比器")
    print("comparator = ABComparator()")
    print("")
    print("# 2. 对比两个报告")
    print("comparison = comparator.compare_reports(")
    print("    'outputs/evaluations/baseline.json',")
    print("    'outputs/evaluations/optimized.json'")
    print(")")
    print("")
    print("# 3. 查看对比结果")
    print("comparator.print_comparison(comparison)")
    print("")
    print("# 4. 保存对比结果")
    print("comparator.save_comparison_json(comparison, 'outputs/comparisons/ab_comparison.json')")
