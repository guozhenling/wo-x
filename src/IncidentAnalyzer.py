# incident_analyzer.py
"""
完整的故障分析系统（整合 Day 1-6）
"""
import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Day 1-2
from models import IncidentResult
from policy import PolicyEngine

# Day 3, 5
from tools.tool_definitions import get_all_tool_definitions
from tools.executor import execute_tool

# Day 6
from trace_manager import TraceManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncidentAnalyzer:
    """
    完整的故障分析器

    整合：
    - Structured Output (Day 1)
    - Policy 规则 (Day 2)
    - 工具调用 (Day 3-5)
    - 轨迹管理 (Day 6)
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.policy = PolicyEngine()
        self.trace = None  # 每次分析创建新的

    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """
        完整的故障分析流程

        Args:
            incident_description: 故障描述

        Returns:
            分析结果，包含：
            - classification: 分类结果（Day 1-2）
            - evidence: 工具调用证据（Day 3-5）
            - recommendation: 处理建议（Day 5）
            - trace: 调用轨迹（Day 6）
        """
        # 初始化轨迹
        self.trace = TraceManager(
            max_calls_per_tool=2,
            max_total_calls=5,
            max_duration_seconds=30
        )

        logger.info(f"\n{'=' * 80}")
        logger.info(f"开始分析故障")
        logger.info(f"{'=' * 80}")
        logger.info(f"描述: {incident_description}")

        # Step 1: 初步分类（可能需要工具）
        messages = self._build_initial_messages(incident_description)

        # Step 2: Tool-Calling Loop
        classification, evidence = self._run_tool_calling_loop(
            messages,
            incident_description
        )

        # Step 3: Policy 规则修正
        if classification:
            logger.info("\n应用 Policy 规则...")
            classification = self.policy.check_and_enforce(
                incident_description,
                classification
            )

        # Step 4: 生成最终报告
        result = self._generate_report(
            incident_description,
            classification,
            evidence
        )

        # 打印轨迹
        self.trace.print_summary()

        # 保存轨迹
        trace_file = self.trace.save_to_file()
        result['trace_file'] = trace_file

        return result

    def _build_initial_messages(self, description: str) -> list:
        """构造初始消息"""
        system_prompt = """你是故障分析专家。

任务：分析故障并给出建议。

可用工具：
- search_logs: 搜索日志
- search_runbooks: 搜索处理手册

流程：
1. 理解故障描述
2. 如需更多证据，调用 search_logs
3. 调用 search_runbooks 查找处理流程
4. 给出分析结果

输出格式（JSON）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment",
  "needs_human_review": true/false,
  "rationale": "判断依据",
  "recommendation": "处理建议"
}"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析故障：{description}"}
        ]

    def _run_tool_calling_loop(
            self,
            messages: list,
            description: str
    ) -> tuple:
        """
        运行工具调用循环

        Returns:
            (classification, evidence)
        """
        evidence = {
            "logs": [],
            "runbooks": []
        }

        max_rounds = 5

        for round_num in range(max_rounds):
            logger.info(f"\n--- Round {round_num + 1} ---")

            # 调用 LLM
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=get_all_tool_definitions(),
                temperature=0.3
            )

            message = response.choices[0].message

            # 没有工具调用，返回最终结果
            if not message.tool_calls:
                logger.info("✓ 得到最终分析")

                try:
                    classification = json.loads(message.content)
                    return classification, evidence
                except:
                    # 如果不是 JSON，尝试提取
                    return {
                        "severity": "P3",
                        "category": "unknown",
                        "needs_human_review": True,
                        "rationale": message.content
                    }, evidence

            # 处理工具调用
            logger.info(f"→ LLM 请求 {len(message.tool_calls)} 个工具")
            messages.append(message.model_dump())

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args_str = tool_call.function.arguments

                # 执行工具
                result = self._execute_tool_with_trace(
                    tool_name,
                    args_str
                )

                # 记录证据
                if tool_name == "search_logs":
                    evidence["logs"].extend(result if isinstance(result, list) else [])
                elif tool_name == "search_runbooks":
                    evidence["runbooks"].extend(result if isinstance(result, list) else [])

                # 添加工具结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        # 超时
        return None, evidence

    def _execute_tool_with_trace(
            self,
            tool_name: str,
            arguments_str: str
    ) -> Any:
        """执行工具并记录轨迹"""
        import time

        logger.info(f"  执行: {tool_name}")

        # 检查调用限制
        if not self.trace.can_call(tool_name):
            logger.warning(f"  ⚠️  {tool_name} 调用次数超限")
            self.trace.record_call(
                tool_name,
                {},
                None,
                0,
                success=False,
                error="调用次数超限"
            )
            return {"error": "调用次数超限"}

        # 执行工具
        try:
            start = time.time()
            arguments = json.loads(arguments_str)
            result = execute_tool(tool_name, arguments)
            duration = (time.time() - start) * 1000

            # 记录成功
            self.trace.record_call(
                tool_name,
                arguments,
                result,
                duration,
                success=True
            )

            logger.info(f"  ✓ 完成 ({duration:.0f}ms)")
            return result

        except Exception as e:
            duration = (time.time() - start) * 1000 if 'start' in locals() else 0
            logger.error(f"  ✗ 失败: {e}")

            self.trace.record_call(
                tool_name,
                json.loads(arguments_str) if arguments_str else {},
                None,
                duration,
                success=False,
                error=str(e)
            )

            return {"error": str(e)}

    def _generate_report(
            self,
            description: str,
            classification: Dict[str, Any],
            evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成最终报告"""
        return {
            "description": description,
            "classification": classification,
            "evidence": {
                "logs_count": len(evidence.get("logs", [])),
                "runbooks_count": len(evidence.get("runbooks", [])),
                "logs_sample": evidence.get("logs", [])[:3],
                "runbooks": evidence.get("runbooks", [])
            },
            "trace_summary": self.trace.get_summary()
        }


# 主函数
def main():
    """测试完整流程"""
    analyzer = IncidentAnalyzer()

    # 测试案例
    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "数据库报 1205 死锁错误，影响订单创建"
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试案例 {i}")
        print(f"{'=' * 80}")

        result = analyzer.analyze(case)

        print(f"\n【分析结果】")
        print(f"严重程度: {result['classification']['severity']}")
        print(f"类别: {result['classification']['category']}")
        print(f"需要审核: {result['classification']['needs_human_review']}")
        print(f"依据: {result['classification']['rationale']}")

        if result['classification'].get('recommendation'):
            print(f"建议: {result['classification']['recommendation']}")

        print(f"\n【证据】")
        print(f"查询日志: {result['evidence']['logs_count']} 条")
        print(f"匹配 Runbook: {result['evidence']['runbooks_count']} 个")

        print(f"\n【调用统计】")
        summary = result['trace_summary']
        print(f"总调用: {summary['total_calls']}")
        print(f"成功: {summary['successful_calls']}")
        print(f"耗时: {summary['total_duration_ms']} ms")
        print(f"轨迹文件: {result['trace_file']}")

        print("\n" + "=" * 80)
        input("按回车继续下一个案例...")


if __name__ == "__main__":
    main()