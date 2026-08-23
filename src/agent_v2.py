"""
Day 6: Agent with ToolCoordinator (规则驱动版本)

使用 ToolCoordinator 规划工具调用，而不是让 LLM 自己决定
"""
import os
import json
import logging
from typing import Dict, Any
from anthropic import Anthropic

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import IncidentResult
from src.policy import PolicyEngine
from src.trace_manager import TraceManager
from tools.tool_coordinator import ToolCoordinator

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


class IncidentAgentV2:
    """故障分析 Agent（ToolCoordinator 版本）"""

    def __init__(
        self,
        model: str = None,
        temperature: float = 0.3
    ):
        if model is None:
            model = get_model()

        # 使用 Anthropic SDK
        base_url = get_base_url()
        if base_url and base_url.endswith('/v1'):
            base_url = base_url[:-3]

        self.client = Anthropic(
            api_key=get_api_key(),
            base_url=base_url if base_url else None
        )
        self.model = model
        self.temperature = temperature

        self.policy = PolicyEngine()
        self.trace = TraceManager()
        self.coordinator = ToolCoordinator(self)

        logger.info(f"初始化 Agent V2: model={model}, 使用 ToolCoordinator")

    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """分析故障（使用 ToolCoordinator）"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("开始分析故障 (ToolCoordinator 模式)")
            logger.info("=" * 80)
            logger.info(f"描述: {incident_description}")

            # 开始轨迹记录
            self.trace.start_trace(incident_description)

            # Step 1: 快速初步分类（不用工具）
            logger.info("\n--- Step 1: 快速分类 ---")
            initial_classification = self._quick_classify(incident_description)
            logger.info(f"初步分类: severity={initial_classification['severity']}, category={initial_classification['category']}")

            # Step 2: ToolCoordinator 规划工具调用
            logger.info("\n--- Step 2: 规划工具调用 ---")
            plan = self.coordinator.plan_tool_calls(
                incident_description,
                initial_classification
            )
            logger.info(f"规划了 {len(plan)} 个工具调用")
            for i, step in enumerate(plan, 1):
                logger.info(f"  {i}. {step['tool']} - {step['reason']}")

            # Step 3: 执行工具调用计划
            logger.info("\n--- Step 3: 执行工具调用 ---")
            evidence = self.coordinator.execute_plan()
            logger.info(f"收集了 {len(evidence)} 个工具结果")

            # Step 4: 基于证据做最终分类
            logger.info("\n--- Step 4: 最终分类 ---")
            final_classification = self._final_classify_with_evidence(
                incident_description,
                initial_classification,
                evidence
            )

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

            # 转换 evidence 格式（coordinator 返回的是 dict）
            evidence_list = [
                {
                    "tool": tool_name,
                    "arguments": {},
                    "result": result
                }
                for tool_name, result in evidence.items()
            ]

            return {
                "classification": final_classification,
                "evidence": evidence_list,
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

    def _quick_classify(self, description: str) -> Dict[str, Any]:
        """
        快速初步分类（不调用工具）

        目的：
        1. 判断严重程度（P0/P1/P2/P3）
        2. 判断类别（availability/latency/database/deployment/unknown）
        3. 为 ToolCoordinator 提供规划依据
        """
        system_prompt = """你是故障分类专家。快速判断严重程度和类别，输出纯 JSON。

严重程度判断：
- P0: 核心功能不可用（支付、订单、登录）
- P1: 核心服务明显故障（数据库、延迟严重）
- P2: 非核心服务或轻微影响
- P3: 低影响、观察

类别判断：
- availability: 可用性问题（错误、故障、不可用）
- latency: 延迟问题（慢、超时）
- database: 数据库问题（死锁、慢查询）
- deployment: 部署问题（部署后出现、回滚）
- unknown: 不确定

输出格式（纯 JSON，不要 markdown）：
{"severity": "P0/P1/P2/P3", "category": "availability/latency/database/deployment/unknown"}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"快速分类：{description}"
            }],
            temperature=0.1
        )

        text = response.content[0].text.strip()
        return self._parse_json(text)

    def _final_classify_with_evidence(
        self,
        description: str,
        initial: Dict,
        evidence: Dict
    ) -> Dict[str, Any]:
        """
        基于证据做最终分类

        参数：
        - description: 故障描述
        - initial: 初步分类结果
        - evidence: 工具调用的证据
        """
        # 构造 evidence 摘要
        evidence_summary = []
        for tool_name, result in evidence.items():
            evidence_summary.append(f"【{tool_name}】\n{json.dumps(result, ensure_ascii=False, indent=2)}")

        evidence_text = "\n\n".join(evidence_summary) if evidence_summary else "（未收集到证据）"

        system_prompt = """你是故障分析专家。基于证据做出准确判断。

输出格式（纯 JSON，不要 markdown）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须引用具体证据）"
}

needs_human_review 判断：
- false: 低影响且无需立即处理（如错误率 < 1%）
- true: 需要人工确认影响范围、执行处理、或做决策"""

        prompt = f"""分析故障并给出最终判断。

【故障描述】
{description}

【初步判断】
严重程度: {initial['severity']}
类别: {initial['category']}

【收集的证据】
{evidence_text}

请基于以上证据，输出最终分类结果（纯 JSON）。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )

        text = response.content[0].text.strip()
        return self._parse_json(text)

    def _parse_json(self, text: str) -> Dict:
        """解析 JSON（清理 markdown 包裹）"""
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.error(f"解析 JSON 失败: {text}")
            return {
                "severity": "P3",
                "category": "unknown",
                "needs_human_review": True,
                "rationale": text
            }

    def _execute_tool_with_trace(self, tool_name: str, tool_arguments: str) -> Any:
        """
        执行工具并记录轨迹

        供 ToolCoordinator 调用
        """
        from tools.executor import execute_tool

        try:
            # 解析参数
            args = json.loads(tool_arguments) if isinstance(tool_arguments, str) else tool_arguments

            # 执行工具
            result = execute_tool(tool_name, args)

            # 记录到轨迹
            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=args,
                tool_output=result,
                success=True
            )

            return result

        except Exception as e:
            logger.error(f"工具执行失败: {e}")

            # 记录失败
            self.trace.record_tool_call(
                tool_name=tool_name,
                tool_input=tool_arguments,
                tool_output={"error": str(e)},
                success=False
            )

            return {"error": f"工具执行失败: {e}"}


def main():
    """测试 Agent V2"""
    agent = IncidentAgentV2()

    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "MySQL 报 1205 死锁错误，影响订单创建",
        "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次"
    ]

    print("=" * 80)
    print("故障分析 Agent V2 测试 (ToolCoordinator)")
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
            print(f"  {j}. {ev['tool']}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
