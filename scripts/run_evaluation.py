#!/usr/bin/env python3
"""
运行完整评测

使用结构化测试案例集评测故障分类器
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.incident_classifier_v1 import IncidentClassifierV1
from tests.test_cases import get_all_cases, get_test_cases_by_priority, print_statistics
from tests.evaluation_framework import EvaluationFramework


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("故障分类器评测系统")
    print("=" * 60)

    # 1. 显示测试案例统计
    print("\n步骤 1: 测试案例统计")
    print("-" * 60)
    print_statistics()

    # 2. 初始化 Agent
    print("\n步骤 2: 初始化 Agent")
    print("-" * 60)
    print("初始化 IncidentClassifierV1...")
    agent = IncidentClassifierV1()
    print("✅ 初始化完成")

    # 3. 创建评测框架
    print("\n步骤 3: 创建评测框架")
    print("-" * 60)
    framework = EvaluationFramework(agent, agent_version="1.0.0")
    print("✅ 评测框架就绪")

    # 4. 选择评测模式
    print("\n步骤 4: 选择评测模式")
    print("-" * 60)
    print("可选模式:")
    print("  1. 全量评测（所有 35 个案例）")
    print("  2. 快速评测（P0 + P1，15 个案例）")
    print("  3. 单一优先级（P0/P1/P2/P3）")
    print("")

    mode = input("请选择模式 (1/2/3，默认 2): ").strip() or "2"

    if mode == "1":
        # 全量评测
        test_cases = get_all_cases()
        print(f"\n✅ 已选择: 全量评测 ({len(test_cases)} 个案例)")
    elif mode == "2":
        # 快速评测（P0 + P1）
        test_cases = (
            get_test_cases_by_priority("P0") +
            get_test_cases_by_priority("P1")
        )
        print(f"\n✅ 已选择: 快速评测 ({len(test_cases)} 个案例)")
    elif mode == "3":
        # 单一优先级
        priority = input("请输入优先级 (P0/P1/P2/P3/EDGE): ").strip().upper()
        test_cases = get_test_cases_by_priority(priority)
        if test_cases:
            print(f"\n✅ 已选择: {priority} 评测 ({len(test_cases)} 个案例)")
        else:
            print(f"\n⚠️ 无效的优先级，使用快速评测")
            test_cases = (
                get_test_cases_by_priority("P0") +
                get_test_cases_by_priority("P1")
            )
    else:
        print("\n⚠️ 无效的模式，使用快速评测")
        test_cases = (
            get_test_cases_by_priority("P0") +
            get_test_cases_by_priority("P1")
        )

    # 5. 运行评测
    print("\n步骤 5: 运行评测")
    print("-" * 60)
    print(f"开始评测 {len(test_cases)} 个案例...")
    print("（这可能需要几分钟，取决于 API 速度）")
    print("")

    report = framework.run_evaluation(test_cases, verbose=True)

    # 6. 打印报告
    framework.print_report(report)

    # 7. 保存报告
    print("\n步骤 6: 保存报告")
    print("-" * 60)

    output_dir = Path("outputs/evaluations")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 JSON
    json_file = output_dir / f"evaluation_{report.report_id}.json"
    framework.save_report_json(report, str(json_file))

    # 保存 Markdown
    md_file = output_dir / f"evaluation_{report.report_id}.md"
    framework.save_report_markdown(report, str(md_file))

    # 8. 总结
    print("\n" + "=" * 60)
    print("评测完成！")
    print("=" * 60)

    print(f"\n核心指标:")
    print(f"  准确率: {report.accuracy:.1%}")
    print(f"  可接受率: {report.acceptable_rate:.1%}")
    if report.p0_total > 0:
        print(f"  P0 准确率: {report.p0_accuracy:.1%}")
    if report.p1_total > 0:
        print(f"  P1 准确率: {report.p1_accuracy:.1%}")

    print(f"\n报告位置:")
    print(f"  JSON: {json_file}")
    print(f"  Markdown: {md_file}")

    # 9. 返回退出码（用于 CI）
    if report.failed > 0:
        print(f"\n⚠️ 有 {report.failed} 个案例失败")
        return 1
    else:
        print(f"\n✅ 所有案例通过！")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断评测")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 评测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
