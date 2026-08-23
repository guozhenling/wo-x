"""
Day 4: Agent with Tool-Calling Loop

实现完整的 Agent，能够：
1. 主动决定是否需要调用工具
2. 执行多轮对话（user → assistant → tool → assistant）
3. 限制调用次数防止无限循环
4. 记录完整的调用轨迹
"""
import os
import json
import logging
from typing import Dict, Any, List
from openai import OpenAI

# 导入我们前 3 天创建的模块
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import IncidentResult
from src.policy import PolicyEngine
from src.trace_manager import TraceManager
from tools import get_all_tool_definitions, execute_tool

# 导入配置工具（会自动加载 config.yaml 或 .env）
try:
    from src.config import get_api_key, get_base_url, get_model
except ImportError:
    # 如果没有 config.py，使用 dotenv
    from dotenv import load_dotenv
    load_dotenv()
    get_api_key = lambda: os.getenv("OPENAI_API_KEY")
    get_base_url = lambda: os.getenv("OPENAI_BASE_URL")
    get_model = lambda: os.getenv("OPENAI_MODEL", "claude-sonnet-5")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncidentAgent:
    """
    故障分析 Agent

    整合 Day 1-3 的所有功能：
    - Day 1: Structured Output
    - Day 2: Policy 规则
    - Day 3: 工具系统
    - Day 4: Tool-Calling Loop（今天）

    工作流程：
    1. 接收故障描述
    2. 决定是否需要查日志
    3. 如果需要，调用 search_logs
    4. 基于日志给出分析
    5. Policy 规则修正
    6. 返回最终结果
    """

    def __init__(
        self,
        model: str = None,  # None 表示使用配置文件中的模型
        temperature: float = 0.3,
        max_rounds: int = 5
    ):
        """
        初始化 Agent

        Args:
            model: LLM 模型，None 则从配置文件读取
            temperature: 温度参数
            max_rounds: 最大对话轮数
        """
        if model is None:
            model = get_model()

        self.client = OpenAI(
            api_key=get_api_key() or os.getenv("OPENAI_API_KEY"),
            base_url=get_base_url() or os.getenv("OPENAI_BASE_URL")
        )
        self.model = model
        self.temperature = temperature
        self.max_rounds = max_rounds

        self.policy = PolicyEngine()
        self.trace = TraceManager()

        logger.info(f"初始化 Agent: model={model}, max_rounds={max_rounds}")

    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """
        分析故障（完整流程）

        Args:
            incident_description: 故障描述

        Returns:
            完整的分析结果，包含：
            - classification: 分类结果
            - evidence: 工具调用的证据
            - trace_file: 调用轨迹文件路径
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"开始分析故障")
        logger.info(f"{'='*80}")
        logger.info(f"描述: {incident_description}")

        # 开始轨迹记录
        trace_id = self.trace.start_trace(incident_description)

        try:
            # 构造初始消息
            messages = self._build_initial_messages(incident_description)

            # Tool-Calling Loop
            final_classification = None
            evidence = []

            for round_num in range(self.max_rounds):
                logger.info(f"\n--- Round {round_num + 1} ---")

                # 调用 LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=get_all_tool_definitions(),
                    temperature=self.temperature
                )

                message = response.choices[0].message

                # 检查是否有工具调用
                if not message.tool_calls:
                    # 没有工具调用，说明 LLM 准备给出最终答案
                    logger.info("✓ LLM 给出最终答案")

                    try:
                        # 解析最终分类结果
                        final_classification = json.loads(message.content)
                        break
                    except json.JSONDecodeError:
                        logger.error(f"解析 LLM 输出失败: {message.content}")
                        # 尝试提取关键信息
                        final_classification = {
                            "severity": "P3",
                            "category": "unknown",
                            "needs_human_review": True,
                            "rationale": message.content
                        }
                        break

                # 有工具调用
                logger.info(f"→ LLM 请求调用 {len(message.tool_calls)} 个工具")

                # 添加 assistant 消息（包含工具调用请求）
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                # 执行每个工具调用
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments

                    logger.info(f"  执行: {tool_name}")
                    logger.debug(f"  参数: {tool_args_str}")

                    # 检查调用次数限制
                    if not self.trace.can_call_tool():
                        logger.warning(f"  ⚠️  工具调用次数已达上限")
                        tool_result = {
                            "error": "工具调用次数超限，证据不足"
                        }
                    else:
                        # 执行工具
                        tool_result = self._execute_tool_safe(
                            tool_name,
                            tool_args_str
                        )

                        # 记录证据
                        evidence.append({
                            "tool": tool_name,
                            "arguments": json.loads(tool_args_str),
                            "result": tool_result
                        })

                    # 添加工具结果消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

                    logger.info(f"  ✓ 工具执行完成")

            # 检查是否得到最终结果
            if not final_classification:
                logger.warning("⚠️  达到最大轮数仍未得到结果")
                final_classification = {
                    "severity": "P3",
                    "category": "unknown",
                    "needs_human_review": True,
                    "rationale": "分析超时，证据不足，需要人工介入"
                }

            # 应用 Policy 规则
            logger.info("\n应用 Policy 规则...")
            final_classification = self.policy.check_and_enforce(
                incident_description,
                final_classification
            )

            # 结束轨迹记录
            trace_file = self.trace.finish_trace(
                final_answer=final_classification,
                status="success"
            )

            logger.info(f"\n✅ 分析完成")
            logger.info(f"最终判断: {final_classification['severity']}")

            return {
                "classification": final_classification,
                "evidence": evidence,
                "trace_file": trace_file,
                "trace_summary": self.trace.get_summary()
            }

        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)

            # 记录失败
            trace_file = self.trace.finish_trace(
                final_answer=None,
                status="error",
                error_message=str(e)
            )

            return {
                "classification": {
                    "severity": "P3",
                    "category": "unknown",
                    "needs_human_review": True,
                    "rationale": f"分析失败: {e}"
                },
                "evidence": [],
                "trace_file": trace_file,
                "error": str(e)
            }

    def _build_initial_messages(self, description: str) -> List[Dict[str, Any]]:
        """构造初始消息"""
        system_prompt = """你是故障分析专家。

