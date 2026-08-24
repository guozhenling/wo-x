"""
健壮的工具执行器 - 完整错误处理与降级

功能：
- 超时保护
- 自动重试
- 降级方案
- 熔断机制
- 缓存策略
"""
import time
import signal
import logging
from typing import Any, Callable, Optional, Dict
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ==================== 自定义异常 ====================

class ToolExecutionError(Exception):
    """工具执行错误基类"""
    pass


class TimeoutError(ToolExecutionError):
    """超时错误"""
    pass


class RetryExhaustedError(ToolExecutionError):
    """重试耗尽"""
    pass


class CircuitBreakerOpenError(ToolExecutionError):
    """熔断器打开"""
    pass


# ==================== 装饰器 ====================

def with_timeout(seconds: int):
    """
    超时装饰器（线程安全版本）

    使用 threading.Timer 实现，支持多线程环境
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import threading

            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                # 超时了
                logger.error(f"{func.__name__} 超时 ({seconds}s)")
                raise TimeoutError(f"操作超时 ({seconds}s)")

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    backoff: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        backoff: 退避时间（秒），每次失败后等待 backoff * attempt
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        wait_time = backoff * attempt
                        logger.warning(
                            f"{func.__name__} 尝试 {attempt}/{max_attempts} 失败: {e}, "
                            f"等待 {wait_time:.1f}s 后重试"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {max_attempts} 次全部失败: {last_exception}"
                        )

            raise RetryExhaustedError(
                f"{func.__name__} 重试 {max_attempts} 次失败: {last_exception}"
            )

        return wrapper
    return decorator


# ==================== 熔断器 ====================

class CircuitBreaker:
    """
    熔断器

    状态机：
    - CLOSED（关闭）：正常执行
    - OPEN（打开）：拒绝执行，直接失败
    - HALF_OPEN（半开）：尝试恢复，允许少量请求

    规则：
    - 连续失败 N 次 → OPEN
    - OPEN 持续 T 秒 → HALF_OPEN
    - HALF_OPEN 成功 → CLOSED
    - HALF_OPEN 失败 → OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_attempts: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts

        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.state = "CLOSED"

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数（带熔断保护）"""

        # 1. 检查熔断状态
        if self.state == "OPEN":
            # 检查是否可以恢复
            if time.time() - self.opened_at > self.recovery_timeout:
                logger.info("熔断器进入 HALF_OPEN 状态，尝试恢复")
                self.state = "HALF_OPEN"
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"熔断器已打开，剩余 {self.recovery_timeout - (time.time() - self.opened_at):.0f}s"
                )

        # 2. 执行函数
        try:
            result = func(*args, **kwargs)

            # 3. 成功处理
            if self.state == "HALF_OPEN":
                self.success_count += 1
                if self.success_count >= self.half_open_attempts:
                    logger.info("熔断器恢复，进入 CLOSED 状态")
                    self.state = "CLOSED"
                    self.failure_count = 0
            elif self.state == "CLOSED":
                # 重置失败计数
                self.failure_count = 0

            return result

        except Exception as e:
            # 4. 失败处理
            self.failure_count += 1

            if self.state == "HALF_OPEN":
                logger.warning("熔断器恢复失败，重新进入 OPEN 状态")
                self.state = "OPEN"
                self.opened_at = time.time()
            elif self.failure_count >= self.failure_threshold:
                logger.error(f"连续失败 {self.failure_count} 次，触发熔断")
                self.state = "OPEN"
                self.opened_at = time.time()

            raise e

    def __str__(self):
        if self.state == "OPEN":
            age = time.time() - self.opened_at
            return f"CircuitBreaker(OPEN, age={age:.0f}s, failures={self.failure_count})"
        return f"CircuitBreaker({self.state}, failures={self.failure_count})"


# ==================== 健壮的工具执行器 ====================

class RobustToolExecutor:
    """
    健壮的工具执行器

    特性：
    1. 超时保护 - 5秒超时
    2. 自动重试 - 最多3次，指数退避
    3. 降级方案 - 缓存 → 空结果
    4. 熔断机制 - 连续失败5次触发
    5. 性能监控 - 成功率、平均耗时
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.cache: Dict[str, Dict[str, Any]] = {}

        # 监控指标
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "cache_hits": 0,
            "total_time": 0.0
        }

    def execute(
        self,
        tool_name: str,
        tool_function: Callable,
        arguments: dict,
        timeout_seconds: int = 5,
        max_retries: int = 3,
        enable_cache: bool = True
    ) -> Any:
        """
        执行工具（带完整保护）

        Args:
            tool_name: 工具名称
            tool_function: 工具函数
            arguments: 工具参数
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数
            enable_cache: 是否启用缓存

        Returns:
            工具执行结果

        Raises:
            ToolExecutionError: 执行失败
        """
        start_time = time.time()
        self.metrics["total_calls"] += 1

        # 1. 检查缓存
        if enable_cache:
            cached = self._get_from_cache(tool_name, arguments)
            if cached is not None:
                self.metrics["cache_hits"] += 1
                self.metrics["successful_calls"] += 1
                logger.info(f"✓ {tool_name} 缓存命中")
                return cached

        # 2. 获取熔断器
        breaker = self._get_circuit_breaker(tool_name)

        # 3. 尝试执行
        try:
            result = breaker.call(
                self._execute_with_protection,
                tool_function,
                arguments,
                timeout_seconds,
                max_retries
            )

            # 4. 成功：缓存结果
            if enable_cache:
                self._save_to_cache(tool_name, arguments, result)

            self.metrics["successful_calls"] += 1
            elapsed = time.time() - start_time
            self.metrics["total_time"] += elapsed

            logger.info(f"✓ {tool_name} 执行成功 ({elapsed:.2f}s)")
            return result

        except (TimeoutError, RetryExhaustedError, CircuitBreakerOpenError) as e:
            # 5. 失败：降级
            self.metrics["failed_calls"] += 1
            logger.error(f"✗ {tool_name} 执行失败: {e}")

            return self._fallback(tool_name, arguments, error=e)

    def _execute_with_protection(
        self,
        func: Callable,
        arguments: dict,
        timeout_seconds: int,
        max_retries: int
    ) -> Any:
        """执行工具（带超时和重试）"""

        @with_timeout(timeout_seconds)
        @with_retry(
            max_attempts=max_retries,
            backoff=1.0,
            exceptions=(Exception,)  # 所有异常都重试
        )
        def protected_func():
            return func(**arguments)

        return protected_func()

    def _get_circuit_breaker(self, tool_name: str) -> CircuitBreaker:
        """获取工具的熔断器"""
        if tool_name not in self.circuit_breakers:
            self.circuit_breakers[tool_name] = CircuitBreaker(
                failure_threshold=5,    # 连续失败5次触发
                recovery_timeout=30,    # 30秒后尝试恢复
                half_open_attempts=3    # 半开状态允许3次尝试
            )
        return self.circuit_breakers[tool_name]

    def _get_cache_key(self, tool_name: str, arguments: dict) -> str:
        """生成缓存键"""
        import json
        import hashlib

        sorted_args = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        content = f"{tool_name}:{sorted_args}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(
        self,
        tool_name: str,
        arguments: dict
    ) -> Optional[Any]:
        """从缓存获取结果"""
        cache_key = self._get_cache_key(tool_name, arguments)

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = time.time() - cached['timestamp']

            # 缓存5分钟内有效
            if age < 300:
                return cached['result']
            else:
                # 过期，但不删除（保留用于降级）
                return None

        return None

    def _save_to_cache(
        self,
        tool_name: str,
        arguments: dict,
        result: Any
    ):
        """保存结果到缓存"""
        cache_key = self._get_cache_key(tool_name, arguments)
        self.cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }

    def _fallback(
        self,
        tool_name: str,
        arguments: dict,
        error: Exception
    ) -> Any:
        """
        降级方案

        Level 1: 使用过期缓存（如果有）
        Level 2: 返回空结果标记
        """
        # Level 1: 尝试使用过期缓存
        cache_key = self._get_cache_key(tool_name, arguments)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = time.time() - cached['timestamp']
            logger.warning(f"使用过期缓存 (age={age:.0f}s)")

            # 如果缓存结果是字典，添加降级标记
            if isinstance(cached['result'], dict):
                return {
                    **cached['result'],
                    "_fallback": "stale_cache",
                    "_cache_age": age
                }
            # 如果是列表或其他类型，包装成字典
            else:
                return {
                    "data": cached['result'],
                    "_fallback": "stale_cache",
                    "_cache_age": age,
                    "_original_result": cached['result']
                }

        # Level 2: 返回空结果
        logger.warning(f"{tool_name} 降级失败，返回空结果")
        return {
            "error": str(error),
            "fallback": True,
            "tool": tool_name,
            "data": []  # 空数据，避免后续代码出错
        }

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        total = self.metrics["total_calls"]
        if total == 0:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "cache_hit_rate": 0.0,
                "avg_time": 0.0
            }

        return {
            "total_calls": total,
            "successful_calls": self.metrics["successful_calls"],
            "failed_calls": self.metrics["failed_calls"],
            "cache_hits": self.metrics["cache_hits"],
            "success_rate": self.metrics["successful_calls"] / total,
            "cache_hit_rate": self.metrics["cache_hits"] / total,
            "avg_time": self.metrics["total_time"] / total if total > 0 else 0.0
        }

    def reset_metrics(self):
        """重置指标"""
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "cache_hits": 0,
            "total_time": 0.0
        }

    def __str__(self):
        metrics = self.get_metrics()
        return (
            f"RobustToolExecutor(\n"
            f"  calls={metrics['total_calls']}, "
            f"  success_rate={metrics['success_rate']:.1%}, "
            f"  cache_hit_rate={metrics['cache_hit_rate']:.1%}, "
            f"  avg_time={metrics['avg_time']:.3f}s\n"
            f")"
        )


