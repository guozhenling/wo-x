# Day 10-11 - 错误处理与降级

**预计学习时间**: 2 天，每天 2.5 小时

## 🎯 学习目标

- 掌握超时处理机制
- 实现重试策略
- 理解降级方案
- 构建健壮的错误处理

## 📖 核心概念

### 1. 为什么需要错误处理？

**生产环境的现实**：

```python
# 理想情况
search_logs("payment")  # ✓ 成功返回

# 实际情况
search_logs("payment")  # ✗ 超时、网络错误、数据库挂了...
```

**常见错误**：
- 超时：查询太慢，5 秒没响应
- 网络错误：连接失败
- 数据不可用：数据库挂了
- 参数错误：传错参数
- 限流：调用太频繁

### 2. 错误处理策略

**策略 1：重试（Retry）**

```python
@retry(max_attempts=3, backoff=2)
def search_logs(service):
    # 自动重试 3 次
    # 失败后等待 2 秒再试
    return query_database(service)
```

**策略 2：超时（Timeout）**

```python
@timeout(seconds=5)
def search_logs(service):
    # 超过 5 秒强制返回
    return query_database(service)
```

**策略 3：降级（Fallback）**

```python
def search_logs(service):
    try:
        return query_elasticsearch(service)
    except Exception:
        # 降级：返回缓存数据
        return get_cached_logs(service)
```

**策略 4：熔断（Circuit Breaker）**

```python
# 如果连续失败 5 次，暂停 30 秒
if consecutive_failures >= 5:
    return "服务暂时不可用，请稍后重试"
```

### 3. 降级方案

**完整的降级链**：

```
Level 1: 实时数据（最准确，可能失败）
  ↓ 失败
Level 2: 缓存数据（稍旧，但可靠）
  ↓ 失败
Level 3: 静态数据（通用建议）
  ↓ 失败
Level 4: 人工介入（最后手段）
```

**示例**：

```python
def get_incident_recommendation(description):
    # Level 1: 实时查询 Runbook
    try:
        return search_runbooks(description)
    except TimeoutError:
        logger.warning("Runbook 查询超时，使用缓存")
        
        # Level 2: 缓存的 Runbook
        try:
            return get_cached_runbooks(description)
        except Exception:
            logger.error("缓存也失败，返回通用建议")
            
            # Level 3: 静态建议
            return get_generic_recommendations(description)
```

## 🔍 完整示例

### 实现健壮的工具执行器

