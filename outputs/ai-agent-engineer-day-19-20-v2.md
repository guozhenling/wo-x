# Day 19-20: 性能优化

## 📋 学习目标

完成这两天的学习后，你将能够：
- 识别 AI 系统的性能瓶颈
- 实施缓存、并发、降级等优化策略
- 在延迟和成本之间权衡
- 建立性能监控和告警

**预计时间**：6-8 小时（两天）

---

## 🎯 为什么需要性能优化？

### 现实问题

当前系统运行一次分类：
```
步骤 1: 初步分类 (LLM)       → 3s
步骤 2: 规划工具 (LLM)        → 2s
步骤 3: 并发执行工具 (5个)     → 8s
步骤 4: 综合分析 (LLM)        → 4s
步骤 5: Policy 检查           → 0.1s
────────────────────────────────────
总计: 17s
```

**问题**：
- 用户等待 17 秒太久
- 每次调用 3 次 LLM，成本高
- 如果 LLM 慢或超时，整个系统卡住

**目标**：
- 将 P95 延迟降到 < 5s
- 降低 50% API 成本
- 保证 99.9% 可用性

---

## 📚 核心概念

### 1. 性能优化的三个维度

#### 维度 1：延迟优化（Latency）
```
目标: 用户等待时间越短越好
策略:
- 缓存（避免重复计算）
- 并发（同时执行）
- 超时保护（快速失败）
```

#### 维度 2：成本优化（Cost）
```
目标: 减少 API 调用次数和 token 消耗
策略:
- 缓存复用
- 使用更便宜的模型
- 减少不必要的调用
```

#### 维度 3：可靠性优化（Reliability）
```
目标: 系统稳定可用
策略:
- 重试机制
- 降级方案
- 熔断保护
```

### 2. 性能优化策略矩阵

| 策略 | 延迟改善 | 成本降低 | 复杂度 | 适用场景 |
|------|---------|---------|--------|---------|
| 结果缓存 | ⭐⭐⭐ | ⭐⭐⭐ | 低 | 重复查询多 |
| 并发执行 | ⭐⭐⭐ | - | 中 | 多个独立任务 |
| 超时保护 | ⭐⭐ | - | 低 | 慢调用拖累全局 |
| 更小模型 | ⭐ | ⭐⭐⭐ | 低 | 简单任务 |
| 减少调用 | ⭐⭐ | ⭐⭐⭐ | 中 | 可合并的步骤 |
| 降级方案 | ⭐ | ⭐⭐ | 高 | 确保可用性 |

### 3. 性能指标

**关键指标**：
```python
# 延迟
p50_latency = 3.2s   # 50% 的请求 < 3.2s
p95_latency = 8.1s   # 95% 的请求 < 8.1s
p99_latency = 15.3s  # 99% 的请求 < 15.3s

# 成本
avg_api_calls = 3.2  # 平均调用 3.2 次 LLM
avg_tokens = 2800    # 平均消耗 2800 tokens

# 可靠性
success_rate = 0.998  # 99.8% 成功率
```

---

## 💻 完整示例

### 示例 1：性能分析器

