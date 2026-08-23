# tools/__init__.py
"""
Day 3: 工具系统
Day 5: 新增 Runbook 检索

提供：
- log_search: 日志搜索工具
- runbook_search: Runbook 检索工具（Day 5 新增）
- tool_definitions: 工具定义（给 LLM）
- executor: 工具执行器
"""

from .log_search import search_logs, LogSearchTool
from .runbook_search import search_runbooks, RunbookSearcher
from .tool_definitions import get_all_tool_definitions, get_search_logs_definition, get_search_runbooks_definition
from .executor import execute_tool

__all__ = [
    'search_logs',
    'LogSearchTool',
    'search_runbooks',
    'RunbookSearcher',
    'get_all_tool_definitions',
    'get_search_logs_definition',
    'get_search_runbooks_definition',
    'execute_tool',
]
