#!/usr/bin/env python3
"""
故障分类器 v1.0 - 生产就绪版本

整合：
- Day 1-2: Structured Output + Policy
- Day 3-5: 工具系统
- Day 6: 调用轨迹
- Day 8-9: 多工具协同
- Day 10-11: 错误处理与降级
- Day 12-13: 端到端集成与优化
"""
import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv

from src.models import IncidentResult
from src.policy import PolicyEngine
from src.trace_manager import TraceManager
from tools.tool_coordinator import ToolCoordinator

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IncidentClassifierV1:
    """
    故障分类器 v1.0

    特性：
    - ✓ 结构化输出（Pydantic）
    - ✓ Policy 规则兜底
    - ✓ 多工具协同（ToolCoordinator）
    - ✓ 智能调度（优先级、依赖）
    - ✓ 错误处理（超时、重试、降级）
    - ✓ 完整轨迹（TraceManager）
    - ✓ 性能监控
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        model: str = None,
        temperature: float = 0.3,
        trace_dir: str = "traces"
    ):
        """
        初始化分类器

        Args:
            model: 模型名称，默认从环境变量读取
            temperature: 温度参数
            trace_dir: 轨迹保存目录
        """
        # 配置 API
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        base_url = os.getenv("OPENAI_BASE_URL")

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url if base_url else None
        )
        self.model = model
        self.temperature = temperature

        # 初始化组件
        self.policy = PolicyEngine()
        self.trace = TraceManager(trace_dir=trace_dir)
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(exist_ok=True)

        logger.info(f"✓ 初始化故障分类器 v{self.VERSION}")
        logger.info(f"  模型: {model}")
        logger.info(f"  轨迹目录: {trace_dir}")

    def classify(self, incident_description: str) -> Dict[str, Any]:
        """
        分类故障（完整流程）

        Args:
            incident_description: 故障描述

        Returns:
            完整的分析结果
        """
        start_time = datetime.now()

        logger.info(f"\n{'='*80}")
        logger.info(f"开始分析故障 (v{self.VERSION})")
        logger.info(f"{'='*80}")
        logger.info(f"描述: {incident_description}")
        logger.info(f"{'='*80}\n")

        try:
            # 开始轨迹记录
            trace_id = self.trace.start_trace(incident_description)
            logger.info(f"轨迹 ID: {trace_id}")

            # Step 1: 初步分类（快速）
            logger.info(f"\n{'---'*20}")
            logger.info("Step 1: 初步分类")
            logger.info(f"{'---'*20}")
            initial_classification = self._initial_classify(incident_description)
            logger.info(f"✓ 初步分类: {initial_classification['severity']} / {initial_classification['category']}")

            # Step 2: 规划工具调用
            logger.info(f"\n{'---'*20}")
            logger.info("Step 2: 规划工具调用")
            logger.info(f"{'---'*20}")
            coordinator = ToolCoordinator(self)
            tool_plan = coordinator.plan_tool_calls(
                incident_description,
                initial_classification
            )
            logger.info(f"✓ 规划了 {len(tool_plan)} 个工具调用:")
            for i, step in enumerate(tool_plan, 1):
                logger.info(f"  {i}. {step['tool']:<25} - {step['reason']}")

            # Step 3: 执行工具调用
            logger.info(f"\n{'---'*20}")
            logger.info("Step 3: 执行工具调用")
            logger.info(f"{'---'*20}")
            evidence = coordinator.execute_plan()
            logger.info(f"✓ 收集证据: {len(evidence)} 个工具返回")

            # 输出工具执行指标
            metrics = coordinator.get_execution_metrics()
            robust_metrics = metrics['robust_executor_metrics']
            logger.info(f"  执行统计:")
            logger.info(f"    总调用: {robust_metrics['total_calls']}")
            logger.info(f"    成功率: {robust_metrics['success_rate']:.1%}")
            logger.info(f"    缓存命中率: {robust_metrics['cache_hit_rate']:.1%}")

            # Step 4: 综合分析
            logger.info(f"\n{'---'*20}")
            logger.info("Step 4: 综合分析")
            logger.info(f"{'---'*20}")
            final_classification = self._final_classify(
                incident_description,
                initial_classification,
                evidence
            )
            logger.info(f"✓ 初步结论: {final_classification['severity']}")

            # Step 5: Policy 规则修正
            logger.info(f"\n{'---'*20}")
            logger.info("Step 5: Policy 规则修正")
            logger.info(f"{'---'*20}")
            final_classification = self.policy.check_and_enforce(
                incident_description,
                final_classification
            )

            violations = self.policy.get_violations()
            if violations:
                logger.info(f"✓ 应用了 {len(violations)} 条 Policy 规则:")
                for v in violations:
                    logger.info(f"  - [{v.level.value}] {v.policy_name}: {v.message}")
            else:
                logger.info("✓ 无 Policy 修正")

            # Step 6: 生成报告
            result = self._build_report(
                incident_description,
                final_classification,
                evidence,
                coordinator,
                start_time
            )

            # 结束轨迹
            trace_file = self.trace.finish_trace(
                final_answer=final_classification,
                status="success"
            )
            result['trace']['file'] = trace_file

            logger.info(f"\n{'='*80}")
            logger.info(f"✅ 分析完成")
            logger.info(f"{'='*80}")
            logger.info(f"最终判断: {result['classification']['severity']} / {result['classification']['category']}")
            logger.info(f"需要审核: {result['classification']['needs_human_review']}")
            logger.info(f"耗时: {result['duration_seconds']}s")
            logger.info(f"轨迹: {trace_file}")
            logger.info(f"{'='*80}\n")

            return result

        except Exception as e:
            logger.error(f"❌ 分析失败: {e}", exc_info=True)

            # 记录失败轨迹
            try:
                trace_file = self.trace.finish_trace(
                    final_answer=None,
                    status="error",
                    error_message=str(e)
                )
            except:
                trace_file = None

            return self._build_error_report(
                incident_description,
                e,
                start_time,
                trace_file
            )

    def _initial_classify(self, description: str) -> Dict[str, Any]:
        """
        初步分类（快速判断）

        Args:
            description: 故障描述

        Returns:
            初步分类结果
        """
        system_prompt = """你是故障分类专家。快速判断严重程度和类别，输出纯 JSON。

