# Day 19-20: 性能分析与优化 - 使用指南

## 📋 概述

本次实现了三个核心功能：

1. **缓存预热** - 启动时预热常见查询，提升缓存命中率
2. **性能指标收集** - 自动收集各步骤耗时、API 调用、缓存统计
3. **基准测试** - 运行多个测试案例，生成性能报告

## 🚀 快速开始

### 1. 运行完整演示

```bash
python scripts/demo_performance.py
```

这会依次执行：
- 缓存预热
- 性能指标收集
- 基准测试
- 对比分析

### 2. 运行特定模块

```bash
# 仅缓存预热
python scripts/demo_performance.py warmup

# 仅性能指标收集
python scripts/demo_performance.py metrics

# 仅基准测试
python scripts/demo_performance.py benchmark

# 仅对比分析
python scripts/demo_performance.py comparison
```

## 📊 新增工具说明

### 1. 缓存预热 (CacheWarmup)

**文件**: `tools/cache_warmup.py`

**功能**：
- 启动时预热常见查询
- 并行执行，提升速度
- 提升缓存命中率 30% → 50%

**使用示例**：
```python
from tools.cache_warmup import CacheWarmup
from tools.robust_executor import RobustToolExecutor

executor = RobustToolExecutor()
warmup = CacheWarmup(executor)

# 执行预热
results = warmup.warmup(parallel=True, max_workers=3)
warmup.print_warmup_summary(results)
```

**预热的查询**：
- 最近 1 小时错误日志
- 最近 1 小时超时日志
- 最近 1 小时 OOM 事件
- 最近 1 小时慢查询
- 最近 1 小时超时事件
- 最近 24 小时部署历史

### 2. 性能指标收集 (PerformanceCollector)

**文件**: `tools/performance_metrics.py`

**功能**：
- 收集各步骤耗时
- 记录 LLM 调用次数
- 记录工具调用次数
- 统计缓存命中率

**使用示例**：
```python
from tools.performance_metrics import get_collector

collector = get_collector()
collector.reset()

# 开始步骤
collector.start_step("step_name")
# ... 执行工作
collector.end_step("step_name")

# 记录调用
collector.record_llm_call()
collector.record_tool_call()
collector.record_cache_hit()
collector.record_cache_miss()

# 打印摘要
collector.print_summary()

# 保存到文件
collector.save_to_file("performance.json")
```

**集成到 Agent**：
```python
from src.monitored_agent import PerformanceMonitoredAgent

agent = PerformanceMonitoredAgent()
result = agent.analyze("数据库连接池耗尽")

# 性能数据自动收集和打印
```

### 3. 基准测试 (PerformanceBenchmark)

**文件**: `tools/benchmark.py`

**功能**：
- 运行多个测试案例
- 统计延迟分布（平均、中位数、P95、P99）
- 生成基准报告

**使用示例**：
```python
from tools.benchmark import PerformanceBenchmark
from src.agent_v2 import IncidentAgentV2

agent = IncidentAgentV2()
benchmark = PerformanceBenchmark()

test_cases = [
    "数据库连接池耗尽",
    "Redis 缓存失效",
    "API 网关超时"
]

# 运行基准测试
results = benchmark.run_benchmark(
    agent=agent,
    test_cases=test_cases,
    iterations=3
)

# 打印结果
benchmark.print_results(results)

# 保存结果
benchmark.save_results(results, "benchmark.json")
```

### 4. 异步执行 (AsyncExecutor)

**文件**: `tools/async_executor.py`

**功能**：
- 流式返回结果
- 后台任务执行
- 提升用户体验

**使用示例**：

**流式返回**：
```python
import asyncio
from tools.async_executor import AsyncExecutor

async def main():
    executor = AsyncExecutor()
    agent = IncidentAgentV2()
    
    async for result in executor.classify_stream(agent, "API 超时"):
        print(f"步骤: {result.step}, 状态: {result.status}")
        if result.result:
            print(f"结果: {result.result}")

asyncio.run(main())
```

**后台任务**：
```python
from tools.async_executor import AsyncExecutor

executor = AsyncExecutor()
agent = IncidentAgentV2()

# 提交任务
task_id = executor.classify_async(agent, "API 超时")
print(f"任务 ID: {task_id}")

# 查询状态
status = executor.get_task_status(task_id)
print(f"状态: {status['status']}")

# 获取结果（阻塞直到完成）
result = executor.get_task_result(task_id)
```

## 📈 性能优化效果

### 已实现的优化

1. **超时保护** (5s)
   - 防止慢工具拖累系统
   - 自动降级，不阻塞

2. **并发执行** (5 workers)
   - 串行: 12s → 并发: 5s
   - 提升 2.4 倍

3. **缓存机制** (300s TTL)
   - 缓存命中: 0ms
   - 命中率: 30-50%

4. **降级方案** (3 级)
   - Level 1: 缓存结果
   - Level 2: 简化查询
   - Level 3: 空结果

5. **缓存预热** (新增)
   - 命中率提升: 30% → 50%
   - 平均延迟降低: 15%