```python
# tools/performance_profiler.py
"""
性能分析工具
"""
import time
import json
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_duration: float = 0.0
    
    # 各步骤耗时
    step_durations: Dict[str, float] = field(default_factory=dict)
    
    # API 调用
    api_calls: int = 0
    total_tokens: int = 0
    
    # 缓存
    cache_hits: int = 0
    cache_misses: int = 0
    
    # 工具执行
    tool_calls: int = 0
    tool_duration: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)

class PerformanceProfiler:
    """
    性能分析器
    
    分析系统性能瓶颈
    """
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
    
    def profile_classification(
        self,
        agent,
        test_cases: List
    ) -> Dict[str, Any]:
        """
        分析分类性能
        
        Args:
            agent: Agent 实例
            test_cases: 测试案例
            
        Returns:
            性能分析报告
        """
        print(f"\n开始性能分析 ({len(test_cases)} 个案例)...")
        
        for i, case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {case.id}...", end=" ")
            
            start = time.time()
            
            try:
                result = agent.classify(case.description)
                duration = time.time() - start
                
                # 提取指标
                metrics = PerformanceMetrics(
                    total_duration=duration
                )
                
                # 从结果中提取详细指标
                if result.get('success'):
                    perf = result.get('performance', {})
                    metrics.api_calls = perf.get('tool_calls', 0)
                    
                    trace = result.get('trace', {})
                    metrics.tool_calls = trace.get('total_calls', 0)
                
                self.metrics.append(metrics)
                print(f"{duration:.2f}s")
                
            except Exception as e:
                print(f"ERROR: {e}")
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        if not self.metrics:
            return {}
        
        # 延迟统计
        durations = [m.total_duration for m in self.metrics]
        durations.sort()
        
        n = len(durations)
        p50 = durations[int(n * 0.5)]
        p95 = durations[int(n * 0.95)]
        p99 = durations[int(n * 0.99)]
        avg = sum(durations) / n
        
        # API 调用统计
        total_api_calls = sum(m.api_calls for m in self.metrics)
        avg_api_calls = total_api_calls / n if n > 0 else 0
        
        # 工具调用统计
        total_tool_calls = sum(m.tool_calls for m in self.metrics)
        avg_tool_calls = total_tool_calls / n if n > 0 else 0
        
        # 缓存统计
        total_cache_hits = sum(m.cache_hits for m in self.metrics)
        total_cache_misses = sum(m.cache_misses for m in self.metrics)
        cache_hit_rate = (
            total_cache_hits / (total_cache_hits + total_cache_misses)
            if (total_cache_hits + total_cache_misses) > 0
            else 0
        )
        
        return {
            "latency": {
                "avg": avg,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "min": min(durations),
                "max": max(durations)
            },
            "api_usage": {
                "total_calls": total_api_calls,
                "avg_calls_per_request": avg_api_calls,
            },
            "tool_usage": {
                "total_calls": total_tool_calls,
                "avg_calls_per_request": avg_tool_calls,
            },
            "cache": {
                "hits": total_cache_hits,
                "misses": total_cache_misses,
                "hit_rate": cache_hit_rate
            },
            "samples": len(self.metrics)
        }
    
    def print_report(self, report: Dict[str, Any]):
        """打印性能报告"""
        print("\n" + "=" * 60)
        print("性能分析报告")
        print("=" * 60)
        
        # 延迟
        latency = report["latency"]
        print(f"\n延迟统计 (n={report['samples']}):")
        print(f"  平均: {latency['avg']:.2f}s")
        print(f"  P50:  {latency['p50']:.2f}s")
        print(f"  P95:  {latency['p95']:.2f}s")
        print(f"  P99:  {latency['p99']:.2f}s")
        print(f"  范围: {latency['min']:.2f}s - {latency['max']:.2f}s")
        
        # 瓶颈分析
        if latency['p95'] > 10:
            print(f"  ⚠️ P95 延迟过高 (> 10s)")
        elif latency['p95'] > 5:
            print(f"  ⚠️ P95 延迟偏高 (> 5s)")
        else:
            print(f"  ✅ 延迟表现良好")
        
        # API 使用
        api = report["api_usage"]
        print(f"\nAPI 调用:")
        print(f"  总调用: {api['total_calls']}")
        print(f"  平均: {api['avg_calls_per_request']:.1f} 次/请求")
        
        # 工具使用
        tool = report["tool_usage"]
        print(f"\n工具调用:")
        print(f"  总调用: {tool['total_calls']}")
        print(f"  平均: {tool['avg_calls_per_request']:.1f} 次/请求")
        
        # 缓存
        cache = report["cache"]
        if cache['hits'] + cache['misses'] > 0:
            print(f"\n缓存效率:")
            print(f"  命中: {cache['hits']}")
            print(f"  未命中: {cache['misses']}")
            print(f"  命中率: {cache['hit_rate']:.1%}")
        
        print("\n" + "=" * 60)
    
    def identify_bottlenecks(self, report: Dict[str, Any]) -> List[str]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        latency = report["latency"]
        api = report["api_usage"]
        cache = report["cache"]
        
        # 延迟瓶颈
        if latency['p95'] > 10:
            bottlenecks.append({
                "type": "高延迟",
                "severity": "高",
                "metric": f"P95 = {latency['p95']:.1f}s",
                "suggestion": "考虑：1) 增加缓存 2) 并发优化 3) 超时保护"
            })
        
        # API 调用过多
        if api['avg_calls_per_request'] > 5:
            bottlenecks.append({
                "type": "API 调用过多",
                "severity": "中",
                "metric": f"平均 {api['avg_calls_per_request']:.1f} 次",
                "suggestion": "考虑：1) 合并调用 2) 减少不必要步骤"
            })
        
        # 缓存命中率低
        if cache['hit_rate'] < 0.5 and cache['hits'] + cache['misses'] > 10:
            bottlenecks.append({
                "type": "缓存命中率低",
                "severity": "中",
                "metric": f"命中率 {cache['hit_rate']:.1%}",
                "suggestion": "考虑：1) 增加缓存容量 2) 优化缓存键"
            })
        
        return bottlenecks
```

