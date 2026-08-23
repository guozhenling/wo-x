# Day 6 重构说明

## 📋 改动概览

### 验证结果

✅ **src/trace_manager.py 已经完全符合 v2 规范！**

现有的 `trace_manager.py` 已经包含：
- ✅ TraceManager 类
- ✅ 完整的调用记录（工具名、参数、结果、耗时）
- ✅ 调用次数限制（最多 2 次）
- ✅ 保存到文件（JSON 格式）
- ✅ 成功/失败状态记录
- ✅ 与 Agent 完美集成

**无需重构！** 只需要：
1. 创建使用示例
2. 说明如何分析轨迹

### 新增文件

1. **examples/trace_demo.py** - 轨迹使用示例
2. **REFACTOR_DAY6.md** - Day 6 说明文档

## 🔍 TraceManager 功能回顾

### 1. 完整的调用记录

```python
from src.trace_manager import TraceManager

trace = TraceManager()

# 开始轨迹
trace_id = trace.start_trace("支付接口报错")

# 记录工具调用
trace.record_tool_call(
    tool_name="search_logs",
    tool_input={"service": "payment"},
    tool_output=[{"message": "error 1"}, {"message": "error 2"}],
    success=True
)

# 结束轨迹
trace_file = trace.finish_trace(
    final_answer={"severity": "P0", "category": "availability"},
    status="success"
)

print(f"轨迹已保存: {trace_file}")
```

### 2. 调用次数限制

```python
# 检查是否可以调用
if trace.can_call_tool():
    # 执行工具
    result = execute_tool(...)
    trace.record_tool_call(...)
else:
    print("调用次数已达上限（2次）")
```

### 3. 保存到文件

轨迹文件格式（JSON）：

```json
{
  "trace_id": "trace_abc123",
  "timestamp": "2024-01-20T10:30:00",
  "user_input": "支付接口报错",
  "tool_calls": [
    {
      "timestamp": "2024-01-20T10:30:01",
      "tool_name": "search_logs",
      "tool_input": {"service": "payment"},
      "tool_output": [...],
      "success": true
    },
    {
      "timestamp": "2024-01-20T10:30:02",
      "tool_name": "search_runbooks",
      "tool_input": {"description": "payment 5xx"},
      "tool_output": [...],
      "success": true
    }
  ],
  "final_answer": {
    "severity": "P0",
    "category": "availability",
    "rationale": "..."
  },
  "status": "success",
  "total_tool_calls": 2
}
```

## 🧪 如何使用

### 在 Agent 中使用（已集成）

```python
# src/agent.py 中已经集成
class IncidentAgent:
    def __init__(self):
        self.trace = TraceManager()  # 已经在用
    
    def analyze(self, description):
        # 开始轨迹
        self.trace.start_trace(description)
        
        # ... 工具调用过程中自动记录 ...
        
        # 结束轨迹
        trace_file = self.trace.finish_trace(
            final_answer=classification,
            status="success"
        )
        
        return {"trace_file": trace_file, ...}
```

### 分析轨迹文件

```python
import json

# 读取轨迹
with open("traces/trace_abc123.json") as f:
    trace = json.load(f)

# 分析
print(f"用户问题: {trace['user_input']}")
print(f"调用次数: {trace['total_tool_calls']}")

for call in trace['tool_calls']:
    print(f"  - {call['tool_name']}: {call['success']}")

print(f"最终判断: {trace['final_answer']['severity']}")
```

## 📊 轨迹的作用

### 1. 审计（Audit）

**场景**：Agent 判断错了

```
问题: "为什么支付故障被判为 P2？"

查看轨迹:
- 调用了 search_logs → 只返回 3 条日志
- 没有调用 search_runbooks
- LLM 基于不完整信息判断

原因: 日志查询参数不对，应该查 ERROR 级别
```

### 2. 调试（Debug）

**场景**：Agent 总是超限

```
问题: "为什么总提示调用次数超限？"

查看轨迹:
- Round 1: search_logs
- Round 2: search_logs (重复查询)
- Round 3: 超限

原因: LLM 重复调用相同工具，需要优化 prompt
```

### 3. 性能分析

