"""
自动化优化建议生成器

根据失败模式自动生成具体的代码优化建议
"""
from typing import List, Dict, Any
from tests.failure_analyzer import FailureAnalyzer
from tests.evaluation_framework import EvaluationReport


class OptimizationAdvisor:
    """
    自动化优化建议生成器

    根据失败模式生成具体的代码修改建议
    """

    def __init__(self):
        self.analyzer = FailureAnalyzer()

    def generate_advice(
        self,
        report: EvaluationReport
    ) -> Dict[str, Any]:
        """
        生成优化建议

        Args:
            report: 评测报告

        Returns:
            优化建议（包含具体代码）
        """
        # 先分析失败
        analysis = self.analyzer.analyze_failures(report)

        if analysis["total_failures"] == 0:
            return {
                "status": "no_failures",
                "message": "没有失败案例，系统表现优秀！",
                "suggestions": []
            }

        # 为每种失败模式生成具体建议
        suggestions = []

        for pattern in analysis["patterns"]:
            pattern_type = pattern.pattern_type

            if pattern_type == "severity_underestimate":
                suggestions.append(self._suggest_for_underestimate(pattern, analysis))
            elif pattern_type == "severity_overestimate":
                suggestions.append(self._suggest_for_overestimate(pattern, analysis))
            elif pattern_type == "category_wrong":
                suggestions.append(self._suggest_for_category_wrong(pattern, analysis))
            elif pattern_type == "edge_case_failure":
                suggestions.append(self._suggest_for_edge_case(pattern, analysis))
            elif pattern_type == "system_error":
                suggestions.append(self._suggest_for_system_error(pattern, analysis))

        return {
            "status": "success",
            "total_failures": analysis["total_failures"],
            "patterns_found": len(analysis["patterns"]),
            "suggestions": suggestions,
            "summary": self._generate_summary(suggestions)
        }

    def _suggest_for_underestimate(
        self,
        pattern: Dict,
        analysis: Dict
    ) -> Dict[str, Any]:
        """生成严重程度低估的优化建议"""
        # 分析具体是哪些案例被低估
        details = analysis["details"]
        underestimated = [d for d in details if d["failure_type"] == "severity_underestimate"]

        # 提取关键词
        keywords = set()
        threshold_issues = []

        for case in underestimated:
            desc = case["description"].lower()

            # 识别关键词
            if "oom" in desc or "内存" in desc:
                keywords.add("OOM")
            if "连接池" in desc or "connection pool" in desc:
                keywords.add("连接池")
            if "错误率" in desc or "error rate" in desc:
                # 提取错误率
                import re
                match = re.search(r'(\d+)%', case["description"])
                if match:
                    rate = int(match.group(1))
                    if 5 <= rate <= 10:
                        threshold_issues.append(rate)
            if "部署" in desc or "deployment" in desc:
                keywords.add("部署")
            if "暴增" in desc or "surge" in desc:
                keywords.add("暴增")

        # 生成具体建议
        suggestion = {
            "priority": 1,
            "pattern": "严重程度低估",
            "affected_count": pattern.count,
            "file": "src/incident_classifier_v1.py",
            "action": "优化提示词",
            "specific_changes": []
        }

        if keywords or threshold_issues:
            changes = []

            # 针对错误率阈值
            if threshold_issues:
                avg_rate = sum(threshold_issues) / len(threshold_issues)
                changes.append({
                    "location": "初步分类提示词（第 240-260 行）",
                    "issue": f"错误率 {int(avg_rate)}% 被低估",
                    "current": "P1: 核心服务明显故障",
                    "suggested": f"""P1（高优先级）- 核心服务明显故障（务必准确判断）：
- 错误率 5-10%（注意：虽未达到 P0 的 >10%，但已严重影响用户体验）
- 核心服务延迟严重或超时率高（> 10%）""",
                    "reason": f"明确指出 {int(avg_rate)}% 的错误率属于 P1，不是 P2"
                })

            # 针对 OOM
            if "OOM" in keywords:
                changes.append({
                    "location": "初步分类提示词（第 240-260 行）",
                    "issue": "OOM 问题被低估",
                    "current": "P1: 服务频繁重启、OOM",
                    "suggested": """P1（高优先级）- 核心服务明显故障（务必准确判断）：
- 服务频繁重启、内存溢出（OOM）、资源耗尽""",
                    "reason": "强调 OOM 的严重性（服务不稳定，随时可能完全挂掉）"
                })

            # 针对连接池
            if "连接池" in keywords:
                changes.append({
                    "location": "初步分类提示词（第 240-260 行）",
                    "issue": "连接池耗尽被低估",
                    "current": "P1: 数据库死锁、慢查询严重影响性能",
                    "suggested": """P1（高优先级）- 核心服务明显故障（务必准确判断）：
- 数据库死锁、慢查询严重影响性能，或连接池耗尽""",
                    "reason": "连接池耗尽会导致新请求无法处理，属于严重问题"
                })

            # 针对部署问题
            if "部署" in keywords or "暴增" in keywords:
                changes.append({
                    "location": "初步分类提示词（第 240-260 行）",
                    "issue": "部署后问题被低估",
                    "current": "P1: 部署后出现明显问题",
                    "suggested": """P1（高优先级）- 核心服务明显故障（务必准确判断）：
- 部署后出现明显问题（错误日志暴增、错误率上升）""",
                    "reason": "部署后问题需要立即处理，防止影响扩大"
                })

            # 添加关键判断点
            if threshold_issues or "OOM" in keywords or "连接池" in keywords:
                changes.append({
                    "location": "最终分类提示词（第 310-320 行）",
                    "issue": "缺少明确的判断指引",
                    "current": "严重程度标准：...",
                    "suggested": f"""关键判断点：
1. 错误率 {int(avg_rate) if threshold_issues else 8}% → P1（不是 P2，已经严重影响用户体验）
2. OOM、连接池耗尽 → P1（服务不稳定，随时可能完全挂掉）
3. 部署后错误暴增 → P1（需要立即处理）""",
                    "reason": "直接告诉模型如何判断，避免歧义"
                })

            suggestion["specific_changes"] = changes

        return suggestion

    def _suggest_for_overestimate(
        self,
        pattern: Dict,
        analysis: Dict
    ) -> Dict[str, Any]:
        """生成严重程度高估的优化建议"""
        return {
            "priority": 1,
            "pattern": "严重程度高估",
            "affected_count": pattern.count,
            "file": "src/incident_classifier_v1.py",
            "action": "放宽 P0/P1 判断标准",
            "specific_changes": [
                {
                    "location": "初步分类提示词（第 240-260 行）",
                    "issue": "P0/P1 定义过于宽泛",
                    "suggested": """加强 P0 的限定条件：
P0（最高优先级）- 核心收入或数据安全受影响（仅限以下情况）：
- 支付、订单创建失败或成功率明显下降（> 10%）
- 核心服务完全不可用或严重故障（错误率 > 10%，注意必须 >10%）
- 用户完全无法登录或注册""",
                    "reason": "强调 P0 的阈值，避免过度判断"
                }
            ]
        }

    def _suggest_for_category_wrong(
        self,
        pattern: Dict,
        analysis: Dict
    ) -> Dict[str, Any]:
        """生成类别判断错误的优化建议"""
        # 分析具体的类别混淆
        details = analysis["details"]
        category_errors = [d for d in details if d["failure_type"] == "category_wrong"]

        # 统计混淆对
        confusions = {}
        for case in category_errors:
            key = f"{case['expected']['category']}→{case['actual']['category']}"
            if key not in confusions:
                confusions[key] = []
            confusions[key].append(case["description"])

        # 找出最常见的混淆
        most_common = max(confusions.items(), key=lambda x: len(x[1]))

        return {
            "priority": 2,
            "pattern": "类别判断错误",
            "affected_count": pattern.count,
            "file": "src/incident_classifier_v1.py",
            "action": "增加类别区分示例",
            "specific_changes": [
                {
                    "location": "初步分类提示词（第 261-270 行）",
                    "issue": f"类别混淆: {most_common[0]}",
                    "suggested": f"""增加对比示例：
- {most_common[0].split('→')[0]}: （举例说明）
- {most_common[0].split('→')[1]}: （举例说明）

示例描述:
{most_common[1][0][:100]}...""",
                    "reason": f"明确区分 {most_common[0]}"
                }
            ]
        }

    def _suggest_for_edge_case(
        self,
        pattern: Dict,
        analysis: Dict
    ) -> Dict[str, Any]:
        """生成边界案例的优化建议"""
        return {
            "priority": 3,
            "pattern": "边界案例失败",
            "affected_count": pattern.count,
            "file": "src/incident_classifier_v1.py",
            "action": "增加输入验证和默认处理",
            "specific_changes": [
                {
                    "location": "classify() 方法开始（第 93-110 行）",
                    "issue": "缺少输入验证",
                    "suggested": """def classify(self, incident_description: str) -> Dict[str, Any]:
    # 输入验证
    if not incident_description or not incident_description.strip():
        return {
            "success": True,
            "classification": {
                "severity": "P3",
                "category": "unknown",
                "reasoning": "空输入，无法判断"
            }
        }

    if len(incident_description.strip()) < 10:
        # 描述过短，可能是测试输入
        pass  # 继续处理，但标记为低优先级""",
                    "reason": "增加边界情况处理，防止崩溃或误判"
                }
            ]
        }

    def _suggest_for_system_error(
        self,
        pattern: Dict,
        analysis: Dict
    ) -> Dict[str, Any]:
        """生成系统错误的优化建议"""
        return {
            "priority": 1,
            "pattern": "系统错误",
            "affected_count": pattern.count,
            "file": "多个文件",
            "action": "修复代码 Bug 或配置错误",
            "specific_changes": [
                {
                    "location": "需要查看错误日志",
                    "issue": "系统运行时错误",
                    "suggested": """检查项：
1. API 配置是否正确（.env 文件）
2. 超时时间是否合理
3. 异常处理是否完整
4. 网络连接是否稳定""",
                    "reason": "系统错误需要修复代码，不是提示词问题"
                }
            ]
        }

    def _generate_summary(self, suggestions: List[Dict]) -> str:
        """生成优化建议摘要"""
        if not suggestions:
            return "没有优化建议"

        lines = []
        lines.append(f"发现 {len(suggestions)} 个优化方向：")

        for i, sug in enumerate(suggestions, 1):
            lines.append(f"{i}. [{sug['pattern']}] 影响 {sug['affected_count']} 个案例")
            lines.append(f"   文件: {sug['file']}")
            lines.append(f"   操作: {sug['action']}")

        return "\n".join(lines)

    def print_advice(self, advice: Dict[str, Any]):
        """打印优化建议"""
        print("\n" + "=" * 60)
        print("自动化优化建议")
        print("=" * 60)

        if advice["status"] == "no_failures":
            print(f"\n✅ {advice['message']}")
            return

        print(f"\n失败案例数: {advice['total_failures']}")
        print(f"失败模式数: {advice['patterns_found']}")

        print(f"\n{advice['summary']}")

        for i, suggestion in enumerate(advice["suggestions"], 1):
            print(f"\n{'─' * 60}")
            print(f"建议 {i}: {suggestion['pattern']}")
            print(f"{'─' * 60}")
            print(f"优先级: {suggestion['priority']}")
            print(f"影响案例: {suggestion['affected_count']} 个")
            print(f"修改文件: {suggestion['file']}")
            print(f"操作: {suggestion['action']}")

            if suggestion.get("specific_changes"):
                print(f"\n具体修改建议:")
                for j, change in enumerate(suggestion["specific_changes"], 1):
                    print(f"\n  修改 {j}:")
                    print(f"  位置: {change['location']}")
                    print(f"  问题: {change['issue']}")
                    if change.get("current"):
                        print(f"  当前: {change['current']}")
                    print(f"  建议:")
                    for line in change["suggested"].split('\n'):
                        print(f"    {line}")
                    print(f"  原因: {change['reason']}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    """
    使用示例
    """
    print("自动化优化建议使用示例:")
    print("\nfrom tests.optimization_advisor import OptimizationAdvisor")
    print("from tests.evaluation_framework import EvaluationFramework")
    print("")
    print("# 1. 运行评测")
    print("framework = EvaluationFramework(agent)")
    print("report = framework.run_evaluation()")
    print("")
    print("# 2. 生成优化建议")
    print("advisor = OptimizationAdvisor()")
    print("advice = advisor.generate_advice(report)")
    print("")
    print("# 3. 查看建议")
    print("advisor.print_advice(advice)")
