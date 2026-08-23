# tests/test_tools.py
"""
Day 3: 测试工具系统

验证：
1. log_search 工具能正常工作
2. tool_definitions 格式正确
3. executor 能正确调用工具
"""
import pytest
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools import search_logs, execute_tool, get_all_tool_definitions


class TestLogSearch:
    """测试日志搜索工具"""

    def test_search_by_service(self):
        """测试：按服务名搜索"""
        logs = search_logs(service="payment", limit=5)

        assert isinstance(logs, list)
        assert len(logs) <= 5
        # 所有日志都应该是 payment 服务的
        for log in logs:
            assert log['service'] == 'payment'

    def test_search_with_keyword(self):
        """测试：关键字搜索"""
        logs = search_logs(service="payment", keyword="timeout", limit=10)

        assert isinstance(logs, list)
        # 所有日志都应该包含 timeout
        for log in logs:
            assert 'timeout' in log['message'].lower()

    def test_limit_enforcement(self):
        """测试：限制条数"""
        logs = search_logs(service="payment", limit=3)

        assert len(logs) <= 3

    def test_no_results(self):
        """测试：没有匹配结果"""
        logs = search_logs(service="payment", keyword="nonexistent_keyword_xyz")

        assert isinstance(logs, list)
        assert len(logs) == 0

    def test_all_services(self):
        """测试：所有服务都能查询"""
        services = ["payment", "order", "user", "recommendation"]

        for service in services:
            logs = search_logs(service=service, limit=5)
            assert isinstance(logs, list)


class TestToolDefinitions:
    """测试工具定义"""

    def test_definition_structure(self):
        """测试：定义结构完整"""
        definitions = get_all_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) >= 1  # 至少有 search_logs

        # 检查第一个工具定义
        tool_def = definitions[0]
        assert 'type' in tool_def
        assert 'function' in tool_def

        func = tool_def['function']
        assert 'name' in func
        assert 'description' in func
        assert 'parameters' in func

    def test_search_logs_definition(self):
        """测试：search_logs 定义"""
        definitions = get_all_tool_definitions()

        # 找到 search_logs
        search_logs_def = None
        for d in definitions:
            if d['function']['name'] == 'search_logs':
                search_logs_def = d
                break

        assert search_logs_def is not None

        # 验证参数定义
        params = search_logs_def['function']['parameters']
        assert 'service' in params['properties']
        assert 'keyword' in params['properties']
        assert 'limit' in params['properties']

        # service 是必需参数
        assert 'service' in params['required']


class TestToolExecutor:
    """测试工具执行器"""

    def test_execute_search_logs(self):
        """测试：执行 search_logs"""
        result = execute_tool(
            "search_logs",
            {"service": "payment", "limit": 3}
        )

        assert isinstance(result, list)
        assert len(result) <= 3

    def test_unknown_tool(self):
        """测试：未知工具"""
        with pytest.raises(ValueError) as exc_info:
            execute_tool("unknown_tool", {})

        assert "未知工具" in str(exc_info.value)

    def test_invalid_arguments(self):
        """测试：无效参数"""
        with pytest.raises(ValueError):
            execute_tool("search_logs", {"invalid_param": "test"})

    def test_missing_required_argument(self):
        """测试：缺少必需参数"""
        with pytest.raises(Exception):  # 可能是 ValueError 或 TypeError
            execute_tool("search_logs", {})  # 缺少 service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
