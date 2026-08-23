#!/usr/bin/env python3
"""
日志搜索工具测试

测试覆盖：
1. 成功查询
2. 无结果
3. 非法参数
4. 超出上限
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from log_search import LogSearchTool, SearchLogsInput, SearchLogsResult, search_logs
from pydantic import ValidationError


class TestSearchLogsInput:
    """测试输入参数校验"""

    def test_valid_input(self):
        """测试有效输入"""
        input_data = SearchLogsInput(service="payment", keyword="timeout", limit=10)
        assert input_data.service == "payment"
        assert input_data.keyword == "timeout"
        assert input_data.limit == 10

    def test_empty_service_rejected(self):
        """测试空服务名被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            SearchLogsInput(service="", keyword="test", limit=10)
        assert "服务名不能为空" in str(exc_info.value)

    def test_whitespace_service_rejected(self):
        """测试纯空格服务名被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            SearchLogsInput(service="   ", keyword="test", limit=10)
        assert "服务名不能为空" in str(exc_info.value)

    def test_keyword_too_long_rejected(self):
        """测试过长关键字被拒绝"""
        long_keyword = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            SearchLogsInput(service="payment", keyword=long_keyword, limit=10)
        assert "关键字长度不能超过100字符" in str(exc_info.value)

    def test_limit_exceeds_max_rejected(self):
        """测试 limit 超过20被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            SearchLogsInput(service="payment", keyword="test", limit=21)
        assert "limit 不能超过20" in str(exc_info.value)

    def test_limit_zero_rejected(self):
        """测试 limit 为0被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            SearchLogsInput(service="payment", keyword="test", limit=0)
        assert "limit 必须大于0" in str(exc_info.value)

    def test_keyword_exactly_100_chars_accepted(self):
        """测试关键字正好100字符被接受"""
        keyword = "a" * 100
        input_data = SearchLogsInput(service="payment", keyword=keyword, limit=10)
        assert input_data.keyword == keyword

    def test_keyword_optional(self):
        """测试关键字可选"""
        input_data = SearchLogsInput(service="payment", limit=10)
        assert input_data.keyword is None


class TestLogSearchTool:
    """测试日志搜索工具"""

    @pytest.fixture
    def tool(self):
        """创建日志搜索工具实例"""
        return LogSearchTool(log_file_path="data/logs.jsonl", timeout_seconds=1.0)

    def test_successful_search_with_keyword(self, tool):
        """测试成功查询（带关键字）"""
        result = tool.search(service="payment", keyword="timeout", limit=10)

        assert isinstance(result, SearchLogsResult)
        assert result.total > 0
        assert len(result.logs) > 0
        assert all(log.service == "payment" for log in result.logs)
        assert all("timeout" in log.message.lower() for log in result.logs)
        assert result.search_time_ms >= 0

    def test_successful_search_without_keyword(self, tool):
        """测试成功查询（无关键字）"""
        result = tool.search(service="payment", limit=5)

        assert isinstance(result, SearchLogsResult)
        assert result.total > 0
        assert len(result.logs) <= 5
        assert all(log.service == "payment" for log in result.logs)

    def test_no_results_found(self, tool):
        """测试无结果"""
        result = tool.search(service="nonexistent_service", limit=10)

        assert isinstance(result, SearchLogsResult)
        assert result.total == 0
        assert len(result.logs) == 0
        assert result.search_time_ms >= 0

    def test_no_results_with_keyword_not_found(self, tool):
        """测试关键字未匹配"""
        result = tool.search(service="payment", keyword="nonexistent_keyword_12345", limit=10)

        assert isinstance(result, SearchLogsResult)
        assert result.total == 0
        assert len(result.logs) == 0

    def test_empty_service_rejected(self, tool):
        """测试空服务名被拒绝"""
        with pytest.raises(ValidationError):
            tool.search(service="", limit=10)

    def test_limit_exceeds_max_rejected(self, tool):
        """测试 limit 超过20被拒绝"""
        with pytest.raises(ValidationError):
            tool.search(service="payment", limit=21)

    def test_keyword_too_long_rejected(self, tool):
        """测试过长关键字被拒绝"""
        long_keyword = "a" * 101
        with pytest.raises(ValidationError):
            tool.search(service="payment", keyword=long_keyword, limit=10)

    def test_limit_respected(self, tool):
        """测试 limit 限制生效"""
        result = tool.search(service="payment", limit=3)

        assert result.total <= 3
        assert len(result.logs) <= 3

    def test_case_insensitive_keyword_search(self, tool):
        """测试关键字搜索大小写不敏感"""
        result1 = tool.search(service="payment", keyword="TIMEOUT", limit=10)
        result2 = tool.search(service="payment", keyword="timeout", limit=10)

        assert result1.total == result2.total

    def test_search_different_services(self, tool):
        """测试搜索不同服务"""
        payment_result = tool.search(service="payment", limit=20)
        order_result = tool.search(service="order", limit=20)
        user_result = tool.search(service="user", limit=20)

        assert payment_result.total > 0
        assert order_result.total > 0
        assert user_result.total > 0

        # 验证服务名正确
        assert all(log.service == "payment" for log in payment_result.logs)
        assert all(log.service == "order" for log in order_result.logs)
        assert all(log.service == "user" for log in user_result.logs)


class TestConvenienceFunction:
    """测试便捷函数"""

    def test_search_logs_function(self):
        """测试 search_logs 便捷函数"""
        result = search_logs(service="payment", keyword="gateway", limit=5)

        assert isinstance(result, SearchLogsResult)
        assert result.total > 0
        assert all(log.service == "payment" for log in result.logs)


class TestTimeout:
    """测试超时保护"""

    def test_timeout_not_triggered_on_small_dataset(self):
        """测试小数据集不触发超时"""
        tool = LogSearchTool(log_file_path="data/logs.jsonl", timeout_seconds=1.0)
        result = tool.search(service="payment", limit=10)

        # 应该成功完成，不抛出 TimeoutError
        assert isinstance(result, SearchLogsResult)
        assert result.search_time_ms < 1000  # 应该远小于超时时间


@pytest.mark.parametrize("service,keyword,limit,should_pass", [
    ("payment", "timeout", 10, True),       # 正常查询
    ("payment", None, 5, True),             # 无关键字
    ("", "test", 10, False),                # 空服务名
    ("payment", "a" * 101, 10, False),      # 关键字过长
    ("payment", "test", 21, False),         # limit 超限
    ("payment", "test", 0, False),          # limit 为0
    ("nonexistent", "test", 10, True),      # 不存在的服务（不报错，返回空）
])
def test_parametrized_validation(service, keyword, limit, should_pass):
    """参数化测试：各种参数组合"""
    tool = LogSearchTool(log_file_path="data/logs.jsonl")

    if should_pass:
        result = tool.search(service=service, keyword=keyword, limit=limit)
        assert isinstance(result, SearchLogsResult)
    else:
        with pytest.raises((ValidationError, ValueError)):
            tool.search(service=service, keyword=keyword, limit=limit)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
