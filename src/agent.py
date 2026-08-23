"""
Day 4: Agent with Tool-Calling Loop (Anthropic SDK 版本)

使用 Anthropic 原生 SDK 实现，支持：
1. 主动决定是否需要调用工具
2. 执行多轮对话
3. 限制调用次数防止无限循环
4. 记录完整的调用轨迹
"""
import os
import json
import logging
from typing import Dict, Any, List
from anthropic import Anthropic

# 导入我们前 3 天创建的模块
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.policy import PolicyEngine
from src.trace_manager import TraceManager
from tools import get_all_tool_definitions, execute_tool

# 导入配置工具
try:
    from src.config import get_api_key, get_base_url, get_model
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()
    get_api_key = lambda: os.getenv("ANTHROPIC_API_KEY")
    get_base_url = lambda: None
    get_model = lambda: os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncidentAgent:
    """故障分析 Agent（Anthropic SDK）"""

    def __init__(
        self,
        model: str = None,
        temperature: float = 0.3,
        max_rounds: int = 5
    ):
        if model is None:
            model = get_model()

        # 使用 Anthropic SDK
        base_url = get_base_url()

        # 如果 base_url 以 /v1 结尾，移除它（Anthropic SDK 会自动添加）
        if base_url and base_url.endswith('/v1'):
            base_url = base_url[:-3]

        self.client = Anthropic(
            api_key=get_api_key(),
            base_url=base_url if base_url else None
        )
        self.model = model
        self.temperature = temperature
        self.max_rounds = max_rounds

        self.policy = PolicyEngine()
        self.trace = TraceManager()

        logger.info(f"初始化 Agent: model={model}, max_rounds={max_rounds}")

    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """分析故障（完整流程）"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("开始分析故障")
            logger.info("=" * 80)
            logger.info(f"描述: {incident_description}")

            # 开始轨迹记录
            self.trace.start_trace(incident_description)

            # 构建初始消息
            system_prompt = self._build_system_prompt()
            messages = [{
                "role": "user",
                "content": f"分析以下故障：\n\n{incident_description}"
            }]

            # 转换工具定义为 Anthropic 格式
            tools = self._convert_tools()

            # Tool-Calling Loop
            evidence = []
            final_classification = None

            for round_num in range(self.max_rounds):
                logger.info(f"\n--- Round {round_num + 1} ---")

                # 调用 Anthropic API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                    temperature=self.temperature
                )

                # 检查是否有工具调用
                tool_uses = [block for block in response.content if block.type == "tool_use"]

                if not tool_uses:
                    # 没有工具调用，LLM 给出最终答案
                    logger.info("✓ LLM 给出最终答案")

                    # 提取文本内容
                    text_blocks = [block.text for block in response.content if block.type == "text"]
                    response_text = "\n".join(text_blocks) if text_blocks else ""

                    # 解析 JSON
                    final_classification = self._parse_final_answer(response_text)
                    break

                # 有工具调用
                logger.info(f"→ LLM 请求调用 {len(tool_uses)} 个工具")

                # 添加 assistant 消息
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # 执行工具并收集结果
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input

                    logger.info(f"  执行: {tool_name}")

                    # 检查调用次数限制
                    if not self.trace.can_call_tool():
                        logger.warning(f"  ⚠️  工具调用次数已达上限")
                        tool_result_content = json.dumps({
                            "error": "工具调用次数超限"
                        }, ensure_ascii=False)
                    else:
                        # 执行工具
                        result = self._execute_tool_safe(tool_name, tool_input)
                        tool_result_content = json.dumps(result, ensure_ascii=False)

                        # 记录证据
                        evidence.append({
                            "tool": tool_name,
                            "arguments": tool_input,
                            "result": result
                        })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result_content
                    })

                    logger.info(f"  ✓ 工具执行完成")

                # 添加工具结果消息
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # 如果工具调用次数已达上限，添加提示
                if not self.trace.can_call_tool():
                    messages.append({
                        "role": "user",
                        "content": "工具调用次数已达上限。请基于现有证据立即输出最终分类结果（纯 JSON 格式）。"
                    })

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

    def _build_system_prompt(self) -> str:
        """构造系统提示词"""
        return """你是故障分析专家。

你的任务：分析故障并给出建议。

可用工具：
- search_logs: 搜索服务日志

分析流程：
1. 理解故障描述
2. 如果需要更多证据，调用 search_logs 查看日志（最多 2 次）
3. **看到工具结果后，立即输出分析结果，不要再调用工具**

输出格式（纯 JSON，不要 markdown）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须基于具体证据）"
}

注意事项：
1. 最多调用 2 次工具
2. 调用工具后，必须基于结果输出 JSON，不要继续调用
3. 如果信息充分，直接给出结果，不要无意义地调用工具
4. rationale 必须详细，说明基于什么证据做出判断
5. 只输出 JSON，不要其他文字"""

    def _convert_tools(self) -> List[Dict]:
        """转换工具定义为 Anthropic 格式"""
        tools = []
        for tool_def in get_all_tool_definitions():
            tools.append({
                "name": tool_def["function"]["name"],
                "description": tool_def["function"]["description"],
                "input_schema": tool_def["function"]["parameters"]
            })
        return tools

    def _execute_tool_safe(self, tool_name: str, tool_input: Dict) -> Any:
        """安全执行工具"""
        try:
            # 执行工具
            result = execute_tool(tool_name, tool_input)

            # 记录到轨迹
            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=result,
                success=True
            )

            return result

        except Exception as e:
            logger.error(f"工具执行失败: {e}")

            # 记录失败
            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output={"error": str(e)},
                success=False
            )

            return {"error": f"工具执行失败: {e}"}

    def _parse_final_answer(self, response_text: str) -> Dict:
        """解析最终答案"""
        try:
            # 清理可能的 markdown 包裹
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

            # 解析 JSON
            return json.loads(cleaned_text)

        except json.JSONDecodeError:
            logger.error(f"解析 LLM 输出失败: {response_text}")
            return {
                "severity": "P3",
                "category": "unknown",
                "needs_human_review": True,
                "rationale": response_text
            }


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

    for i, description in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {description}")
        print("-" * 80)

        result = agent.analyze(description)

        print(f"\n【分析结果】")
        print(f"严重程度: {result['classification']['severity']}")
        print(f"类别: {result['classification']['category']}")
        print(f"需要审核: {result['classification']['needs_human_review']}")
        print(f"依据: {result['classification']['rationale']}")

        print(f"\n【证据】")
        print(f"调用工具: {len(result['evidence'])} 次")
        for j, ev in enumerate(result['evidence'], 1):
            print(f"  {j}. {ev['tool']}({ev['arguments']})")

        print(f"\n【轨迹】")
        print(f"文件: {result['trace_file']}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
