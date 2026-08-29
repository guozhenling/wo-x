"""
统一评测框架

提供标准化的评测流程和报告生成
"""
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from tests.test_cases import TestCase, get_all_cases


@dataclass
class TestResult:
    """单个测试结果"""
    test_id: str
    description: str
    expected_severity: str
    actual_severity: str
    expected_category: str
    actual_category: str
    is_correct: bool          # 完全正确（严重程度和类别都对）
    is_acceptable: bool       # 可接受（严重程度在允许范围内）
    duration: float
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EvaluationReport:
    """评测报告"""
    # 基本信息
    report_id: str
    agent_version: str
    total_cases: int
    start_time: str
    end_time: str
    total_duration: float

    # 准确率统计
    passed: int = 0           # 完全正确
    acceptable: int = 0       # 可接受
    failed: int = 0           # 失败

    accuracy: float = 0.0            # 完全正确率
    acceptable_rate: float = 0.0     # 可接受率

    # 维度准确率
    severity_correct: int = 0
    category_correct: int = 0
    severity_accuracy: float = 0.0
    category_accuracy: float = 0.0

    # 关键指标（P0/P1）
    p0_total: int = 0
    p0_correct: int = 0
    p0_accuracy: float = 0.0

    p1_total: int = 0
    p1_correct: int = 0
    p1_accuracy: float = 0.0

    # 性能指标
    avg_duration: float = 0.0
    p95_duration: float = 0.0

    # 详细结果
    results: List[TestResult] = field(default_factory=list)

    # 失败案例
    failures: List[Dict[str, Any]] = field(default_factory=list)