严重程度判断标准：

P0（最高优先级）- 核心收入或数据安全受影响：
- 支付、订单创建失败或成功率明显下降
- 核心服务完全不可用或严重故障（错误率 > 10%）
- 用户无法登录或注册
- 数据丢失或安全漏洞

P1（高优先级）- 核心服务明显故障：
- 核心服务（推荐、搜索、广告）延迟严重或超时率高（> 10%）
- 数据库死锁、慢查询严重影响性能
- 服务频繁重启、OOM
- 部署后出现明显问题

P2（中优先级）- 非核心服务或部分影响：
- 非核心功能故障
- 低流量影响（< 10%）
- 已通过回滚恢复

P3（低优先级）- 观察即可：
- 低错误率（< 1%）且无趋势恶化
- 偶发问题

类别：
- availability: 可用性问题（错误、故障、不可用）
- latency: 延迟问题（慢、超时、响应时间长）
- database: 数据库问题（死锁、慢查询）
- deployment: 部署问题（部署后出现）
- unknown: 不确定

输出格式（纯 JSON）：
{"severity": "P0/P1/P2/P3", "category": "availability/latency/database/deployment/unknown"}"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"快速分类：{description}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        # 调试：检查响应类型
        if isinstance(response, str):
            # 某些 API 网关可能直接返回字符串
            logger.warning("API 返回字符串格式，尝试直接解析")
            return self._parse_json(response)

        text = response.choices[0].message.content.strip()
        return self._parse_json(text)

    def _final_classify(
        self,
        description: str,
        initial: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        最终分类（基于证据）

        Args:
            description: 故障描述
            initial: 初步分类结果
            evidence: 工具调用证据

        Returns:
            最终分类结果
        """
        # 构造证据摘要
        evidence_summary = self._summarize_evidence(evidence)

        system_prompt = """你是故障分析专家。基于证据做出准确判断。

严重程度标准：
- P0: 核心收入功能故障，支付/订单成功率下降，核心服务完全不可用（错误率 > 10%）
- P1: 核心服务明显故障，延迟严重或超时率 > 10%，数据库死锁严重，服务频繁 OOM
- P2: 非核心功能故障，低流量影响（< 10%），已回滚恢复
- P3: 低错误率（< 1%），偶发问题，无需立即处理

输出格式（纯 JSON）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须引用具体证据）",
  "recommendation": "具体处理建议"
}

