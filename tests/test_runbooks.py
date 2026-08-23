# tests/test_runbooks.py
"""
Day 5: 测试 Runbook 检索

验证：
1. Runbook 加载成功
2. 关键词匹配准确
3. 返回相关结果
"""
import pytest
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools import search_runbooks, RunbookSearcher


class TestRunbookSearch:
    """测试 Runbook 检索"""

    def test_search_payment_5xx(self):
        """测试：支付 5xx 问题"""
        results = search_runbooks("支付接口 5xx 错误率 35%", severity="P0")

        assert isinstance(results, list)
        assert len(results) > 0

        # 应该匹配到支付相关的 Runbook
        best_match = results[0]
        assert '支付' in best_match['title'] or 'payment' in best_match['title'].lower()
        assert best_match['score'] > 0

    def test_search_database_deadlock(self):
        """测试：数据库死锁"""
        results = search_runbooks("MySQL 报 1205 死锁错误", category="database")

        assert isinstance(results, list)
        assert len(results) > 0

        # 应该匹配到数据库相关的 Runbook
        best_match = results[0]
        assert '数据库' in best_match['title'] or 'deadlock' in best_match['title'].lower()

    def test_search_deployment(self):
        """测试：部署问题"""
        results = search_runbooks("发布后服务报错，需要回滚")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_no_match(self):
        """测试：无匹配结果"""
        results = search_runbooks("这是一个完全不相关的描述xyz123")

        # 可能返回空列表或分数很低的结果
        assert isinstance(results, list)

    def test_with_severity_filter(self):
        """测试：严重程度过滤"""
        results_p0 = search_runbooks("支付报错", severity="P0")
        results_p2 = search_runbooks("推荐延迟", severity="P2")

        assert isinstance(results_p0, list)
        assert isinstance(results_p2, list)

    def test_result_structure(self):
        """测试：返回结果结构"""
        results = search_runbooks("支付 5xx")

        assert len(results) > 0

        result = results[0]
        # 验证必需字段
        assert 'title' in result
        assert 'score' in result
        assert 'matched_keywords' in result
        assert 'check_steps' in result

        # check_steps 应该是列表
        assert isinstance(result['check_steps'], list)


class TestRunbookSearcher:
    """测试 RunbookSearcher 类"""

    @pytest.fixture
    def searcher(self):
        """创建 searcher 实例"""
        return RunbookSearcher()

    def test_load_runbooks(self, searcher):
        """测试：Runbook 加载"""
        assert len(searcher.runbooks) > 0

    def test_search_method(self, searcher):
        """测试：search 方法"""
        results = searcher.search("支付 5xx", top_k=2)

        assert isinstance(results, list)
        assert len(results) <= 2

    def test_scoring(self, searcher):
        """测试：评分逻辑"""
        # 高匹配度
        results_high = searcher.search("支付接口 5xx gateway timeout", severity="P0")

        # 低匹配度
        results_low = searcher.search("系统慢")

        if results_high and results_low:
            # 高匹配度应该得分更高
            assert results_high[0]['score'] >= results_low[0]['score']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
