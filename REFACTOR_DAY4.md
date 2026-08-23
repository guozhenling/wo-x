# Day 4 重构说明

## 📋 改动概览

### 新增文件

1. **src/agent.py** - 完整的 Agent 实现
   - 实现 Tool-Calling Loop
   - 整合 Day 1-3 所有功能
   - 支持多轮对话
   - 完整的轨迹记录

2. **tests/test_agent.py** - Agent 测试
   - 测试工具调用
   - 测试 Policy 集成
   - 测试轨迹记录

## 🎯 Day 4 的核心：Tool-Calling Loop

### 什么是 Tool-Calling Loop？

**传统方式**（Day 1-3）：
```
用户问题 → LLM 回答
```

**Tool-Calling Loop**（Day 4）：
```
用户问题
  ↓
[Round 1] LLM 分析: "我需要查日志"
  ↓
  调用 search_logs(service="payment")
  ↓
  返回日志: [35 条 ERROR]
  ↓
[Round 2] LLM 基于日志分析: "根据日志判断为 P0..."
  ↓
最终结果
```

### 消息格式

完整的对话历史：

```python
messages = [
    # 1. System prompt
    {"role": "system", "content": "你是故障分析专家..."},
    
    # 2. 用户问题
    {"role": "user", "content": "支付接口报错"},
    
    # 3. Assistant 请求调用工具
    {
        "role": "assistant",
        "content": null,
        "tool_calls": [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "search_logs",
                "arguments": '{"service": "payment"}'
            }
        }]
    },
    
    # 4. 工具返回结果
    {
        "role": "tool",
        "tool_call_id": "call_123",
        "content": '[{"timestamp": "...", "message": "..."}]'
    },
    
    # 5. Assistant 的最终回复
    {
        "role": "assistant",
        "content": '{"severity": "P0", "category": "availability", ...}'
    }
]
```

## 🔄 整合 Day 1-3

### Day 1: Structured Output

```python
# Agent 返回结构化的 IncidentResult
final_classification = json.loads(message.content)
# → {"severity": "P0", "category": "availability", ...}
```

### Day 2: Policy 规则

```python
# Agent 分析完后，应用 Policy 修正
final_classification = self.policy.check_and_enforce(
    incident_description,
    final_classification
)
```

### Day 3: 工具系统

```python
# Agent 调用工具
result = execute_tool(tool_name, arguments)

# 工具定义告诉 LLM 何时调用
tools=get_all_tool_definitions()
```

### Day 4: 完整流程

```python
agent = IncidentAgent()
result = agent.analyze("支付接口报错")

# 返回:
# - classification: 分类结果（Day 1）
# - evidence: 工具调用证据（Day 3）
# - trace_file: 完整轨迹（Day 4）
# - 应用了 Policy 修正（Day 2）
```

## 🧪 如何测试

### 测试 Agent

```bash
# 运行 Agent
python src/agent.py

# 运行单元测试
pytest tests/test_agent.py -v

# 查看轨迹文件
cat traces/trace_*.json | jq .
```

### 预期行为

**案例 1：支付 5xx（需要查日志）**
```
描述: "支付接口 5xx 错误率 35%"

Round 1: LLM 决定查日志
  → search_logs(service="payment")
  → 返回 10 条 ERROR 日志

Round 2: LLM 基于日志分析
  → severity: P0（基于日志证据）
  → rationale: "根据日志显示..."

Policy 修正:
  → needs_human_review: True（P0 必须审核）
```

**案例 2：推荐延迟（可能不需要查日志）**
```
描述: "推荐系统 P99 延迟 2 秒"

Round 1: LLM 直接分析
  → 信息充分，不需要查日志
  → severity: P2
  → rationale: "推荐系统非核心..."

Policy 修正:
  → 无需修正
```

## 📊 关键特性

### 1. 智能决策

Agent 自己决定：
- 是否需要查日志
- 查哪个服务的日志
- 查多少条

### 2. 调用次数限制

```python
# 最多调用 2 次工具
if not self.trace.can_call_tool():
    return {"error": "调用次数超限"}
```

防止：
- 无限循环
- 成本失控

### 3. 完整轨迹

记录：
- 用户输入
- 每次工具调用（参数、结果、耗时）
- 最终答案
- 成功/失败状态

用途：
- 审计
- 调试
- 性能分析

### 4. 错误处理

处理：
- JSON 解析失败
- 工具执行失败
- 参数错误
- 超时

策略：
- 记录到轨迹
- 返回错误信息给 LLM
- LLM 可以重试或给出结论

## 📚 对应学习文档

参考 `outputs/ai-agent-engineer-day-4-v2.md`：

- **核心概念 1**：什么是 Tool-Calling Loop
- **核心概念 2**：完整流程解析
- **核心概念 3**：消息格式详解
- **核心概念 4**：为什么需要限制调用次数
- **完整示例**：参考 `src/agent.py`

## ✅ Day 4 完成标志

- [x] 创建 src/agent.py（完整的 Agent）
- [x] 实现 Tool-Calling Loop
- [x] 整合 Day 1-3 所有功能
- [x] 调用次数限制生效
- [x] 完整的轨迹记录
- [x] 创建测试文件
- [x] 所有测试通过

## 🎯 Day 4 的关键学习点

1. **Agent 的核心是决策能力**
   - Day 1-3：被动调用（你告诉它做什么）
   - Day 4：主动决策（它自己决定做什么）

2. **多轮对话是 Agent 的基础**
   - 不是一问一答
   - 是一个完整的推理过程
   - 可以多次调用工具、多次思考

3. **消息历史必须完整**
   - LLM 需要看到完整的对话
   - user → assistant → tool → assistant
   - 顺序不能乱

4. **必须限制调用次数**
   - 防止无限循环
   - 控制成本
   - 避免超时

## 🔗 与现有代码的关系

### 新增的 agent.py

- **整合**：Day 1 的 models、Day 2 的 policy、Day 3 的 tools
- **新增**：Tool-Calling Loop 逻辑
- **使用**：现有的 trace_manager.py

### 与旧代码的关系

- `src/IncidentAnalyzer.py` - 旧的 Agent（保留）
- `src/agent.py` - 新的 Agent（Day 4 标准）

区别：
- 旧：手动管理工具调用
- 新：LLM 主动决策

## 📝 Git 提交

```bash
# 添加新文件
git add src/agent.py tests/test_agent.py REFACTOR_DAY4.md

# 提交
git commit -m "Refactor Day 4: 实现 Tool-Calling Loop

改动：
- 新增 src/agent.py（完整的 Agent）
- 新增 tests/test_agent.py（Agent 测试）
- 实现 Tool-Calling Loop（多轮对话）
- 整合 Day 1-3 所有功能
- 调用次数限制和完整轨迹记录

Agent 特性：
- LLM 主动决策是否调用工具
- 完整的多轮对话流程
- 整合 Structured Output + Policy + Tools
- 完整的错误处理和轨迹记录
- 符合 Day 4 v2 规范

相关文档：outputs/ai-agent-engineer-day-4-v2.md
"
```

## 🎯 下一步：Day 5

Day 5 会添加第二个工具 - Runbook 检索：
- 实现 search_runbooks
- 创建 Runbook 文件（YAML）
- Agent 能同时使用两个工具
- 不仅能"发现问题"，还能"推荐方案"

这将让 Agent 从"诊断助手"进化到"处理建议"！