你的任务：分析故障并给出建议。

可用工具：
- search_logs: 搜索服务日志

分析流程：
1. 理解故障描述
2. 如果需要更多证据，调用 search_logs 查看日志
3. 基于证据给出分析结果

输出格式（JSON）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须基于具体证据）"
}

注意事项：
1. 最多调用 2 次工具
2. 如果信息充分，直接给出结果，不要无意义地调用工具
3. rationale 必须详细，说明基于什么证据做出判断
4. 如果证据不足，明确说明"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析以下故障：\n\n{description}"}
        ]

    def _execute_tool_safe(
        self,
        tool_name: str,
        arguments_str: str
    ) -> Any:
        """
        安全执行工具

        处理所有可能的异常
        """
        try:
            # 解析参数
            arguments = json.loads(arguments_str)

            # 执行工具
            result = execute_tool(tool_name, arguments)

            # 记录到轨迹
            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=arguments,
                tool_output=result,
                success=True
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            error_msg = f"参数格式错误: {e}"

            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input={},
                tool_output=None,
                success=False,
                error_message=error_msg
            )

            return {"error": error_msg}

        except ValueError as e:
            logger.error(f"参数校验失败: {e}")
            error_msg = f"参数不合法: {e}"

            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=json.loads(arguments_str) if arguments_str else {},
                tool_output=None,
                success=False,
                error_message=error_msg
            )

            return {"error": error_msg}

        except Exception as e:
            logger.error(f"工具执行异常: {e}")
            error_msg = f"工具执行失败: {e}"

            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=json.loads(arguments_str) if arguments_str else {},
                tool_output=None,
                success=False,
                error_message=error_msg
            )

            return {"error": error_msg}


def main():
    """测试 Agent"""
    agent = IncidentAgent()

    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "MySQL 报 1205 死锁错误，影响订单创建"
    ]

    print("=" * 80)
    print("故障分析 Agent 测试")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case}")
        print("-" * 80)

        result = agent.analyze(case)

        print(f"\n【分析结果】")
        print(f"严重程度: {result['classification']['severity']}")
        print(f"类别: {result['classification']['category']}")
        print(f"需要审核: {result['classification']['needs_human_review']}")
        print(f"依据: {result['classification']['rationale']}")

        print(f"\n【证据】")
        print(f"调用工具: {len(result['evidence'])} 次")
        for j, evidence in enumerate(result['evidence'], 1):
            print(f"  {j}. {evidence['tool']}({evidence['arguments']})")

        print(f"\n【轨迹】")
        print(f"文件: {result['trace_file']}")

        print("\n" + "=" * 80)

        if i < len(test_cases):
            import time
            time.sleep(1)  # 避免 API 限流


if __name__ == "__main__":
    main()