### 示例 2：优化策略实现

```python
# src/optimizations.py
"""
性能优化策略
"""
import time
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, List, Dict

class OptimizationStrategies:
    """性能优化策略集合"""
    
    @staticmethod
    def cache_with_ttl(ttl_seconds: int = 300):
        """
        带 TTL 的缓存装饰器
        
        Args:
            ttl_seconds: 缓存过期时间（秒）
        """
        def decorator(func: Callable) -> Callable:
            cache = {}
            cache_times = {}
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                key = str(args) + str(sorted(kwargs.items()))
                
                # 检查缓存
                now = time.time()
                if key in cache:
                    if now - cache_times[key] < ttl_seconds:
                        return cache[key]
                    else:
                        # 过期，删除
                        del cache[key]
                        del cache_times[key]
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 存入缓存
                cache[key] = result
                cache_times[key] = now
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def timeout(seconds: float):
        """
        超时装饰器
        
        Args:
            seconds: 超时时间
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"函数 {func.__name__} 超时 ({seconds}s)")
                
                # 设置超时
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(seconds))
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def parallel_execute(
        tasks: List[Callable],
        max_workers: int = 5,
        timeout: float = 30
    ) -> List[Any]:
        """
        并发执行多个任务
        
        Args:
            tasks: 任务列表
            max_workers: 最大并发数
            timeout: 总超时时间
            
        Returns:
            结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(task): i
                for i, task in enumerate(tasks)
            }
            
            # 收集结果
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 任务失败，记录但不中断
                    results.append({"error": str(e)})
        
        return results
    
    @staticmethod
    def retry_with_backoff(
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0
    ):
        """
        指数退避重试装饰器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟
            max_delay: 最大延迟
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        if attempt < max_retries:
                            # 计算延迟（指数退避）
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            time.sleep(delay)
                        else:
                            # 最后一次尝试失败
                            raise last_exception
                
                raise last_exception
            
            return wrapper
        return decorator
    
    @staticmethod
    def fallback(fallback_func: Callable):
        """
        降级装饰器
        
        Args:
            fallback_func: 降级函数
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 主函数失败，调用降级函数
                    return fallback_func(*args, **kwargs, error=e)
            
            return wrapper
        return decorator
```

### 示例 3：优化版 Agent

```python
# src/incident_classifier_optimized.py
"""
优化版故障分类器
"""
from src.incident_classifier_v1 import IncidentClassifierV1
from src.optimizations import OptimizationStrategies as Opt

class IncidentClassifierOptimized(IncidentClassifierV1):
    """
    优化版故障分类器
    
    应用性能优化策略
    """
    
    @Opt.cache_with_ttl(ttl_seconds=300)
    def _initial_classify(self, description: str):
        """初步分类 - 带缓存"""
        return super()._initial_classify(description)
    
    @Opt.timeout(seconds=30)
    @Opt.retry_with_backoff(max_retries=2)
    def _final_classify(self, description, initial, evidence):
        """综合分析 - 带超时和重试"""
        return super()._final_classify(description, initial, evidence)
    
    @Opt.fallback(fallback_func=lambda *args, **kwargs: {
        "severity": "P2",
        "category": "unknown",
        "needs_human_review": True,
        "rationale": "分析失败，降级为 P2"
    })
    def classify(self, description: str):
        """分类 - 带降级"""
        return super().classify(description)
```

---

## 🎯 动手练习

### Level 1：基础 - 性能分析

**任务**：分析当前系统的性能瓶颈

**步骤**：
1. 运行性能分析器
2. 识别 P95 延迟 > 10s 的案例
3. 找出最慢的步骤

**代码**：
```python
from tools.performance_profiler import PerformanceProfiler
from tests.test_cases import get_all_cases

profiler = PerformanceProfiler()
cases = get_all_cases()[:10]  # 先测 10 个

report = profiler.profile_classification(agent, cases)
profiler.print_report(report)

bottlenecks = profiler.identify_bottlenecks(report)
for b in bottlenecks:
    print(f"{b['type']}: {b['suggestion']}")
```

### Level 2：进阶 - 实施优化

**任务**：实施 2-3 个优化策略