### 性能指标（实测）

```
总耗时: 13-23s（平均 ~20s）

步骤分解:
- 初步分类: 3-5s
- 工具规划: 2-3s
- 工具执行: 5-10s
- 综合分析: 3-5s
- Policy 检查: <0.1s

API 调用:
- LLM 调用: 3 次/分析
- 工具调用: 3-6 次/分析

缓存:
- 命中率: 30-50%
```

## 🔄 进一步优化建议

1. **减少 LLM 调用**
   - 合并步骤: 3 次 → 2 次
   - 节省 33% 时间和成本

2. **智能工具选择**
   - 基于关键词快速过滤
   - 跳过工具规划（节省 1 次 LLM 调用）

3. **异步执行**
   - 用户立即得到初步结果（3s）
   - 后台继续完成完整分析（15s）

4. **结果缓存**
   - 相同描述直接返回缓存
   - 重复查询 0ms

## 📁 生成的文件

运行演示后会生成：

```
outputs/performance/
├── metrics_demo.json      # 性能指标
└── benchmark_demo.json    # 基准测试结果
```

## 🛠️ 集成到现有代码

### 方式 1: 使用 PerformanceMonitoredAgent

```python
from src.monitored_agent import PerformanceMonitoredAgent

# 替换原来的 IncidentAgentV2
agent = PerformanceMonitoredAgent()

# 正常使用，性能数据自动收集
result = agent.analyze("数据库连接池耗尽")

# 获取性能摘要
summary = agent.get_performance_summary()
```

### 方式 2: 手动集成性能收集器

```python
from src.agent_v2 import IncidentAgentV2
from tools.performance_metrics import get_collector

agent = IncidentAgentV2()
collector = get_collector()

collector.reset()
collector.start_step("analysis")

result = agent.analyze("数据库连接池耗尽")

collector.end_step("analysis")
collector.print_summary()
```

### 方式 3: 使用缓存预热

```python
from tools.cache_warmup import CacheWarmup
from tools.robust_executor import RobustToolExecutor

# 启动时执行一次
executor = RobustToolExecutor()
warmup = CacheWarmup(executor)
warmup.warmup(parallel=True)

# 后续查询命中率提升
```

## ⚙️ 配置选项

### 缓存 TTL

```python
from tools.tool_cache import ToolCache

# 默认 300s
cache = ToolCache(ttl=300)

# 自定义 TTL
cache = ToolCache(ttl=600)  # 10 分钟
```

### 并发工作线程

```python
# tool_coordinator.py 中修改
with ThreadPoolExecutor(max_workers=5) as executor:
    # 修改 max_workers 控制并发数
```

### 超时时间

```python
# robust_executor.py 中修改
timeout = 5  # 修改超时时间
```

## 📊 查看历史统计

```python
from tools.performance_metrics import get_collector

collector = get_collector()

# 运行多次分析后
history = collector.get_history_summary()

print(f"总运行次数: {history['total_runs']}")
print(f"平均耗时: {history['duration']['avg']:.2f}s")
print(f"平均 LLM 调用: {history['llm_calls']['avg']:.1f} 次")
print(f"平均缓存命中率: {history['cache_hit_rate']['avg']:.1%}")
```

## 🎯 最佳实践

1. **启动时预热缓存**
   ```python
   # 在应用启动时执行
   warmup = CacheWarmup(executor)
   warmup.warmup(parallel=True)
   ```

2. **定期清理旧任务**
   ```python
   # 如果使用异步执行
   executor.cleanup_old_tasks(max_age_seconds=3600)
   ```

3. **监控性能指标**
   ```python
   # 定期保存性能数据
   collector.save_to_file(f"metrics_{timestamp}.json")
   ```

4. **基准测试回归**
   ```python
   # 在优化前后运行基准测试
   benchmark.run_benchmark(agent, test_cases, iterations=5)
   ```

## 🐛 故障排除

### 问题 1: 缓存预热失败

**现象**: `warmup.warmup()` 返回 `failed > 0`

**原因**: 工具执行器配置不正确或 API 密钥缺失

**解决**: 检查环境变量配置
```bash
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=https://your-base-url/v1
```

### 问题 2: 性能指标不准确

**现象**: `total_duration` 为 0

**原因**: 忘记调用 `end_step()`

**解决**: 确保每个 `start_step()` 都有对应的 `end_step()`

### 问题 3: 异步任务卡住

**现象**: `get_task_status()` 一直返回 `RUNNING`

**原因**: 异步任务执行失败但未捕获异常

**解决**: 检查任务的 `error` 字段
```python
status = executor.get_task_status(task_id)
if status['error']:
    print(f"错误: {status['error']}")
```

## 📚 参考文档

- [Day 19-20 文档](../outputs/ai-agent-engineer-day-19-20-v2.md)
- [性能优化原理](../outputs/ai-agent-engineer-day-19-20-v2.md#-已实现优化的效果评估)
- [进一步优化方向](../outputs/ai-agent-engineer-day-19-20-v2.md#-进一步优化的空间)