class EvaluationFramework:
    """
    统一评测框架

    提供标准化的评测流程、结果统计和报告生成
    """

    def __init__(self, agent, agent_version: str = "1.0.0"):
        """
        初始化评测框架

        Args:
            agent: 要评测的 Agent 实例
            agent_version: Agent 版本号
        """
        self.agent = agent
        self.agent_version = agent_version

    def run_single_test(self, test_case: TestCase) -> TestResult:
        """
        运行单个测试案例

        Args:
            test_case: 测试案例

        Returns:
            测试结果
        """
        start = time.time()

        try:
            # 调用 Agent
            result = self.agent.classify(test_case.description)
            duration = time.time() - start

            # 检查是否成功
            if not result.get('success'):
                return TestResult(
                    test_id=test_case.id,
                    description=test_case.description,
                    expected_severity=test_case.expected_severity,
                    actual_severity="ERROR",
                    expected_category=test_case.expected_category,
                    actual_category="ERROR",
                    is_correct=False,
                    is_acceptable=False,
                    duration=duration,
                    error=str(result.get('error', 'Unknown error'))
                )

            # 提取分类结果
            classification = result['classification']
            actual_severity = classification['severity']
            actual_category = classification['category']

            # 判断是否正确
            is_correct = (
                actual_severity == test_case.expected_severity and
                actual_category == test_case.expected_category
            )

            # 判断是否可接受（严重程度在允许范围内）
            is_acceptable = (
                actual_severity in test_case.acceptable_severities
            )

            return TestResult(
                test_id=test_case.id,
                description=test_case.description,
                expected_severity=test_case.expected_severity,
                actual_severity=actual_severity,
                expected_category=test_case.expected_category,
                actual_category=actual_category,
                is_correct=is_correct,
                is_acceptable=is_acceptable,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start
            return TestResult(
                test_id=test_case.id,
                description=test_case.description,
                expected_severity=test_case.expected_severity,
                actual_severity="ERROR",
                expected_category=test_case.expected_category,
                actual_category="ERROR",
                is_correct=False,
                is_acceptable=False,
                duration=duration,
                error=str(e)
            )

    def run_evaluation(
        self,
        test_cases: Optional[List[TestCase]] = None,
        verbose: bool = True
    ) -> EvaluationReport:
        """
        运行完整评测

        Args:
            test_cases: 测试案例列表（None 则使用所有案例）
            verbose: 是否打印详细进度

        Returns:
            评测报告
        """
        # 使用所有案例（如果未指定）
        if test_cases is None:
            test_cases = get_all_cases()

        # 初始化报告
        report = EvaluationReport(
            report_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            agent_version=self.agent_version,
            total_cases=len(test_cases),
            start_time=datetime.now().isoformat(),
            end_time="",
            total_duration=0.0
        )

        if verbose:
            print(f"\n开始评测 {len(test_cases)} 个案例...")
            print("=" * 60)

        # 运行所有测试
        for i, test_case in enumerate(test_cases, 1):
            if verbose:
                print(f"\n[{i}/{len(test_cases)}] {test_case.id}: {test_case.description[:50]}...")

            result = self.run_single_test(test_case)
            report.results.append(result)

            # 统计结果
            if result.is_correct:
                report.passed += 1
                if verbose:
                    print(f"  ✅ 正确: {result.actual_severity} / {result.actual_category}")
            elif result.is_acceptable:
                report.acceptable += 1
                if verbose:
                    print(f"  ⚠️  可接受: {result.actual_severity} (期望 {result.expected_severity})")
            else:
                report.failed += 1
                if verbose:
                    if result.error:
                        print(f"  ❌ 失败: {result.error}")
                    else:
                        print(f"  ❌ 错误: {result.actual_severity} (期望 {result.expected_severity})")

                # 记录失败案例
                report.failures.append({
                    "test_id": result.test_id,
                    "description": result.description,
                    "expected": {
                        "severity": result.expected_severity,
                        "category": result.expected_category
                    },
                    "actual": {
                        "severity": result.actual_severity,
                        "category": result.actual_category
                    },
                    "error": result.error
                })

            # 统计维度准确率
            if result.actual_severity == test_case.expected_severity:
                report.severity_correct += 1
            if result.actual_category == test_case.expected_category:
                report.category_correct += 1

            # 统计 P0/P1 准确率
            if test_case.expected_severity == "P0":
                report.p0_total += 1
                if result.actual_severity == "P0":
                    report.p0_correct += 1
            elif test_case.expected_severity == "P1":
                report.p1_total += 1
                if result.actual_severity == "P1":
                    report.p1_correct += 1

        # 计算最终统计
        report.end_time = datetime.now().isoformat()
        report.total_duration = sum(r.duration for r in report.results)

        report.accuracy = report.passed / report.total_cases
        report.acceptable_rate = (report.passed + report.acceptable) / report.total_cases
        report.severity_accuracy = report.severity_correct / report.total_cases
        report.category_accuracy = report.category_correct / report.total_cases

        if report.p0_total > 0:
            report.p0_accuracy = report.p0_correct / report.p0_total
        if report.p1_total > 0:
            report.p1_accuracy = report.p1_correct / report.p1_total

        # 性能统计
        durations = [r.duration for r in report.results]
        report.avg_duration = sum(durations) / len(durations)
        sorted_durations = sorted(durations)
        report.p95_duration = sorted_durations[int(len(durations) * 0.95)]

        return report

    def print_report(self, report: EvaluationReport):
        """
        打印评测报告（控制台格式）

        Args:
            report: 评测报告
        """
        print("\n" + "=" * 60)
        print("评测报告")
        print("=" * 60)

        # 基本信息
        print(f"\nAgent 版本: {report.agent_version}")
        print(f"报告 ID: {report.report_id}")
        print(f"开始时间: {report.start_time}")
        print(f"结束时间: {report.end_time}")

        # 总体统计
        print(f"\n总体统计:")
        print(f"  总案例数: {report.total_cases}")
        print(f"  完全正确: {report.passed} ({report.accuracy:.1%})")
        print(f"  可接受: {report.acceptable} ({report.acceptable_rate:.1%})")
        print(f"  失败: {report.failed}")

        # 维度准确率
        print(f"\n维度准确率:")
        print(f"  严重程度: {report.severity_correct}/{report.total_cases} ({report.severity_accuracy:.1%})")
        print(f"  故障类别: {report.category_correct}/{report.total_cases} ({report.category_accuracy:.1%})")

        # 关键指标（P0/P1）
        print(f"\n关键指标:")
        if report.p0_total > 0:
            print(f"  P0 准确率: {report.p0_correct}/{report.p0_total} ({report.p0_accuracy:.1%})")
        if report.p1_total > 0:
            print(f"  P1 准确率: {report.p1_correct}/{report.p1_total} ({report.p1_accuracy:.1%})")

        # 性能指标
        print(f"\n性能指标:")
        print(f"  总耗时: {report.total_duration:.1f}s")
        print(f"  平均耗时: {report.avg_duration:.2f}s/案例")
        print(f"  P95 延迟: {report.p95_duration:.2f}s")

        # 失败案例
        if report.failures:
            print(f"\n失败案例 ({len(report.failures)} 个):")
            for failure in report.failures[:10]:  # 最多显示 10 个
                print(f"\n  [{failure['test_id']}] {failure['description'][:50]}...")
                print(f"    期望: {failure['expected']['severity']} / {failure['expected']['category']}")
                print(f"    实际: {failure['actual']['severity']} / {failure['actual']['category']}")
                if failure.get('error'):
                    print(f"    错误: {failure['error']}")

            if len(report.failures) > 10:
                print(f"\n  ... 还有 {len(report.failures) - 10} 个失败案例")

        print("\n" + "=" * 60)

    def save_report_json(self, report: EvaluationReport, filepath: str):
        """
        保存评测报告为 JSON 格式

        Args:
            report: 评测报告
            filepath: 保存路径
        """
        # 转换为字典
        report_dict = {
            "metadata": {
                "report_id": report.report_id,
                "agent_version": report.agent_version,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "total_duration": report.total_duration,
            },
            "summary": {
                "total_cases": report.total_cases,
                "passed": report.passed,
                "acceptable": report.acceptable,
                "failed": report.failed,
                "accuracy": report.accuracy,
                "acceptable_rate": report.acceptable_rate,
                "severity_accuracy": report.severity_accuracy,
                "category_accuracy": report.category_accuracy,
            },
            "key_metrics": {
                "p0_total": report.p0_total,
                "p0_correct": report.p0_correct,
                "p0_accuracy": report.p0_accuracy,
                "p1_total": report.p1_total,
                "p1_correct": report.p1_correct,
                "p1_accuracy": report.p1_accuracy,
            },
            "performance": {
                "avg_duration": report.avg_duration,
                "p95_duration": report.p95_duration,
            },
            "failures": report.failures,
            "results": [
                {
                    "test_id": r.test_id,
                    "description": r.description,
                    "expected": {
                        "severity": r.expected_severity,
                        "category": r.expected_category
                    },
                    "actual": {
                        "severity": r.actual_severity,
                        "category": r.actual_category
                    },
                    "is_correct": r.is_correct,
                    "is_acceptable": r.is_acceptable,
                    "duration": r.duration,
                    "error": r.error,
                    "timestamp": r.timestamp
                }
                for r in report.results
            ]
        }

        # 保存到文件
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"\n报告已保存到: {filepath}")

    def save_report_markdown(self, report: EvaluationReport, filepath: str):
        """
        保存评测报告为 Markdown 格式

        Args:
            report: 评测报告
            filepath: 保存路径
        """
        lines = []

        # 标题
        lines.append(f"# 评测报告")
        lines.append("")
        lines.append(f"**报告 ID**: {report.report_id}")
        lines.append(f"**Agent 版本**: {report.agent_version}")
        lines.append(f"**生成时间**: {report.end_time}")
        lines.append("")

        # 总体统计
        lines.append("## 总体统计")
        lines.append("")
        lines.append(f"- 总案例数: {report.total_cases}")
        lines.append(f"- 完全正确: {report.passed} ({report.accuracy:.1%})")
        lines.append(f"- 可接受: {report.acceptable} ({report.acceptable_rate:.1%})")
        lines.append(f"- 失败: {report.failed}")
        lines.append("")

        # 维度准确率
        lines.append("## 维度准确率")
        lines.append("")
        lines.append(f"- 严重程度: {report.severity_correct}/{report.total_cases} ({report.severity_accuracy:.1%})")
        lines.append(f"- 故障类别: {report.category_correct}/{report.total_cases} ({report.category_accuracy:.1%})")
        lines.append("")

        # 关键指标
        lines.append("## 关键指标")
        lines.append("")
        if report.p0_total > 0:
            lines.append(f"- P0 准确率: {report.p0_correct}/{report.p0_total} ({report.p0_accuracy:.1%})")
        if report.p1_total > 0:
            lines.append(f"- P1 准确率: {report.p1_correct}/{report.p1_total} ({report.p1_accuracy:.1%})")
        lines.append("")

        # 性能指标
        lines.append("## 性能指标")
        lines.append("")
        lines.append(f"- 总耗时: {report.total_duration:.1f}s")
        lines.append(f"- 平均耗时: {report.avg_duration:.2f}s/案例")
        lines.append(f"- P95 延迟: {report.p95_duration:.2f}s")
        lines.append("")

        # 失败案例
        if report.failures:
            lines.append("## 失败案例")
            lines.append("")
            for failure in report.failures:
                lines.append(f"### {failure['test_id']}")
                lines.append("")
                lines.append(f"**描述**: {failure['description']}")
                lines.append("")
                lines.append(f"**期望**: {failure['expected']['severity']} / {failure['expected']['category']}")
                lines.append(f"**实际**: {failure['actual']['severity']} / {failure['actual']['category']}")
                if failure.get('error'):
                    lines.append(f"**错误**: {failure['error']}")
                lines.append("")

        # 保存到文件
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"\nMarkdown 报告已保存到: {filepath}")


if __name__ == "__main__":
    """
    使用示例
    """
    print("评测框架使用示例:")
    print("\nfrom tests.evaluation_framework import EvaluationFramework")
    print("from src.incident_classifier_v1 import IncidentClassifierV1")
    print("")
    print("# 1. 初始化")
    print("agent = IncidentClassifierV1()")
    print("framework = EvaluationFramework(agent, agent_version='1.0.0')")
    print("")
    print("# 2. 运行评测")
    print("report = framework.run_evaluation()")
    print("")
    print("# 3. 打印报告")
    print("framework.print_report(report)")
    print("")
    print("# 4. 保存报告")
    print("framework.save_report_json(report, 'outputs/evaluations/report.json')")
    print("framework.save_report_markdown(report, 'outputs/evaluations/report.md')")
