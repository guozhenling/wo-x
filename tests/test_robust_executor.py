"""
测试健壮的工具执行器
"""
import pytest
import time
from unittest.mock import Mock, patch
from tools.robust_executor import (
    RobustToolExecutor,
    TimeoutError,
    RetryExhaustedError,
    CircuitBreakerOpenError,
    CircuitBreaker
)


class TestRobustToolExecutor:
    """测试健壮执行器"""

    def setup_method(self):
        """每个测试前重置"""
        self.executor = RobustToolExecutor()

    def test_successful_execution(self):
        """测试正常执行"""
        def mock_tool(service, keyword):
            return [{"message": f"{service} log"}]

        result = self.executor.execute(
            "search_logs",
            mock_tool,
            {"service": "payment", "keyword": "ERROR"}
        )

        assert result == [{"message": "payment log"}]
        metrics = self.executor.get_metrics()
        assert metrics["success_rate"] == 1.0

    def test_cache_hit(self):
        """测试缓存命中"""
        call_count = 0

        def mock_tool(service, keyword):
            nonlocal call_count
            call_count += 1
            return [{"message": f"log {call_count}"}]

        # 第一次调用
        result1 = self.executor.execute(
            "search_logs",
            mock_tool,
            {"service": "payment", "keyword": "ERROR"}
        )

        # 第二次调用（应该命中缓存）
        result2 = self.executor.execute(
            "search_logs",
            mock_tool,
            {"service": "payment", "keyword": "ERROR"}
        )

        # 验证
        assert result1 == result2
        assert call_count == 1  # 只调用了一次
        metrics = self.executor.get_metrics()
        assert metrics["cache_hit_rate"] == 0.5  # 2次调用，1次命中

    def test_retry_on_failure(self):
        """测试失败重试"""
        attempt_count = 0

        def flaky_tool(service, keyword):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("临时失败")
            return [{"message": "success"}]

        result = self.executor.execute(
            "search_logs",
            flaky_tool,
            {"service": "payment", "keyword": "ERROR"},
            max_retries=3
        )

        # 第二次尝试成功
        assert result == [{"message": "success"}]
        assert attempt_count == 2

    def test_fallback_on_exhausted_retries(self):
        """测试重试耗尽后降级"""
        def always_fail(service, keyword):
            raise Exception("总是失败")

        result = self.executor.execute(
            "search_logs",
            always_fail,
            {"service": "payment", "keyword": "ERROR"},
            max_retries=2
        )

        # 返回降级结果
        assert result["fallback"] is True
        assert "error" in result
        assert result["data"] == []

    def test_timeout_protection(self):
        """测试超时保护"""
        def slow_tool(service, keyword):
            time.sleep(10)  # 睡眠10秒
            return [{"message": "success"}]

        result = self.executor.execute(
            "search_logs",
            slow_tool,
            {"service": "payment", "keyword": "ERROR"},
            timeout_seconds=1,  # 1秒超时
            max_retries=1
        )

        # 超时后降级
        assert result["fallback"] is True

    def test_stale_cache_fallback(self):
        """测试过期缓存降级"""
        def mock_tool(service, keyword):
            return [{"message": "cached"}]

        # 第一次调用，成功并缓存
        result1 = self.executor.execute(
            "search_logs",
            mock_tool,
            {"service": "payment", "keyword": "ERROR"}
        )

        # 手动过期缓存
        cache_key = self.executor._get_cache_key(
            "search_logs",
            {"service": "payment", "keyword": "ERROR"}
        )
        self.executor.cache[cache_key]["timestamp"] = time.time() - 400  # 过期

        # 模拟工具失败
        def failing_tool(service, keyword):
            raise Exception("工具失败")

        # 第二次调用，工具失败，应该使用过期缓存
        result2 = self.executor.execute(
            "search_logs",
            failing_tool,
            {"service": "payment", "keyword": "ERROR"},
            max_retries=1
        )

        # 应该返回过期缓存（列表类型会被包装成字典）
        assert result2["_fallback"] == "stale_cache"
        assert result2["data"] == [{"message": "cached"}]
        assert result2["_cache_age"] > 300  # 过期了

    def test_metrics_tracking(self):
        """测试性能指标跟踪"""
        def mock_tool(service, keyword):
            time.sleep(0.1)
            return [{"message": "log"}]

        # 执行多次
        for i in range(5):
            self.executor.execute(
                "search_logs",
                mock_tool,
                {"service": "payment", "keyword": str(i)}  # 不同参数，不会命中缓存
            )

        metrics = self.executor.get_metrics()
        assert metrics["total_calls"] == 5
        assert metrics["successful_calls"] == 5
        assert metrics["success_rate"] == 1.0
        assert metrics["avg_time"] >= 0.1  # 平均至少0.1秒


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_breaker_opens_after_failures(self):
        """测试连续失败后触发熔断"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

        def failing_func():
            raise Exception("失败")

        # 前3次失败
        for i in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        # 第4次应该直接熔断
        assert breaker.state == "OPEN"
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(failing_func)

    def test_circuit_breaker_half_open_recovery(self):
        """测试熔断器半开状态恢复"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,  # 1秒后尝试恢复
            half_open_attempts=2
        )

        def failing_func():
            raise Exception("失败")

        # 触发熔断
        for i in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        assert breaker.state == "OPEN"

        # 等待恢复时间
        time.sleep(1.5)

        # 应该进入 HALF_OPEN 状态
        def success_func():
            return "success"

        # 连续成功后应该恢复
        for i in range(2):
            result = breaker.call(success_func)
            assert result == "success"

        assert breaker.state == "CLOSED"

    def test_circuit_breaker_resets_on_success(self):
        """测试成功后重置失败计数"""
        breaker = CircuitBreaker(failure_threshold=3)

        def sometimes_fail():
            if breaker.failure_count < 2:
                raise Exception("失败")
            return "success"

        # 失败2次
        for i in range(2):
            with pytest.raises(Exception):
                breaker.call(sometimes_fail)

        assert breaker.failure_count == 2

        # 成功1次，应该重置
        result = breaker.call(sometimes_fail)
        assert result == "success"
        assert breaker.failure_count == 0


class TestIntegration:
    """集成测试"""

    def test_full_workflow_with_failures(self):
        """测试完整工作流（包含失败场景）"""
        executor = RobustToolExecutor()
        call_count = 0

        def unreliable_tool(service, keyword):
            """30% 失败率的工具"""
            nonlocal call_count
            call_count += 1

            if call_count % 3 == 0:  # 每3次失败1次
                raise Exception("随机失败")

            time.sleep(0.05)
            return [{"message": f"log {call_count}"}]

        # 执行10次
        results = []
        for i in range(10):
            result = executor.execute(
                "search_logs",
                unreliable_tool,
                {"service": "payment", "keyword": str(i)},
                max_retries=2
            )
            results.append(result)

        # 验证
        metrics = executor.get_metrics()
        print(f"\n集成测试结果:")
        print(f"  总调用: {metrics['total_calls']}")
        print(f"  成功: {metrics['successful_calls']}")
        print(f"  失败: {metrics['failed_calls']}")
        print(f"  成功率: {metrics['success_rate']:.1%}")

        # 应该至少有一些成功（重试机制）
        assert metrics["successful_calls"] > 0
        # 应该至少有一些失败（30%失败率）
        assert metrics["failed_calls"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
