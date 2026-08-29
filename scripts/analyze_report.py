#!/usr/bin/env python3
"""
分析已有的评测报告

适用场景：
- 已经运行过评测，有 JSON 报告文件
- 想单独分析失败案例
- 不需要重新运行评测
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.failure_analyzer import FailureAnalyzer
from tests.evaluation_framework import EvaluationReport, TestResult
from datetime import datetime


def load_report_from_json(filepath: str) -> EvaluationReport:
    """
    从 JSON 文件加载评测报告

    Args:
        filepath: 报告文件路径

    Returns:
        EvaluationReport 对象
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 重建 TestResult 列表
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

    # 重建 EvaluationReport
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
    print("分析已有评测报告")
    print("=" * 60)

    # 1. 选择报告文件
    print("\n步骤 1: 选择评测报告")
    print("-" * 60)

    # 列出可用的报告
    eval_dir = Path("outputs/evaluations")
    if eval_dir.exists():
        json_files = sorted(eval_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

        if json_files:
            print("\n可用的评测报告（按时间倒序）:")
            for i, f in enumerate(json_files[:10], 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                size = f.stat().st_size
                print(f"  {i}. {f.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')}, {size} bytes)")

            if len(json_files) > 10:
                print(f"  ... 还有 {len(json_files) - 10} 个报告")

            print("\n选择:")
            choice = input(f"  输入编号 (1-{min(10, len(json_files))}) 或完整路径 (默认: 1): ").strip()

            if not choice:
                choice = "1"

            # 判断是编号还是路径
            if choice.isdigit() and 1 <= int(choice) <= len(json_files):
                report_file = str(json_files[int(choice) - 1])
            else:
                report_file = choice
        else:
            print("\n⚠️ outputs/evaluations/ 目录下没有找到报告文件")
            report_file = input("请输入报告文件路径: ").strip()
    else:
        print("\n⚠️ outputs/evaluations/ 目录不存在")
        report_file = input("请输入报告文件路径: ").strip()

    # 2. 加载报告
    print("\n步骤 2: 加载评测报告")
    print("-" * 60)

    if not Path(report_file).exists():
        print(f"\n❌ 报告文件不存在: {report_file}")
        return 1

    try:
        report = load_report_from_json(report_file)
        print(f"\n✅ 成功加载报告: {report.report_id}")
        print(f"   Agent 版本: {report.agent_version}")
        print(f"   总案例数: {report.total_cases}")
        print(f"   失败案例: {report.failed}")
    except Exception as e:
        print(f"\n❌ 加载报告失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 3. 分析失败案例
    print("\n步骤 3: 分析失败案例")
    print("-" * 60)

    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze_failures(report)

    # 4. 打印分析结果
    analyzer.print_analysis(analysis)

    # 5. 保存分析结果
    print("\n步骤 4: 保存分析结果")
    print("-" * 60)

    output_dir = Path("outputs/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis_file = output_dir / f"analysis_{report.report_id}.json"
    analyzer.save_analysis_json(analysis, str(analysis_file))

    # 6. 显示优化建议
    if analysis["total_failures"] > 0:
        print("\n步骤 5: 优化建议")
        print("-" * 60)
        print("\n根据失败分析，建议按以下步骤优化:")
        print("")

        for i, suggestion in enumerate(analysis["suggestions"], 1):
            print(f"{i}. [{suggestion['severity']}] {suggestion['pattern']}")
            print(f"   影响: {suggestion['impact']}")
            print(f"   建议: {suggestion['suggestion']}")
            print("")

        print("优化方法:")
        print("  - 优化提示词: 修改 src/incident_classifier_v1.py")
        print("  - 调整规则: 修改 src/policy.py")
        print("  - 换模型: 修改 .env 中的 OPENAI_MODEL")
        print("")
        print("优化后，运行评测并使用以下命令对比:")
        print("  python scripts/run_optimization_flow.py")
        print("  选择模式 3（仅对比）")

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
