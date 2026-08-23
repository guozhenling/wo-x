"""
Day 3: 工具执行器（Tool Executor）

负责：
- 将工具名映射到实际的 Python 函数
- 执行工具调用
- 处理错误

这是连接 LLM 和实际工具的桥梁。
"""
import sys
import os
from typing import Dict, Any
import logging

# 支持直接运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from tools.log_search import search_logs
    from tools.runbook_search import search_runbooks
    from tools.slow_query_search import search_slow_queries
    from tools.deployment_history import get_deployment_history
    from tools.oom_search import search_oom_events
    from tools.timeout_search import search_timeout_events
else:
    from .log_search import search_logs
    from .runbook_search import search_runbooks
    from .slow_query_search import search_slow_queries
    from .deployment_history import get_deployment_history
    from .oom_search import search_oom_events
    from .timeout_search import search_timeout_events

logger = logging.getLogger(__name__)


def execute_tool(
    tool_name: str,
    tool_arguments: Dict[str, Any]
) -> Any:
    """
    执行工具调用

    Args:
        tool_name: 工具名称（来自 LLM）
        tool_arguments: 工具参数（来自 LLM，JSON 对象）

    Returns:
        工具执行结果

    Raises:
        ValueError: 工具不存在或参数不合法
        RuntimeError: 工具执行失败

    示例：
        result = execute_tool(
            "search_logs",
            {"service": "payment", "limit": 10}
        )
    """
    # 工具映射表
    TOOL_REGISTRY = {
        "search_logs": search_logs,
        "search_runbooks": search_runbooks,
        "search_slow_queries": search_slow_queries,
        "get_deployment_history": get_deployment_history,
        "search_oom_events": search_oom_events,
        "search_timeout_events": search_timeout_events,
    }

    # 检查工具是否存在
    if tool_name not in TOOL_REGISTRY:
        logger.error(f"未知工具: {tool_name}")
        raise ValueError(f"未知工具: {tool_name}")

    tool_function = TOOL_REGISTRY[tool_name]

    try:
        # 执行工具
        logger.info(f"执行工具: {tool_name}({tool_arguments})")
        result = tool_function(**tool_arguments)
        logger.info(f"工具执行成功: {tool_name}")
        return result

    except TypeError as e:
        # 参数错误（参数名不匹配或缺少必需参数）
        logger.error(f"工具参数错误: {e}")
        raise ValueError(f"参数错误: {e}")

    except Exception as e:
        # 其他错误
        logger.error(f"工具执行失败: {e}", exc_info=True)
        raise RuntimeError(f"工具执行失败: {e}")


if __name__ == "__main__":
    # 测试工具执行器
    print("测试工具执行器\n")

    # 测试 1: 正确调用
    print("1. 正确调用:")
    try:
        result = execute_tool("search_logs", {"service": "payment", "limit": 3})
        print(f"   ✓ 返回 {len(result)} 条日志")
    except Exception as e:
        print(f"   ✗ 失败: {e}")

    # 测试 2: 错误的工具名
    print("\n2. 错误的工具名:")
    try:
        result = execute_tool("unknown_tool", {})
        print(f"   ✗ 应该失败但通过了")
    except ValueError as e:
        print(f"   ✓ 正确拒绝: {e}")

    # 测试 3: 错误的参数
    print("\n3. 错误的参数:")
    try:
        result = execute_tool("search_logs", {"invalid_param": "test"})
        print(f"   ✗ 应该失败但通过了")
    except ValueError as e:
        print(f"   ✓ 正确拒绝: {e}")

    # 测试 4: 缺少必需参数
    print("\n4. 缺少必需参数:")
    try:
        result = execute_tool("search_logs", {})  # 缺少 service
        print(f"   ✗ 应该失败但通过了")
    except Exception as e:
        print(f"   ✓ 正确拒绝: {e}")

    print("\n✅ 测试完成")