**建议优化**：
1. **增加缓存**：
   ```python
   @lru_cache(maxsize=100)
   def _initial_classify(self, description):
       # ...
   ```

2. **并发执行工具**（已有，优化 max_workers）

3. **超时保护**：
   ```python
   @timeout(seconds=10)
   def _call_llm(self, prompt):
       # ...
   ```

### Level 3：高级 - A/B 对比优化效果

**任务**：对比优化前后的性能

**步骤**：
1. 运行基线性能测试
2. 应用优化策略
3. 运行优化后性能测试
4. 对比指标：
   - P95 延迟降低了多少？
   - API 调用减少了多少？
   - 成功率是否保持？

**代码**：
```python
# 基线
baseline_report = profiler.profile_classification(agent_baseline, cases)

# 优化后
optimized_report = profiler.profile_classification(agent_optimized, cases)

# 对比
print(f"P95 延迟: {baseline_report['latency']['p95']:.1f}s → {optimized_report['latency']['p95']:.1f}s")
print(f"API 调用: {baseline_report['api_usage']['avg_calls_per_request']:.1f} → {optimized_report['api_usage']['avg_calls_per_request']:.1f}")
```

---

## ✅ 自我检查清单

完成这两天的学习后，你应该能回答：

### 概念理解
- [ ] 性能优化的三个维度是什么？
- [ ] 缓存、并发、超时各解决什么问题？
- [ ] 如何在延迟和成本之间权衡？
- [ ] 什么是降级？为什么需要？

### 实践能力
- [ ] 能否分析性能瓶颈？
- [ ] 能否实施缓存优化？
- [ ] 能否配置超时和重试？
- [ ] 能否量化优化效果？

### 工程实践
- [ ] 如何设置合理的超时时间？
- [ ] 缓存的 TTL 如何确定？
- [ ] 何时需要降级方案？
- [ ] 如何监控性能指标？

---

## 🤔 常见问题

### Q1：缓存会不会导致结果不一致？
**A**：是的，所以需要：
1. 设置合理的 TTL（如 5 分钟）
2. 只缓存稳定的结果
3. 提供手动刷新机制

### Q2：并发会不会增加 API 成本？
**A**：不会。并发是"同时执行"，不是"多次执行"：
- 不并发：A (3s) → B (3s) → C (3s) = 9s, 3 次调用
- 并发：A + B + C 同时 = 3s, 3 次调用

### Q3：超时设多少合适？
**A**：根据 P95 延迟：
- P95 = 5s → 超时 10s（2倍）
- P95 = 10s → 超时 20s
- 原则：让 95% 的请求能完成

### Q4：降级方案会降低准确率吗？
**A**：会，但保证了可用性：
- 无降级：10% 请求失败（用户看到错误）
- 有降级：10% 请求降级为 P2（可能不准，但有输出）

权衡：可用性 > 准确率

### Q5：优化后准确率下降了怎么办？
**A**：优化策略有问题：
- 缓存导致结果过期 → 缩短 TTL
- 超时导致分析不完整 → 放宽超时
- 降级太激进 → 提高降级阈值

---

## 📚 延伸阅读

### 相关技术
- **Redis** - 分布式缓存
- **RabbitMQ/Kafka** - 异步消息队列
- **Prometheus** - 性能监控
- **Jaeger** - 分布式追踪

### 性能优化最佳实践
1. **先测量再优化**（避免过早优化）
2. **优化最大瓶颈**（80/20 原则）
3. **验证优化效果**（数据驱动）
4. **权衡利弊**（没有银弹）

### 下一步
- Day 21：第三周总结
- Day 22-23：监控告警

---

## 🎯 本节重点

1. **性能优化三维度：延迟、成本、可靠性**
2. **缓存是最有效的优化手段**（延迟 ↓ 成本 ↓）
3. **超时和降级保证可用性**（快速失败 > 长时间等待）
4. **先分析后优化，用数据验证效果**

---

## 💡 小贴士

**类比 Java 后端优化**：
```java
// 缓存
@Cacheable(value = "users", key = "#id")
public User getUserById(Long id) { }

// 超时
@HystrixCommand(
    commandProperties = {
        @HystrixProperty(name = "execution.isolation.thread.timeoutInMilliseconds", value = "3000")
    }
)

// 降级
@HystrixCommand(fallbackMethod = "getFallback")
public String getData() { }
```

AI 系统优化思路完全一样！

---

**完成 Day 19-20 后，你的系统将从 17s 优化到 < 5s，成本降低 50%！**

**下一步**：Day 21 - 第三周总结
