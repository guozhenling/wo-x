#!/usr/bin/env python3
"""
Level 3 高级分析工具集成脚本

集成性能分析、趋势追踪和自动化优化建议
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.performance_profiler import PerformanceProfiler
from tests.trend_tracker import TrendTracker
from tests.optimization_advisor import OptimizationAdvisor
from tests.evaluation_framework import EvaluationFramework
from tests.test_cases import get_test_cases_by_priority
from src.incident_classifier_v1 import IncidentClassifierV1
import json


def load_report_from_json(filepath: str):
    """从 JSON 加载报告"""
    from tests.evaluation_framework import EvaluationReport, TestResult
    from datetime import datetime

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    for r in data["results"]:
        result = TestResult(
            test_id=r["test_id"],
            description=r["description"],
            expected_severity=r["expected"]["severity"],
            actual_severity=r["actual"]["severity"],
            expected_category=r["expected"]["category"],
            actual_category=r["actual"]["category"],
            is_correct=r["is_correct"],
            is_acceptable=r["is_acceptable"],
            duration=r["duration"],
            error=r.get("error", ""),
            timestamp=r.get("timestamp", datetime.now().isoformat())
        )
        results.append(result)

    report = EvaluationReport(
        report_id=data["metadata"]["report_id"],
        agent_version=data["metadata"]["agent_version"],
        total_cases=data["summary"]["total_cases"],
        start_time=data["metadata"]["start_time"],
        end_time=data["metadata"]["end_time"],
        total_duration=data["metadata"]["total_duration"],
        passed=data["summary"]["passed"],
        acceptable=data["summary"]["acceptable"],
        failed=data["summary"]["failed"],
        accuracy=data["summary"]["accuracy"],
        acceptable_rate=data["summary"]["acceptable_rate"],
        severity_correct=int(data["summary"]["severity_accuracy"] * data["summary"]["total_cases"]),
        category_correct=int(data["summary"]["category_accuracy"] * data["summary"]["total_cases"]),
        severity_accuracy=data["summary"]["severity_accuracy"],
        category_accuracy=data["summary"]["category_accuracy"],
        p0_total=data["key_metrics"]["p0_total"],
        p0_correct=data["key_metrics"]["p0_correct"],
        p0_accuracy=data["key_metrics"]["p0_accuracy"],
        p1_total=data["key_metrics"]["p1_total"],
        p1_correct=data["key_metrics"]["p1_correct"],
        p1_accuracy=data["key_metrics"]["p1_accuracy"],
        avg_duration=data["performance"]["avg_duration"],
        p95_duration=data["performance"]["p95_duration"],
        results=results,
        failures=data.get("failures", [])
    )

    return report


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Level 3 高级分析工具")
    print("=" * 60)

    print("\n可用功能:")
    print("  1. 性能分析（分析延迟和瓶颈）")
    print("  2. 趋势追踪（分析多次评测趋势）")
    print("  3. 自动化优化建议（生成具体代码建议）")
    print("  4. 完整分析（运行所有工具）")
    print("")

    mode = input("选择功能 (1/2/3/4，默认 4): ").strip() or "4"

    # 选择报告
    print("\n" + "=" * 60)
    print("选择评测报告")
    print("=" * 60)

    eval_dir = Path("outputs/evaluations")
    if eval_dir.exists():
        json_files = sorted(eval_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

        if json_files:
            print("\n可用的评测报告（按时间倒序）:")
            for i, f in enumerate(json_files[:5], 1):
                from datetime import datetime
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"  {i}. {f.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")

            choice = input(f"\n输入编号 (1-{min(5, len(json_files))}) 或路径 (默认: 1): ").strip() or "1"

            if choice.isdigit() and 1 <= int(choice) <= len(json_files):
                report_file = str(json_files[int(choice) - 1])
            else:
                report_file = choice
        else:
            report_file = input("输入报告文件路径: ").strip()
    else:
        report_file = input("输入报告文件路径: ").strip()

    if not Path(report_file).exists():
        print(f"\n❌ 报告文件不存在: {report_file}")
        return 1

    # 加载报告
    try:
        report = load_report_from_json(report_file)
        print(f"\n✅ 成功加载报告: {report.report_id}")
    except Exception as e:
        print(f"\n❌ 加载报告失败: {e}")
        return 1

    # 执行分析
    if mode == "1":
        # 性能分析
        print("\n" + "=" * 60)
        print("性能分析")
        print("=" * 60)

        profiler = PerformanceProfiler()
        profile = profiler.profile_from_report(report)
        profiler.print_profile(profile)

        # 保存
        output_dir = Path("outputs/performance")
        output_dir.mkdir(parents=True, exist_ok=True)
        profiler.save_profile_json(profile, str(output_dir / f"profile_{report.report_id}.json"))

    elif mode == "2":
        # 趋势追踪
        print("\n" + "=" * 60)
        print("趋势追踪")
        print("=" * 60)

        tracker = TrendTracker()

        # 询问是否添加当前报告
        add = input(f"\n是否将当前报告添加到趋势追踪? (y/n, 默认 y): ").strip().lower() or "y"
        if add == "y":
            tracker.add_report(report_file)

        # 分析趋势
        analysis = tracker.analyze_trends()
        tracker.print_trends(analysis)

        # 生成图表
        if analysis["status"] == "success":
            try:
                tracker.generate_chart()
            except Exception as e:
                print(f"\n⚠️ 生成图表失败: {e}")
                print("   （可能需要安装 matplotlib: pip install matplotlib）")

    elif mode == "3":
        # 自动化优化建议
        print("\n" + "=" * 60)
        print("自动化优化建议")
        print("=" * 60)

        advisor = OptimizationAdvisor()
        advice = advisor.generate_advice(report)
        advisor.print_advice(advice)

    elif mode == "4":
        # 完整分析
        print("\n执行完整分析...")

        # 1. 性能分析
        print("\n" + "=" * 60)
        print("1/3: 性能分析")
        print("=" * 60)

        profiler = PerformanceProfiler()
        profile = profiler.profile_from_report(report)
        profiler.print_profile(profile)

        output_dir = Path("outputs/performance")
        output_dir.mkdir(parents=True, exist_ok=True)
        profiler.save_profile_json(profile, str(output_dir / f"profile_{report.report_id}.json"))

        # 2. 自动化优化建议
        print("\n" + "=" * 60)
        print("2/3: 自动化优化建议")
        print("=" * 60)

        advisor = OptimizationAdvisor()
        advice = advisor.generate_advice(report)
        advisor.print_advice(advice)

        # 3. 趋势追踪
        print("\n" + "=" * 60)
        print("3/3: 趋势追踪")
        print("=" * 60)

        tracker = TrendTracker()
        add = input(f"\n是否将当前报告添加到趋势追踪? (y/n, 默认 y): ").strip().lower() or "y"
        if add == "y":
            tracker.add_report(report_file)

        analysis = tracker.analyze_trends()
        tracker.print_trends(analysis)

        if analysis["status"] == "success":
            try:
                tracker.generate_chart()
            except Exception as e:
                print(f"\n⚠️ 生成图表失败: {e}")
                print("   （可能需要安装 matplotlib: pip install matplotlib）")

    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