# ==================== 测试 ====================

if __name__ == "__main__":
    import random

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 模拟不稳定的工具
    def unstable_tool(service: str, keyword: str):
        """模拟不稳定的日志搜索"""
        failure_rate = 0.3  # 30% 失败率

        if random.random() < failure_rate:
            raise Exception("随机失败")

        time.sleep(0.1)  # 模拟查询耗时
        return [
            {"timestamp": "2026-08-20 16:45:00", "level": "ERROR", "message": f"{service} error 1"},
            {"timestamp": "2026-08-20 16:46:00", "level": "ERROR", "message": f"{service} error 2"}
        ]

    # 测试
    print("=" * 60)
    print("测试健壮的工具执行器")
    print("=" * 60)

    executor = RobustToolExecutor()

    # 测试1: 正常执行 + 缓存
    print("\n测试1: 正常执行 + 缓存")
    print("-" * 60)

    for i in range(5):
        print(f"\n尝试 {i+1}:")
        result = executor.execute(
            "search_logs",
            unstable_tool,
            {"service": "payment", "keyword": "ERROR"},
            timeout_seconds=2,
            max_retries=3
        )

        if isinstance(result, dict) and result.get("fallback"):
            print(f"  ⚠ 降级: {result['error']}")
        else:
            if isinstance(result, list):
                print(f"  ✓ 成功: {len(result)} 条日志")
            else:
                print(f"  ✓ 成功: {result}")

    # 测试2: 熔断机制
    print("\n\n测试2: 熔断机制")
    print("-" * 60)

    def always_fail(**kwargs):
        raise Exception("总是失败")

    for i in range(8):
        print(f"\n尝试 {i+1}:")
        result = executor.execute(
            "failing_tool",
            always_fail,
            {"test": "data"},
            timeout_seconds=1,
            max_retries=1  # 减少重试，快速触发熔断
        )
        if isinstance(result, dict):
            if result.get("fallback"):
                print(f"  ⚠ 降级: {result.get('error', 'unknown')}")
            else:
                print(f"  结果: {result}")

        time.sleep(0.5)

    # 输出指标
    print("\n" + "=" * 60)
    print("性能指标")
    print("=" * 60)
    print(executor)

    metrics = executor.get_metrics()
    print(f"\n详细指标:")
    print(f"  总调用: {metrics['total_calls']}")
    print(f"  成功: {metrics['successful_calls']}")
    print(f"  失败: {metrics['failed_calls']}")
    print(f"  缓存命中: {metrics['cache_hits']}")
    print(f"  成功率: {metrics['success_rate']:.1%}")
    print(f"  缓存命中率: {metrics['cache_hit_rate']:.1%}")
    print(f"  平均耗时: {metrics['avg_time']:.3f}s")
