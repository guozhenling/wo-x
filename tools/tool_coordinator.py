# tool_coordinator.py
"""
工具协调器 - 智能管理多工具调用
"""
import json
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolPriority(Enum):
    """工具优先级"""
    REQUIRED = "required"  # 必须调用
    IMPORTANT = "important"  # 重要，优先调用
    OPTIONAL = "optional"  # 可选，按需调用


class ToolCoordinator:
    """
    工具协调器

    功能：
    - 管理工具调用顺序
    - 处理工具依赖
    - 优化调用策略
    """

    def __init__(self, agent):
        self.agent = agent
        self.execution_plan = []

    def plan_tool_calls(
            self,
            incident_description: str,
            initial_classification: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        规划工具调用

        根据故障描述和初步分类，决定：
        - 调用哪些工具
        - 按什么顺序
        - 是否并行
        """
        plan = []
        severity = initial_classification.get('severity', 'P3')
        category = initial_classification.get('category', 'unknown')

        # 规则 1: 所有故障都查日志（优先级高）
        plan.append({
            "tool": "search_logs",
            "priority": ToolPriority.REQUIRED,
            "arguments": self._get_log_search_args(incident_description),
            "reason": "获取错误证据"
        })

        # 规则 2: P0/P1 必须查 Runbook
        if severity in ['P0', 'P1']:
            plan.append({
                "tool": "search_runbooks",
                "priority": ToolPriority.REQUIRED,
                "arguments": {
                    "description": incident_description,
                    "severity": severity,
                    "category": category
                },
                "reason": "高优先级故障需要标准处理流程",
                "depends_on": ["search_logs"]  # 依赖日志结果
            })

        # 规则 3: 数据库问题查慢查询
        if category == "database":
            plan.append({
                "tool": "search_slow_queries",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {"time_range": 60},
                "reason": "数据库问题需要查慢查询"
            })

        # 规则 4: 部署问题查发布历史
        if category == "deployment" or "部署" in incident_description:
            plan.append({
                "tool": "get_deployment_history",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {"hours": 24},
                "reason": "可能与最近部署相关"
            })

        # 规则 5: OOM/重启问题查 OOM 事件
        if any(keyword in incident_description.lower() for keyword in
               ["oom", "内存", "重启", "killed", "crash", "pod"]):
            plan.append({
                "tool": "search_oom_events",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {"time_range": 120, "min_restart_count": 0},
                "reason": "可能存在内存溢出问题"
            })

        # 规则 6: 延迟/超时问题查搜推广超时
        if category == "latency" or any(keyword in incident_description.lower() for keyword in
               ["超时", "延迟", "慢", "timeout", "latency", "推荐", "搜索", "广告"]):
            # 识别服务类型
            service = None
            if "推荐" in incident_description or "recommendation" in incident_description.lower():
                service = "recommendation"
            elif "搜索" in incident_description or "search" in incident_description.lower():
                service = "search"
            elif "广告" in incident_description or "ad" in incident_description.lower():
                service = "ad"

            plan.append({
                "tool": "search_timeout_events",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {
                    "time_range": 60,
                    "service": service,
                    "status": "timeout"  # 只查超时事件
                },
                "reason": "延迟问题需要分析超时事件"
            })

        self.execution_plan = plan
        return plan

    def execute_plan(self) -> Dict[str, Any]:
        """
        执行工具调用计划

        按优先级和依赖关系执行
        """
        results = {}

        # 按优先级排序
        sorted_plan = sorted(
            self.execution_plan,
            key=lambda x: (
                0 if x['priority'] == ToolPriority.REQUIRED else
                1 if x['priority'] == ToolPriority.IMPORTANT else 2
            )
        )

        for step in sorted_plan:
            tool_name = step['tool']

            # 检查依赖
            if 'depends_on' in step:
                missing_deps = [
                    dep for dep in step['depends_on']
                    if dep not in results
                ]
                if missing_deps:
                    logger.warning(f"跳过 {tool_name}，缺少依赖: {missing_deps}")
                    continue

            # 检查是否可以调用
            if not self.agent.trace.can_call_tool():
                logger.warning(f"跳过 {tool_name}，调用次数超限")
                continue

            # 执行工具
            logger.info(f"执行: {tool_name} ({step['reason']})")
            result = self.agent._execute_tool_with_trace(
                tool_name,
                json.dumps(step['arguments'])
            )

            results[tool_name] = result

            # 根据结果调整后续计划
            self._adjust_plan_based_on_result(tool_name, result)

        return results

    def _get_log_search_args(self, description: str) -> Dict[str, Any]:
        """根据描述推断日志搜索参数"""
        args = {"keyword": "ERROR", "limit": 20}

        # 提取服务名
        services = ["payment", "order", "user", "recommendation"]
        for service in services:
            if service in description.lower() or service in description:
                args["service"] = service
                break

        if "service" not in args:
            # 默认支付（最关键）
            args["service"] = "payment"

        return args

    def _adjust_plan_based_on_result(
            self,
            tool_name: str,
            result: Any
    ):
        """根据工具结果调整后续计划"""
        # 例如：如果日志显示 5xx 很多，提高 Runbook 查询优先级
        if tool_name == "search_logs":
            if isinstance(result, list) and len(result) > 10:
                logger.info("日志错误较多，提高 Runbook 查询优先级")
                for step in self.execution_plan:
                    if step['tool'] == 'search_runbooks':
                        step['priority'] = ToolPriority.REQUIRED


# 测试
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from src.trace_manager import TraceManager

    # 模拟测试
    class MockAgent:
        def __init__(self):
            self.trace = TraceManager()

        def _execute_tool_with_trace(self, tool_name, args):
            print(f"  执行 {tool_name}({args})")
            return {"success": True}


    agent = MockAgent()
    coordinator = ToolCoordinator(agent)

    # 测试 P0 故障
    print("测试 1: P0 支付故障")
    print("=" * 60)
    plan = coordinator.plan_tool_calls(
        "支付接口 5xx 错误率 35%",
        {"severity": "P0", "category": "availability"}
    )

    print("执行计划:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step['tool']} - {step['reason']}")
        print(f"   优先级: {step['priority'].value}")

    print("\n执行:")
    coordinator.execute_plan()