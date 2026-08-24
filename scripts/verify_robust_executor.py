#!/usr/bin/env python3
"""
快速验证脚本 - 验证健壮执行器是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.tool_coordinator import ToolCoordinator
from src.trace_manager import TraceManager

print("=" * 60)
print("验证健壮执行器集成")
print("=" * 60)

# 创建模拟 Agent
class MockAgent:
    def __init__(self):
        self.trace = TraceManager()

agent = MockAgent()
coordinator = ToolCoordinator(agent)

# 测试工具映射
print("\n1. 验证工具映射...")
tools = [
    "search_logs",
    "search_runbooks",
    "search_slow_queries",
    "get_deployment_history",
    "search_oom_events",
    "search_timeout_events"
]

for tool_name in tools:
    try:
        tool_func = coordinator._get_tool_function(tool_name)
        print(f"  ✓ {tool_name}: {tool_func.__name__}")
    except Exception as e:
        print(f"  ✗ {tool_name}: {e}")
        sys.exit(1)

# 测试健壮执行器
print("\n2. 验证健壮执行器...")
print(f"  ✓ RobustExecutor: {coordinator.robust_executor}")

# 测试性能指标
print("\n3. 验证性能指标...")
metrics = coordinator.get_execution_metrics()
print(f"  ✓ 缓存统计: {metrics['cache_stats']}")
print(f"  ✓ 健壮执行器指标: {metrics['robust_executor_metrics']}")

print("\n" + "=" * 60)
print("✓ 所有验证通过！")
print("=" * 60)