needs_human_review 判断：
- false: 低影响且无需立即处理（如错误率 < 1% 且已恢复）
- true: 需要人工确认影响范围、执行处理、或做决策"""

        prompt = f"""分析故障并给出最终判断。

【故障描述】
{description}

【初步判断】
严重程度: {initial['severity']}
类别: {initial['category']}

【收集的证据】
{evidence_summary}

请基于以上证据，输出最终分类结果（纯 JSON）。"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )

        # 调试：检查响应类型
        if isinstance(response, str):
            logger.warning("API 返回字符串格式，尝试直接解析")
            return self._parse_json(response)

        text = response.choices[0].message.content.strip()
        return self._parse_json(text)

    def _summarize_evidence(self, evidence: Dict[str, Any]) -> str:
        """
        总结证据

        Args:
            evidence: 工具调用结果

        Returns:
            证据摘要文本
        """
        if not evidence:
            return "（未收集到证据）"

        lines = []
        for tool_name, result in evidence.items():
            # 处理不同类型的结果
            if isinstance(result, dict) and result.get("fallback"):
                # 降级结果
                lines.append(f"- {tool_name}: 降级 ({result.get('error', 'unknown')})")
            elif isinstance(result, list):
                lines.append(f"- {tool_name}: {len(result)} 条记录")
                # 显示前3条
                for i, item in enumerate(result[:3], 1):
                    if isinstance(item, dict):
                        summary = item.get('message') or item.get('description') or str(item)[:100]
                        lines.append(f"  {i}. {summary}")
            elif isinstance(result, dict):
                lines.append(f"- {tool_name}: " + json.dumps(result, ensure_ascii=False)[:200])
            else:
                lines.append(f"- {tool_name}: {str(result)[:100]}")

        return "\n".join(lines)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        解析 JSON（清理 markdown 包裹）

        Args:
            text: 待解析文本

        Returns:
            解析后的字典
        """
        try:
            cleaned = text.strip()

            # 移除 markdown 代码块标记
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]

            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()
            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.error(f"原始文本: {text}")

            # 返回安全的默认值
            return {
                "severity": "P3",
                "category": "unknown",
                "needs_human_review": True,
                "rationale": f"解析失败: {text}"
            }

    def _build_report(
        self,
        description: str,
        classification: Dict[str, Any],
        evidence: Dict[str, Any],
        coordinator: ToolCoordinator,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        构建完整报告

        Args:
            description: 故障描述
            classification: 分类结果
            evidence: 证据
            coordinator: 工具协调器
            start_time: 开始时间

        Returns:
            完整报告
        """
        duration = (datetime.now() - start_time).total_seconds()

        # 获取性能指标
        metrics = coordinator.get_execution_metrics()
        robust_metrics = metrics['robust_executor_metrics']

        # 获取 Policy 违反记录
        violations = self.policy.get_violations()

        # 获取轨迹摘要
        trace_summary = self.trace.get_summary()

        return {
            "version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "description": description,
            "classification": classification,
            "evidence_summary": {
                tool: (len(result) if isinstance(result, list)
                      else "降级" if isinstance(result, dict) and result.get("fallback")
                      else "成功")
                for tool, result in evidence.items()
            },
            "policy_violations": [
                {
                    "policy": v.policy_name,
                    "level": v.level.value,
                    "action": v.action.value,
                    "message": v.message,
                    "original_value": v.original_value,
                    "corrected_value": v.corrected_value
                }
                for v in violations
            ],
            "performance": {
                "tool_calls": robust_metrics['total_calls'],
                "success_rate": round(robust_metrics['success_rate'], 3),
                "cache_hit_rate": round(robust_metrics['cache_hit_rate'], 3),
                "avg_tool_time": round(robust_metrics['avg_time'], 3)
            },
            "trace": {
                "trace_id": self.trace.current_trace.trace_id if self.trace.current_trace else None,
                "total_calls": trace_summary['total_tool_calls'],
                "file": None  # 将在 classify() 中填充
            },
            "success": True
        }

    def _build_error_report(
        self,
        description: str,
        error: Exception,
        start_time: datetime,
        trace_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建错误报告

        Args:
            description: 故障描述
            error: 异常对象
            start_time: 开始时间
            trace_file: 轨迹文件路径

        Returns:
            错误报告
        """
        duration = (datetime.now() - start_time).total_seconds()

        return {
            "version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "description": description,
            "classification": {
                "severity": "P3",
                "category": "unknown",
                "needs_human_review": True,
                "rationale": "分析失败，需要人工介入",
                "recommendation": "请人工检查系统日志"
            },
            "evidence_summary": {},
            "policy_violations": [],
            "performance": {
                "tool_calls": 0,
                "success_rate": 0,
                "cache_hit_rate": 0,
                "avg_tool_time": 0
            },
            "error": str(error),
            "trace": {
                "trace_id": self.trace.current_trace.trace_id if self.trace.current_trace else None,
                "file": trace_file
            },
            "success": False
        }

    def _execute_tool_with_trace(self, tool_name: str, tool_arguments: str) -> Any:
        """
        执行工具并记录轨迹

        供 ToolCoordinator 调用

        Args:
            tool_name: 工具名称
            tool_arguments: 工具参数（JSON 字符串）

        Returns:
            工具执行结果
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
                success=False,
                error_message=str(e)
            )

            return {"error": f"工具执行失败: {e}"}