```python
# robust_executor.py
"""
健壮的工具执行器 - 包含完整错误处理
"""
import time
import logging
from typing import Any, Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """工具执行错误"""
    pass

class TimeoutError(ToolExecutionError):
    """超时错误"""
    pass

class RetryExhaustedError(ToolExecutionError):
    """重试耗尽"""
    pass

def with_timeout(seconds: int):
    """超时装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"函数超时 ({seconds}s)")
            
            # 设置超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # 取消超时
                return result
            except TimeoutError:
                signal.alarm(0)
                raise
        
        return wrapper
    return decorator

def with_retry(
    max_attempts: int = 3,
    backoff: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """重试装饰器"""
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
                            f"尝试 {attempt}/{max_attempts} 失败: {e}, "
                            f"等待 {wait_time}s 后重试"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"重试 {max_attempts} 次全部失败")
            
            raise RetryExhaustedError(
                f"重试 {max_attempts} 次失败: {last_exception}"
            )
        
        return wrapper
    return decorator

class RobustToolExecutor:
    """
    健壮的工具执行器
    
    特性：
    - 超时保护
    - 自动重试
    - 降级方案
    - 熔断机制
    """
    
    def __init__(self):
        self.failure_count = {}  # 记录失败次数
        self.circuit_breaker = {}  # 熔断状态
        self.cache = {}  # 缓存
    
    def execute_with_fallback(
        self,
        tool_name: str,
        tool_function: Callable,
        arguments: dict,
        timeout_seconds: int = 5,
        max_retries: int = 2
    ) -> Any:
        """
        执行工具（带降级）
        
        流程：
        1. 检查熔断
        2. 尝试执行（带超时和重试）
        3. 失败时降级
        """
        # 1. 检查熔断
        if self._is_circuit_open(tool_name):
            logger.warning(f"{tool_name} 已熔断，使用降级方案")
            return self._fallback(tool_name, arguments)
        
        # 2. 尝试执行
        try:
            result = self._execute_with_protection(
                tool_function,
                arguments,
                timeout_seconds,
                max_retries
            )
            
            # 成功，重置失败计数
            self.failure_count[tool_name] = 0
            
            # 缓存结果
            cache_key = self._get_cache_key(tool_name, arguments)
            self.cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"{tool_name} 执行失败: {e}")
            
            # 记录失败
            self.failure_count[tool_name] = \
                self.failure_count.get(tool_name, 0) + 1
            
            # 触发熔断
            if self.failure_count[tool_name] >= 5:
                self._open_circuit(tool_name)
            
            # 3. 降级
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
        @with_retry(max_attempts=max_retries, backoff=1.0)
        def protected_func():
            return func(**arguments)
        
        return protected_func()
    
    def _is_circuit_open(self, tool_name: str) -> bool:
        """检查熔断器是否打开"""
        if tool_name not in self.circuit_breaker:
            return False
        
        breaker = self.circuit_breaker[tool_name]
        
        # 熔断时间到了，尝试恢复
        if time.time() - breaker['opened_at'] > 30:
            logger.info(f"{tool_name} 熔断恢复，尝试执行")
            del self.circuit_breaker[tool_name]
            self.failure_count[tool_name] = 0
            return False
        
        return True
    
    def _open_circuit(self, tool_name: str):
        """打开熔断器"""
        logger.warning(f"{tool_name} 触发熔断（连续失败 5 次）")
        self.circuit_breaker[tool_name] = {
            "opened_at": time.time()
        }
    
    def _fallback(
        self,
        tool_name: str,
        arguments: dict,
        error: Optional[Exception] = None
    ) -> Any:
        """降级方案"""
        
        # Level 1: 使用缓存
        cache_key = self._get_cache_key(tool_name, arguments)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = time.time() - cached['timestamp']
            if age < 300:  # 5 分钟内的缓存
                logger.info(f"使用缓存数据 (age: {age:.0f}s)")
                return cached['result']
        
        # Level 2: 返回空结果或错误信息
        logger.warning(f"{tool_name} 降级失败，返回空结果")
        return {
            "error": str(error) if error else "工具暂时不可用",
            "fallback": True
        }
    
    def _get_cache_key(self, tool_name: str, arguments: dict) -> str:
        """生成缓存键"""
        import json
        return f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"

# 测试
if __name__ == "__main__":
    import random
    
    executor = RobustToolExecutor()
    
    # 模拟不稳定的工具
    def unstable_tool(service):
        if random.random() < 0.3:  # 30% 失败率
            raise Exception("Random failure")
        time.sleep(0.1)
        return [{"message": f"{service} log"}]
    
    # 测试
    print("测试健壮执行器\n")
    
    for i in range(10):
        print(f"尝试 {i+1}:")
        try:
            result = executor.execute_with_fallback(
                "search_logs",
                unstable_tool,
                {"service": "payment"},
                timeout_seconds=2,
                max_retries=2
            )
            
            if result.get("fallback"):
                print(f"  降级: {result['error']}")
            else:
                print(f"  成功: {len(result)} 条日志")
        except Exception as e:
            print(f"  失败: {e}")
        
        time.sleep(0.5)
```

## 💪 动手练习

### Day 10: 实现错误处理（2.5 小时）

**任务**：
1. 实现 RobustToolExecutor
2. 添加超时、重试、降级
3. 测试各种错误场景

### Day 11: 集成到 Agent（2.5 小时）

**任务**：
1. 替换原有的工具执行
2. 添加监控指标（成功率、平均耗时）
3. 压力测试

## ✅ 完成检查清单

- [ ] 实现了完整的错误处理
- [ ] 测试了超时、重试、降级
- [ ] 集成到 Agent
- [ ] 系统更加健壮

## 🎯 Day 12-13 预告

**端到端集成**

有了错误处理，系统更稳定了。接下来：
- 整合所有模块
- 优化性能
- 准备 v1.0 发布

最后冲刺！🚀