```python
# 分析所有轨迹
import glob
import json

total_calls = 0
avg_time = 0

for trace_file in glob.glob("traces/*.json"):
    with open(trace_file) as f:
        trace = json.load(f)
        total_calls += trace['total_tool_calls']

print(f"平均调用次数: {total_calls / len(files)}")
```

### 4. 成本控制

```python
# 估算成本
def estimate_cost(trace):
    cost = 0
    
    # 每次 LLM 调用约 0.01 元
    llm_calls = len(trace['tool_calls']) + 1  # +1 最终回复
    cost += llm_calls * 0.01
    
    # 工具调用成本（如果有）
    cost += trace['total_tool_calls'] * 0.001
    
    return cost
```

## 📚 对应学习文档

参考 `outputs/ai-agent-engineer-day-6-v2.md`：

- **核心概念 1**：为什么需要轨迹
- **核心概念 2**：轨迹记录什么
- **核心概念 3**：调用次数限制
- **完整示例**：参考 src/trace_manager.py

## ✅ Day 6 完成标志

- [x] 验证 trace_manager.py 符合 v2 规范 ✅
- [x] TraceManager 与 Agent 完美集成 ✅
- [x] 调用次数限制正常工作 ✅
- [x] 能保存和读取轨迹文件 ✅
- [x] 创建使用示例和说明 ✅

## 🎯 Day 6 的关键学习点

### 1. 轨迹是 Agent 的"黑匣子"

就像飞机的黑匣子：
- ✅ 记录所有操作
- ✅ 出问题时能回溯
- ✅ 用于事后分析

### 2. 调用次数限制很重要

防止：
- ❌ 无限循环（LLM 一直调用工具）
- ❌ 成本失控（每次调用都要钱）
- ❌ 超时（用户等不及）

### 3. 轨迹用途广泛

- 审计：回答"为什么这么判断"
- 调试：找出 Agent 的问题
- 优化：分析性能瓶颈
- 成本：控制 API 开销

### 4. 结构化存储

JSON 格式：
- ✅ 易读
- ✅ 易解析
- ✅ 易分析

## 🔗 与其他 Day 的关系

- **Day 3-4**: Agent 调用工具
- **Day 6**: TraceManager 记录调用
- **集成**: Agent 自动记录所有操作到轨迹

```python
# Agent 中
self.trace.start_trace(description)           # 开始
self.trace.record_tool_call(...)              # 记录每次调用
trace_file = self.trace.finish_trace(...)     # 结束并保存
```

## 🧪 如何验证

### 运行 Agent 并查看轨迹

```bash
# 1. 运行 Agent
python src/agent.py

# 2. 查看生成的轨迹文件
ls traces/

# 3. 查看轨迹内容
cat traces/trace_*.json | jq .

# 4. 验证内容
# - 是否记录了所有工具调用？
# - 调用次数是否正确？
# - 是否有完整的输入输出？
```

### 测试调用次数限制

```python
from src.trace_manager import TraceManager

trace = TraceManager()
trace.start_trace("测试")

# 第 1 次
assert trace.can_call_tool() == True
trace.record_tool_call("search_logs", {}, [], True)

# 第 2 次
assert trace.can_call_tool() == True
trace.record_tool_call("search_logs", {}, [], True)

# 第 3 次（应该被拒绝）
assert trace.can_call_tool() == False
print("✓ 调用次数限制工作正常")
```

## 📝 Git 提交

```bash
# 添加文件
git add REFACTOR_DAY6.md

# 提交
git commit -m "Refactor Day 6: 验证 trace_manager 符合 v2 规范

改动：
- 验证 src/trace_manager.py 完全符合 Day 6 v2 要求
- 无需修改，已经很完善
- 创建 Day 6 说明文档

TraceManager 特性（已有）：
- 完整的调用记录
- 调用次数限制（最多 2 次）
- 保存到 JSON 文件
- 成功/失败状态记录
- 与 Agent 完美集成

用途：
- 审计：回溯 Agent 决策
- 调试：找出问题根因
- 性能分析：优化瓶颈
- 成本控制：统计开销

符合 Day 6 v2 规范

相关文档：outputs/ai-agent-engineer-day-6-v2.md
"
```

## 🎯 下一步：Day 7

Day 7 是第一周总结：
- 整合所有模块（Day 1-6）
- 创建完整的端到端示例
- 第一周作业和测试清单
- 准备进入第二周

最后冲刺！🚀
