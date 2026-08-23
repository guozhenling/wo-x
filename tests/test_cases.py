#!/usr/bin/env python3
"""
故障分类器测试运行器（增强版）
支持多维度评分、失败案例分析、标签筛选
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import json
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from client import LLMClient
from incident_triage import IncidentClassifier
from test_data import TestCase, get_test_cases, get_cases_by_tag, get_cases_by_severity


@dataclass
class TestResult:
    """测试结果数据结构"""
    case_id: int
    description: str

    # 期望值
    expected_severity: str
    expected_category: str
    expected_human_review: bool
    requires_tool_evidence: bool

    # 实际值
    actual_severity: str
    actual_category: str
    actual_human_review: bool
    actual_rationale: str
    has_tool_calls: bool

    # 评分维度
    format_valid: bool  # 格式有效（JSON 解析成功）
    severity_correct: bool  # 严重度正确
    risk_control_correct: bool  # 风险控制正确（needs_human_review）
    evidence_exists: bool  # 证据存在（rationale 非空且有意义）

    # 综合判断
    passed: bool  # 所有关键维度都通过

    # 额外信息
    tags: List[str]
    error: str = None


class TestRunner:
    """测试运行器"""

    def __init__(self, classifier: IncidentClassifier):
        self.classifier = classifier
        self.results: List[TestResult] = []

    def run_single_case(self, case: TestCase) -> TestResult:
        """运行单个测试案例"""
        try:
            # 执行分类
            result = self.classifier.classify(case.description)

            # 评估各个维度
            format_valid = True  # 能返回结果说明格式有效
            severity_correct = result.severity == case.expected_severity
            risk_control_correct = result.needs_human_review == case.expected_human_review
            evidence_exists = bool(result.rationale and len(result.rationale.strip()) > 10)

            # 检查工具调用（如果需要证据）
            has_tool_calls = False  # TODO: 从 trace_manager 获取
            if case.requires_tool_evidence:
                # 对于需要工具证据的案例，应该有工具调用或明确说明证据不足
                evidence_exists = has_tool_calls or "证据不足" in result.rationale or "insufficient" in result.rationale.lower()

            # 综合判断：关键维度都通过
            passed = format_valid and severity_correct and risk_control_correct and evidence_exists

            return TestResult(
                case_id=case.id,
                description=case.description,
                expected_severity=case.expected_severity,
                expected_category=case.expected_category,
                expected_human_review=case.expected_human_review,
                requires_tool_evidence=case.requires_tool_evidence,
                actual_severity=result.severity,
                actual_category=result.category,
                actual_human_review=result.needs_human_review,
                actual_rationale=result.rationale,
                has_tool_calls=has_tool_calls,
                format_valid=format_valid,
                severity_correct=severity_correct,
                risk_control_correct=risk_control_correct,
                evidence_exists=evidence_exists,
                passed=passed,
                tags=case.tags
            )

        except Exception as e:
            # 格式错误或其他异常
            return TestResult(
                case_id=case.id,
                description=case.description,
                expected_severity=case.expected_severity,
                expected_category=case.expected_category,
                expected_human_review=case.expected_human_review,
                requires_tool_evidence=case.requires_tool_evidence,
                actual_severity="",
                actual_category="",
                actual_human_review=False,
                actual_rationale="",
                has_tool_calls=False,
                format_valid=False,
                severity_correct=False,
                risk_control_correct=False,
                evidence_exists=False,
                passed=False,
                tags=case.tags,
                error=str(e)
            )

    def run_all(self, cases: List[TestCase], verbose: bool = True) -> Dict[str, Any]:
        """运行所有测试案例"""
        total = len(cases)
        self.results = []

        if verbose:
            print("=" * 80)
            print(f"开始测试 {total} 个案例")
            print("=" * 80)
            print()

        # 逐个执行
        for i, case in enumerate(cases, 1):
            if verbose:
                print(f"[{i}/{total}] Case #{case.id}: {case.description[:60]}...")

            result = self.run_single_case(case)
            self.results.append(result)

            if verbose:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                print(f"  {status} | 严重度: {result.actual_severity} | 审核: {result.actual_human_review}")
                if not result.passed:
                    if not result.severity_correct:
                        print(f"    - 严重度错误: 期望 {result.expected_severity}, 实际 {result.actual_severity}")
                    if not result.risk_control_correct:
                        print(f"    - 风险控制错误: 期望 {result.expected_human_review}, 实际 {result.actual_human_review}")
                    if not result.evidence_exists:
                        print(f"    - 证据不足: rationale 为空或过短")
                    if result.error:
                        print(f"    - 错误: {result.error}")
                print()

        # 生成统计报告
        return self.generate_report(verbose)

    def generate_report(self, verbose: bool = True) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.results)

        # 计算各维度通过率
        format_valid_count = sum(1 for r in self.results if r.format_valid)
        severity_correct_count = sum(1 for r in self.results if r.severity_correct)
        risk_control_correct_count = sum(1 for r in self.results if r.risk_control_correct)
        evidence_exists_count = sum(1 for r in self.results if r.evidence_exists)
        passed_count = sum(1 for r in self.results if r.passed)

        # 失败案例
        failed_cases = [r for r in self.results if not r.passed]

        # 按严重程度分组
        severity_stats = {}
        for severity in ["P0", "P1", "P2", "P3"]:
            severity_results = [r for r in self.results if r.expected_severity == severity]
            if severity_results:
                severity_passed = sum(1 for r in severity_results if r.passed)
                severity_stats[severity] = {
                    "total": len(severity_results),
                    "passed": severity_passed,
                    "rate": severity_passed / len(severity_results) * 100
                }

        # 按标签分组
        tag_stats = {}
        all_tags = set()
        for r in self.results:
            all_tags.update(r.tags)
        for tag in all_tags:
            tag_results = [r for r in self.results if tag in r.tags]
            tag_passed = sum(1 for r in tag_results if r.passed)
            tag_stats[tag] = {
                "total": len(tag_results),
                "passed": tag_passed,
                "rate": tag_passed / len(tag_results) * 100
            }

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_cases": total,
            "metrics": {
                "format_valid": {
                    "count": format_valid_count,
                    "rate": format_valid_count / total * 100
                },
                "severity_correct": {
                    "count": severity_correct_count,
                    "rate": severity_correct_count / total * 100
                },
                "risk_control_correct": {
                    "count": risk_control_correct_count,
                    "rate": risk_control_correct_count / total * 100
                },
                "evidence_exists": {
                    "count": evidence_exists_count,
                    "rate": evidence_exists_count / total * 100
                },
                "overall_passed": {
                    "count": passed_count,
                    "rate": passed_count / total * 100
                }
            },
            "severity_breakdown": severity_stats,
            "tag_breakdown": tag_stats,
            "failed_cases": [
                {
                    "case_id": r.case_id,
                    "description": r.description,
                    "expected_severity": r.expected_severity,
                    "actual_severity": r.actual_severity,
                    "expected_human_review": r.expected_human_review,
                    "actual_human_review": r.actual_human_review,
                    "tags": r.tags,
                    "error": r.error
                }
                for r in failed_cases
            ]
        }

        if verbose:
            self.print_report(report)

        return report

    def print_report(self, report: Dict[str, Any]):
        """打印测试报告"""
        print("=" * 80)
        print("测试报告")
        print("=" * 80)
        print()

        # 总览
        total = report["total_cases"]
        passed = report["metrics"]["overall_passed"]["count"]
        pass_rate = report["metrics"]["overall_passed"]["rate"]

        print(f"总案例数: {total}")
        print(f"通过案例: {passed}")
        print(f"失败案例: {total - passed}")
        print(f"总通过率: {pass_rate:.1f}%")
        print()

        # 各维度评分
        print("=" * 80)
        print("各维度评分")
        print("=" * 80)
        metrics = report["metrics"]
        print(f"1. 格式有效:     {metrics['format_valid']['count']}/{total} ({metrics['format_valid']['rate']:.1f}%)")
        print(f"2. 严重度正确:   {metrics['severity_correct']['count']}/{total} ({metrics['severity_correct']['rate']:.1f}%)")
        print(f"3. 风险控制正确: {metrics['risk_control_correct']['count']}/{total} ({metrics['risk_control_correct']['rate']:.1f}%)")
        print(f"4. 证据存在:     {metrics['evidence_exists']['count']}/{total} ({metrics['evidence_exists']['rate']:.1f}%)")
        print()

        # 按严重程度分组
        print("=" * 80)
        print("按严重程度分组")
        print("=" * 80)
        for severity in ["P0", "P1", "P2", "P3"]:
            if severity in report["severity_breakdown"]:
                stats = report["severity_breakdown"][severity]
                print(f"{severity}: {stats['passed']}/{stats['total']} ({stats['rate']:.1f}%)")
        print()

        # 按标签分组
        print("=" * 80)
        print("按标签分组")
        print("=" * 80)
        for tag, stats in sorted(report["tag_breakdown"].items()):
            print(f"{tag}: {stats['passed']}/{stats['total']} ({stats['rate']:.1f}%)")
        print()

        # 失败案例列表
        failed_cases = report["failed_cases"]
        if failed_cases:
            print("=" * 80)
            print(f"失败案例列表 ({len(failed_cases)} 个)")
            print("=" * 80)
            for i, case in enumerate(failed_cases, 1):
                print(f"\n{i}. Case #{case['case_id']}")
                print(f"   描述: {case['description'][:70]}...")
                print(f"   标签: {', '.join(case['tags'])}")
                print(f"   期望: {case['expected_severity']} | 审核={case['expected_human_review']}")
                print(f"   实际: {case['actual_severity']} | 审核={case['actual_human_review']}")
                if case['error']:
                    print(f"   错误: {case['error']}")
        else:
            print("🎉 所有测试案例通过!")

        print("\n" + "=" * 80)


def run_tests(tag_filter: str = None, verbose: bool = True, save_results: bool = True):
    """
    运行测试

    Args:
        tag_filter: 标签过滤器（可选），如 "payment_5xx", "malicious"
        verbose: 是否打印详细信息
        save_results: 是否保存结果到文件
    """
    # 初始化
    if verbose:
        print("正在初始化分类器...")

    try:
        llm_client = LLMClient()
        classifier = IncidentClassifier(llm_client)
        if verbose:
            print("✓ 初始化成功\n")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return

    # 获取测试案例
    if tag_filter:
        cases = get_cases_by_tag(tag_filter)
        if verbose:
            print(f"筛选标签: {tag_filter}")
            print(f"匹配案例: {len(cases)} 个\n")
    else:
        cases = get_test_cases()

    if not cases:
        print("没有匹配的测试案例")
        return

    # 运行测试
    runner = TestRunner(classifier)
    report = runner.run_all(cases, verbose=verbose)

    # 保存结果
    if save_results:
        output_file = "test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            # 保存完整结果（包括每个案例的详细信息）
            full_report = {
                **report,
                "detailed_results": [asdict(r) for r in runner.results]
            }
            json.dump(full_report, f, ensure_ascii=False, indent=2)

        if verbose:
            print(f"\n详细结果已保存到: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="故障分类器测试运行器")
    parser.add_argument("--tag", type=str, help="按标签筛选测试案例")
    parser.add_argument("--quiet", action="store_true", help="静默模式，只输出摘要")
    parser.add_argument("--no-save", action="store_true", help="不保存结果到文件")

    args = parser.parse_args()

    run_tests(
        tag_filter=args.tag,
        verbose=not args.quiet,
        save_results=not args.no_save
    )
