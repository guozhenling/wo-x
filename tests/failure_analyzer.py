"""
失败分析工具

分析评测失败的案例，识别失败模式，生成优化建议
"""
from typing import List, Dict, Any
from collections import defaultdict
from dataclasses import dataclass

from tests.evaluation_framework import TestResult, EvaluationReport


@dataclass
class FailurePattern:
    """失败模式"""
    pattern_type: str        # 失败类型
    count: int              # 出现次数
    cases: List[str]        # 案例 ID 列表
    description: str        # 模式描述
    suggested_fix: str      # 建议修复
    severity: str = "中"    # 严重程度（高/中/低）


class FailureAnalyzer:
    """
    失败案例分析器

    分析评测失败的案例，识别失败模式，生成优化建议
    """

    def __init__(self):
        self.failure_types = {
            "severity_overestimate": "严重程度高估",
            "severity_underestimate": "严重程度低估",
            "category_wrong": "类别判断错误",
            "edge_case_failure": "边界案例失败",
            "system_error": "系统错误"
        }

    def analyze_failures(
        self,
        report: EvaluationReport
    ) -> Dict[str, Any]:
        """
        分析失败案例

        Args:
            report: 评测报告

        Returns:
            分析结果
        """
        # 1. 提取失败案例
        failures = [r for r in report.results if not r.is_acceptable]

        if not failures:
            return {
                "total_failures": 0,
                "patterns": [],
                "suggestions": [],
                "summary": "没有失败案例，表现优秀！"
            }

        # 2. 分类失败类型
        type_groups = defaultdict(list)

        for f in failures:
            failure_type = self._classify_failure(f)
            type_groups[failure_type].append(f)

        # 3. 识别模式
        patterns = []

        for ftype, cases in type_groups.items():
            pattern = self._identify_pattern(ftype, cases)
            patterns.append(pattern)

        # 4. 生成建议（按影响大小排序）
        suggestions = self._generate_suggestions(patterns)

        # 5. 生成摘要
        summary = self._generate_summary(failures, patterns)

        return {
            "total_failures": len(failures),
            "failure_types": {
                ftype: len(cases)
                for ftype, cases in type_groups.items()
            },
            "patterns": patterns,
            "suggestions": suggestions,
            "summary": summary,
            "details": [
                {
                    "test_id": f.test_id,
                    "description": f.description,
                    "expected": {
                        "severity": f.expected_severity,
                        "category": f.expected_category
                    },
                    "actual": {
                        "severity": f.actual_severity,
                        "category": f.actual_category
                    },
                    "failure_type": self._classify_failure(f),
                    "error": f.error
                }
                for f in failures
            ]
        }

    def _classify_failure(self, result: TestResult) -> str:
        """
        分类单个失败案例

        Args:
            result: 测试结果

        Returns:
            失败类型
        """
        if result.error:
            return "system_error"

        # 严重程度映射
        severity_map = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        expected_level = severity_map.get(result.expected_severity, 3)
        actual_level = severity_map.get(result.actual_severity, 3)

        # 判断失败类型
        if actual_level < expected_level:
            return "severity_overestimate"  # 高估（实际给的更严重）
        elif actual_level > expected_level:
            return "severity_underestimate"  # 低估
        elif result.actual_category != result.expected_category:
            return "category_wrong"
        else:
            return "edge_case_failure"

    def _identify_pattern(
        self,
        failure_type: str,
        cases: List[TestResult]
    ) -> FailurePattern:
        """
        识别失败模式

        Args:
            failure_type: 失败类型
            cases: 案例列表

        Returns:
            失败模式
        """
        case_ids = [c.test_id for c in cases]

        # 生成模式描述和修复建议
        pattern_desc, fix_suggestion, severity = self._analyze_pattern(
            failure_type,
            cases
        )

        return FailurePattern(
            pattern_type=failure_type,
            count=len(cases),
            cases=case_ids,
            description=pattern_desc,
            suggested_fix=fix_suggestion,
            severity=severity
        )

    def _analyze_pattern(
        self,
        failure_type: str,
        cases: List[TestResult]
    ) -> tuple:
        """
        分析模式细节

        Args:
            failure_type: 失败类型
            cases: 案例列表

        Returns:
            (模式描述, 修复建议, 严重程度)
        """
        if failure_type == "severity_overestimate":
            # 分析是否都高估到某个特定级别
            actual_levels = [c.actual_severity for c in cases]
            expected_levels = [c.expected_severity for c in cases]

            # 检查是否有系统性问题
            p0_overestimate = sum(1 for a in actual_levels if a == "P0")

            if p0_overestimate > len(cases) / 2:
                desc = f"{len(cases)} 个案例被高估为 P0（最严重）"
                fix = "检查 Policy 规则是否过于严格，或提示词中的 P0 定义是否过宽"
                severity = "高"
            else:
                desc = f"{len(cases)} 个案例严重程度判断偏高"
                fix = "在提示词中强调优先级判断标准，增加降级示例"
                severity = "中"

            return (desc, fix, severity)

        elif failure_type == "severity_underestimate":
            # 检查是否低估了关键案例（P0/P1）
            critical_underestimate = sum(
                1 for c in cases
                if c.expected_severity in ["P0", "P1"]
            )

            if critical_underestimate > 0:
                desc = f"{len(cases)} 个案例被低估（包含 {critical_underestimate} 个关键案例）"
                fix = "检查是否缺少关键信息判断（如影响范围、错误率阈值），增强提示词对严重性的描述"
                severity = "高"
            else:
                desc = f"{len(cases)} 个案例被低估"
                fix = "优化提示词，明确严重程度的判断标准"
                severity = "中"

            return (desc, fix, severity)

        elif failure_type == "category_wrong":
            # 分析类别混淆
            actual_cats = [c.actual_category for c in cases]
            expected_cats = [c.expected_category for c in cases]

            confusion = defaultdict(int)
            for exp, act in zip(expected_cats, actual_cats):
                confusion[f"{exp}→{act}"] += 1

            most_common = max(confusion.items(), key=lambda x: x[1])

            desc = f"{len(cases)} 个类别判断错误，最常见混淆: {most_common[0]} ({most_common[1]} 次)"
            fix = f"在提示词中明确区分 {most_common[0].split('→')[0]} 和 {most_common[0].split('→')[1]}，增加示例"
            severity = "中"

            return (desc, fix, severity)

        elif failure_type == "system_error":
            desc = f"{len(cases)} 个系统错误（超时、API 失败等）"
            fix = "检查代码逻辑、API 调用、异常处理、网络连接"
            severity = "高"

            return (desc, fix, severity)

        else:  # edge_case_failure
            # 分析边界案例特征
            edge_descriptions = [c.description for c in cases]

            # 检查是否有空描述
            empty_desc = sum(1 for d in edge_descriptions if not d.strip())
            # 检查是否有模糊描述
            vague_desc = sum(1 for d in edge_descriptions if len(d.strip()) < 10)

            if empty_desc > 0:
                desc = f"{len(cases)} 个边界案例失败（包含 {empty_desc} 个空输入）"
                fix = "增加空输入处理逻辑，返回默认的 P3/unknown"
            elif vague_desc > 0:
                desc = f"{len(cases)} 个边界案例失败（包含 {vague_desc} 个模糊描述）"
                fix = "增加模糊输入的处理逻辑和示例"
            else:
                desc = f"{len(cases)} 个边界案例失败"
                fix = "分析具体案例，针对性增加处理逻辑"

            severity = "低"

            return (desc, fix, severity)

    def _generate_suggestions(
        self,
        patterns: List[FailurePattern]
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议

        Args:
            patterns: 失败模式列表

        Returns:
            建议列表（按优先级排序）
        """
        suggestions = []

        # 按严重程度和影响大小排序
        severity_order = {"高": 0, "中": 1, "低": 2}
        sorted_patterns = sorted(
            patterns,
            key=lambda p: (severity_order.get(p.severity, 3), -p.count)
        )

        for i, pattern in enumerate(sorted_patterns, 1):
            suggestions.append({
                "priority": i,
                "severity": pattern.severity,
                "pattern": self.failure_types.get(
                    pattern.pattern_type,
                    pattern.pattern_type
                ),
                "impact": f"影响 {pattern.count} 个案例",
                "suggestion": pattern.suggested_fix,
                "affected_cases": pattern.cases
            })

        return suggestions

    def _generate_summary(
        self,
        failures: List[TestResult],
        patterns: List[FailurePattern]
    ) -> str:
        """
        生成分析摘要

        Args:
            failures: 失败案例列表
            patterns: 失败模式列表

        Returns:
            摘要文本
        """
        lines = []

        lines.append(f"发现 {len(failures)} 个失败案例，识别出 {len(patterns)} 种失败模式。")

        # 高优先级问题
        high_priority = [p for p in patterns if p.severity == "高"]
        if high_priority:
            lines.append(f"\n⚠️ 高优先级问题 {len(high_priority)} 个：")
            for p in high_priority:
                lines.append(f"  - {p.description}")

        # 建议优先优化方向
        if patterns:
            top_pattern = max(patterns, key=lambda p: p.count)
            lines.append(f"\n💡 建议优先优化: {self.failure_types.get(top_pattern.pattern_type)}（影响 {top_pattern.count} 个案例）")

        return "\n".join(lines)

    def print_analysis(self, analysis: Dict[str, Any]):
        """
        打印分析报告

        Args:
            analysis: 分析结果
        """
        print("\n" + "=" * 60)
        print("失败案例分析报告")
        print("=" * 60)

        if analysis["total_failures"] == 0:
            print("\n✅ 没有失败案例！")
            return

        print(f"\n{analysis['summary']}")

        print(f"\n失败类型分布:")
        for ftype, count in analysis["failure_types"].items():
            type_name = self.failure_types.get(ftype, ftype)
            print(f"  {type_name}: {count} 个")

        print(f"\n识别到的失败模式:")
        for pattern in analysis["patterns"]:
            type_name = self.failure_types.get(pattern.pattern_type)
            print(f"\n  [{pattern.severity}] {type_name}:")
            print(f"    影响: {pattern.count} 个案例")
            print(f"    描述: {pattern.description}")
            print(f"    建议: {pattern.suggested_fix}")
            print(f"    案例: {', '.join(pattern.cases[:5])}")
            if len(pattern.cases) > 5:
                print(f"          ... 还有 {len(pattern.cases) - 5} 个")

        print(f"\n优化建议（按优先级）:")
        for suggestion in analysis["suggestions"]:
            print(f"\n  {suggestion['priority']}. [{suggestion['severity']}] {suggestion['pattern']}")
            print(f"     {suggestion['impact']}")
            print(f"     💡 {suggestion['suggestion']}")

        print("\n" + "=" * 60)

    def save_analysis_json(self, analysis: Dict[str, Any], filepath: str):
        """
        保存分析结果为 JSON

        Args:
            analysis: 分析结果
            filepath: 保存路径
        """
        import json
        from pathlib import Path

        # 转换 FailurePattern 对象为字典
        analysis_dict = analysis.copy()
        analysis_dict["patterns"] = [
            {
                "pattern_type": p.pattern_type,
                "count": p.count,
                "cases": p.cases,
                "description": p.description,
                "suggested_fix": p.suggested_fix,
                "severity": p.severity
            }
            for p in analysis["patterns"]
        ]

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_dict, f, indent=2, ensure_ascii=False)

        print(f"\n分析结果已保存到: {filepath}")


if __name__ == "__main__":
    """
    使用示例
    """
    print("失败分析器使用示例:")
    print("\nfrom tests.failure_analyzer import FailureAnalyzer")
    print("from tests.evaluation_framework import EvaluationFramework")
    print("")
    print("# 1. 运行评测")
    print("framework = EvaluationFramework(agent)")
    print("report = framework.run_evaluation()")
    print("")
    print("# 2. 分析失败")
    print("analyzer = FailureAnalyzer()")
    print("analysis = analyzer.analyze_failures(report)")
    print("")
    print("# 3. 查看分析结果")
    print("analyzer.print_analysis(analysis)")
    print("")
    print("# 4. 保存分析结果")
    print("analyzer.save_analysis_json(analysis, 'outputs/analysis.json')")
