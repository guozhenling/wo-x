#!/usr/bin/env python3
"""
完整的评测、分析和优化流程

集成评测框架、失败分析器和 A/B 对比工具
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.incident_classifier_v1 import IncidentClassifierV1
from tests.test_cases import get_all_cases, get_test_cases_by_priority
from tests.evaluation_framework import EvaluationFramework
from tests.failure_analyzer import FailureAnalyzer
from tests.ab_comparator import ABComparator


def run_baseline_evaluation():
    """运行基线评测"""
    print("\n" + "=" * 60)
    print("步骤 1: 基线评测")
    print("=" * 60)

    # 初始化
    agent = IncidentClassifierV1()
    framework = EvaluationFramework(agent, agent_version="1.0.0")

    # 选择测试集（快速评测：P0 + P1）
    test_cases = (
        get_test_cases_by_priority("P0") +
        get_test_cases_by_priority("P1")
    )

    print(f"\n运行基线评测 ({len(test_cases)} 个案例)...")

    # 运行评测
    report = framework.run_evaluation(test_cases, verbose=True)

    # 打印报告
    framework.print_report(report)

    # 保存报告
    output_dir = Path("outputs/evaluations")
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_file = output_dir / "baseline.json"
    framework.save_report_json(report, str(baseline_file))
    framework.save_report_markdown(report, str(output_dir / "baseline.md"))

    return report, str(baseline_file)


def analyze_failures(report):
    """分析失败案例"""
    print("\n" + "=" * 60)
    print("步骤 2: 失败分析")
    print("=" * 60)

    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze_failures(report)

    # 打印分析结果
    analyzer.print_analysis(analysis)

    # 保存分析结果
    output_dir = Path("outputs/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis_file = output_dir / f"analysis_{report.report_id}.json"
    analyzer.save_analysis_json(analysis, str(analysis_file))

    return analysis


def show_optimization_guide(analysis):
    """显示优化指导"""
    print("\n" + "=" * 60)
    print("步骤 3: 优化指导")
    print("=" * 60)

    if analysis["total_failures"] == 0:
        print("\n✅ 没有失败案例，系统表现优秀！")
        print("\n可选优化方向:")
        print("  1. 提升性能（减少延迟）")
        print("  2. 降低成本（减少 LLM 调用）")
        print("  3. 增加测试案例覆盖")
        return

    print("\n根据失败分析，建议按以下步骤优化:")
    print("")

    for i, suggestion in enumerate(analysis["suggestions"], 1):
        print(f"{i}. [{suggestion['severity']}] {suggestion['pattern']}")
        print(f"   影响: {suggestion['impact']}")
        print(f"   建议: {suggestion['suggestion']}")
        print("")

    print("优化方法:")
    print("  - 优化提示词: 修改 src/incident_classifier_v1.py 中的提示词")
    print("  - 调整规则: 修改 src/policy.py 中的 Policy 规则")
    print("  - 换模型: 修改 .env 中的 OPENAI_MODEL")
    print("")
    print("优化后，重新运行评测并使用 A/B 对比验证效果。")


def run_optimized_evaluation():
    """运行优化后评测"""
    print("\n" + "=" * 60)
    print("步骤 4: 优化后评测")
    print("=" * 60)

    print("\n⚠️ 请先根据优化建议修改代码，然后继续。")
    input("按 Enter 继续运行优化后的评测...")

    # 初始化（重新加载，应用了修改）
    agent = IncidentClassifierV1()
    framework = EvaluationFramework(agent, agent_version="1.0.1")

    # 使用相同的测试集
    test_cases = (
        get_test_cases_by_priority("P0") +
        get_test_cases_by_priority("P1")
    )

    print(f"\n运行优化后评测 ({len(test_cases)} 个案例)...")

    # 运行评测
    report = framework.run_evaluation(test_cases, verbose=True)

    # 打印报告
    framework.print_report(report)

    # 保存报告
    output_dir = Path("outputs/evaluations")
    optimized_file = output_dir / "optimized.json"
    framework.save_report_json(report, str(optimized_file))
    framework.save_report_markdown(report, str(output_dir / "optimized.md"))

    return report, str(optimized_file)


def compare_results(baseline_file, optimized_file):
    """对比优化效果"""
    print("\n" + "=" * 60)
    print("步骤 5: A/B 对比")
    print("=" * 60)

    comparator = ABComparator()
    comparison = comparator.compare_reports(baseline_file, optimized_file)

    # 打印对比结果
    comparator.print_comparison(comparison)

    # 保存对比结果
    output_dir = Path("outputs/comparisons")
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_file = output_dir / "ab_comparison.json"
    comparator.save_comparison_json(comparison, str(comparison_file))

    return comparison


def main():
    """主流程"""
    print("\n" + "=" * 60)
    print("评测、分析与优化完整流程")
    print("=" * 60)

    print("\n本流程将执行:")
    print("  1. 基线评测")
    print("  2. 失败分析")
    print("  3. 优化指导")
    print("  4. 优化后评测")
    print("  5. A/B 对比")
    print("")

    mode = input("选择模式 (1=完整流程, 2=仅基线+分析, 3=仅对比, 默认1): ").strip() or "1"

    if mode == "1":
        # 完整流程
        # 步骤 1: 基线评测
        baseline_report, baseline_file = run_baseline_evaluation()

        # 步骤 2: 失败分析
        analysis = analyze_failures(baseline_report)

        # 步骤 3: 优化指导
        show_optimization_guide(analysis)

        # 步骤 4: 优化后评测
        optimized_report, optimized_file = run_optimized_evaluation()

        # 步骤 5: A/B 对比
        comparison = compare_results(baseline_file, optimized_file)

        # 总结
        print("\n" + "=" * 60)
        print("流程完成！")
        print("=" * 60)
        print(f"\n{comparison['recommendation']}")

    elif mode == "2":
        # 仅基线评测 + 失败分析
        baseline_report, baseline_file = run_baseline_evaluation()
        analysis = analyze_failures(baseline_report)
        show_optimization_guide(analysis)

        print("\n" + "=" * 60)
        print("分析完成！")
        print("=" * 60)
        print("\n根据优化建议修改代码后，可以运行:")
        print("  python scripts/run_evaluation.py")
        print("生成优化后的报告，然后使用本脚本的模式 3 进行对比。")

    elif mode == "3":
        # 仅 A/B 对比
        print("\n请提供两个评测报告文件:")
        baseline_file = input("  基线报告 (默认: outputs/evaluations/baseline.json): ").strip()
        baseline_file = baseline_file or "outputs/evaluations/baseline.json"

        optimized_file = input("  优化报告 (默认: outputs/evaluations/optimized.json): ").strip()
        optimized_file = optimized_file or "outputs/evaluations/optimized.json"

        if not Path(baseline_file).exists():
            print(f"\n❌ 基线报告不存在: {baseline_file}")
            return 1

        if not Path(optimized_file).exists():
            print(f"\n❌ 优化报告不存在: {optimized_file}")
            return 1

        comparison = compare_results(baseline_file, optimized_file)

        print("\n" + "=" * 60)
        print("对比完成！")
        print("=" * 60)
        print(f"\n{comparison['recommendation']}")

    else:
        print("\n❌ 无效的模式选择")
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 流程失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
