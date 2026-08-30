"""
测试 Day 19-20 性能优化功能
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.performance_metrics import PerformanceCollector, PerformanceMetrics
from tools.benchmark import PerformanceBenchmark
from tools.cache_warmup import CacheWarmup
from tools.async_executor import AsyncExecutor, TaskStatus
from tools.robust_executor import RobustToolExecutor


class TestPerformanceMetrics:
    """测试性能指标收集"""

    def test_collector_basic(self):
        """测试基本收集功能"""
        collector = PerformanceCollector()
        collector.reset()

        # 记录步骤
        collector.start_step("step1")
        collector.end_step("step1")

        # 记录调用
        collector.record_llm_call()
        collector.record_tool_call()
        collector.record_cache_hit()

        # 获取指标
        metrics = collector.get_metrics()

        assert "step1" in metrics.step_durations
        assert metrics.llm_calls == 1
        assert metrics.tool_calls == 1
        assert metrics.cache_hits == 1

    def test_metrics_to_dict(self):
        """测试指标转换为字典"""
        metrics = PerformanceMetrics()
        metrics.llm_calls = 3
        metrics.tool_calls = 5
        metrics.cache_hits = 2
        metrics.cache_misses = 3

        data = metrics.to_dict()

        assert data["llm_calls"] == 3
        assert data["tool_calls"] == 5
        assert data["cache_hit_rate"] == 0.4  # 2/(2+3)

    def test_cache_hit_rate(self):
        """测试缓存命中率计算"""
        metrics = PerformanceMetrics()

        # 无调用
        assert metrics.get_cache_hit_rate() == 0.0

        # 50% 命中率
        metrics.cache_hits = 5
        metrics.cache_misses = 5
        assert metrics.get_cache_hit_rate() == 0.5

        # 100% 命中率
        metrics.cache_hits = 10
        metrics.cache_misses = 0
        assert metrics.get_cache_hit_rate() == 1.0


class TestCacheWarmup:
    """测试缓存预热"""

    def test_get_common_queries(self):
        """测试获取常见查询"""
        executor = RobustToolExecutor()
        warmup = CacheWarmup(executor)

        queries = warmup.get_common_queries()

        # 应该有多个常见查询
        assert len(queries) > 0

        # 每个查询应该有必要字段
        for query in queries:
            assert "tool" in query
            assert "params" in query
            assert "description" in query

    def test_warmup_structure(self):
        """测试预热结果结构"""
        executor = RobustToolExecutor()
        warmup = CacheWarmup(executor)

        # 只预热一个查询（避免真实 API 调用）
        class MockExecutor:
            def execute(self, tool, params):
                return {"mock": True}

        warmup.executor = MockExecutor()

        results = warmup.warmup(parallel=False)

        # 检查结果结构
        assert "total" in results
        assert "success" in results
        assert "failed" in results
        assert "details" in results


class TestAsyncExecutor:
    """测试异步执行器"""

    def test_task_status(self):
        """测试任务状态管理"""
        executor = AsyncExecutor()

        # 模拟任务
        task_id = "test-task-123"
        executor.tasks[task_id] = {
            "status": TaskStatus.COMPLETED,
            "result": {"test": "data"},
            "error": None
        }

        # 获取状态
        status = executor.get_task_status(task_id)
        assert status is not None
        assert status["status"] == TaskStatus.COMPLETED

        # 获取结果
        result = executor.get_task_result(task_id)
        assert result == {"test": "data"}

    def test_nonexistent_task(self):
        """测试不存在的任务"""
        executor = AsyncExecutor()

        status = executor.get_task_status("nonexistent")
        assert status is None

        result = executor.get_task_result("nonexistent")
        assert result is None


class TestBenchmark:
    """测试基准测试"""

    def test_benchmark_structure(self):
        """测试基准测试结果结构"""
        # 创建模拟 agent
        class MockAgent:
            def analyze(self, description):
                return {"mock": True}

        agent = MockAgent()
        benchmark = PerformanceBenchmark()

        test_cases = ["case1", "case2"]

        results = benchmark.run_benchmark(
            agent=agent,
            test_cases=test_cases,
            iterations=2
        )

        # 检查结果结构
        assert "results" in results
        assert "summary" in results

        summary = results["summary"]
        assert "total_cases" in summary
        assert "successful_cases" in summary
        assert "avg" in summary
        assert "p95" in summary


class TestIntegration:
    """集成测试"""

    def test_collector_with_coordinator(self):
        """测试收集器与协调器集成"""
        from tools.tool_coordinator import ToolCoordinator
        from tools.performance_metrics import get_collector

        # 创建模拟 agent
        class MockAgent:
            def __init__(self):
                self.trace = MockTrace()

        class MockTrace:
            def can_call_tool(self):
                return True

        agent = MockAgent()
        coordinator = ToolCoordinator(agent)

        # 协调器应该有收集器
        assert coordinator.collector is not None
        assert coordinator.collector == get_collector()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