# 命令行工具
def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python incident_classifier_v1.py <故障描述>")
        print("\n示例:")
        print('  python incident_classifier_v1.py "支付接口 5xx 错误率 35%"')
        print('  python incident_classifier_v1.py "推荐系统 P99 延迟从 500ms 升至 2 秒"')
        sys.exit(1)

    description = " ".join(sys.argv[1:])

    # 创建分类器
    classifier = IncidentClassifierV1()

    # 执行分类
    result = classifier.classify(description)

    # 输出结果
    print(f"\n{'='*80}")
    print("分析结果")
    print(f"{'='*80}")
    print(f"严重程度: {result['classification']['severity']}")
    print(f"类别: {result['classification']['category']}")
    print(f"需要审核: {result['classification']['needs_human_review']}")

    print(f"\n分析依据:")
    print(result['classification']['rationale'])

    if result['classification'].get('recommendation'):
        print(f"\n处理建议:")
        print(result['classification']['recommendation'])

    print(f"\n性能统计:")
    perf = result.get('performance', {})
    print(f"  工具调用: {perf.get('tool_calls', 0)}")
    print(f"  成功率: {perf.get('success_rate', 0):.1%}")
    print(f"  缓存命中率: {perf.get('cache_hit_rate', 0):.1%}")
    print(f"  平均耗时: {perf.get('avg_tool_time', 0):.3f}s")
    print(f"  总耗时: {result['duration_seconds']}s")

    if result.get('policy_violations'):
        print(f"\nPolicy 修正:")
        for v in result['policy_violations']:
            print(f"  - [{v['level']}] {v['policy']}: {v['message']}")

    print(f"\n轨迹文件: {result['trace']['file']}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
