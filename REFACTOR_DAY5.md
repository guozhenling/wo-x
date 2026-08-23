# Day 5 重构说明

## 📋 改动概览

### 新增文件

1. **tools/runbook_search.py** - Runbook 检索工具
   - 基于关键词匹配
   - 返回标准化处理步骤

2. **runbooks/** - Runbook 文件目录
   - `payment_5xx.yaml` - 支付 5xx 处理
   - `database_deadlock.yaml` - 数据库死锁处理
   - `deployment_rollback.yaml` - 部署回滚流程

3. **tests/test_runbooks.py** - Runbook 测试

### 更新文件

- `tools/tool_definitions.py` - 添加 search_runbooks 定义
- `tools/executor.py` - 注册 search_runbooks
- `tools/__init__.py` - 导出 search_runbooks

## 🎯 Day 5 的核心：第二个工具

### Agent 现在能做什么？

**Day 3（只有 search_logs）**：
```
Agent: "我看到日志有很多 5xx 错误"
用户: "那怎么办？"
Agent: "..."
```

**Day 5（有 search_runbooks）**：
```
Agent: "我看到日志有很多 5xx 错误，并且找到了标准处理流程：
1. 检查支付网关状态
2. 检查数据库连接
3. 如果网关问题，切换备用通道
..."
```

### 两个工具的协同

```
用户问题: "支付接口报错"
  ↓
[Round 1] Agent: "我需要查日志"
  ↓
  search_logs(service="payment")
  → 返回: 35 条 ERROR 日志
  ↓
[Round 2] Agent: "日志显示 5xx 很多，我查一下处理流程"
  ↓
  search_runbooks("payment 5xx", severity="P0")
  → 返回: "支付 5xx 错误处理" Runbook
  ↓
[Round 3] Agent: "根据日志和 Runbook，判断为 P0..."
  最终输出: {
    severity: "P0",
    rationale: "根据日志和标准流程...",
    recommendation: "1. 检查网关 2. 切换备用..."
  }
```

## 🔍 Runbook 文件格式

YAML 格式，包含：

```yaml
title: 支付 5xx 错误处理
keywords: [支付, 5xx, payment, gateway]  # 用于匹配
severity_match: [P0, P1]                  # 适用的严重程度
category: availability                     # 类别

check_steps:                              # 检查步骤
  - 检查支付网关状态
  - 检查数据库连接

fix_steps:                                # 修复步骤
  - 如果网关问题：切换备用通道
  - 如果数据库问题：重启连接池

escalation_conditions:                    # 升级条件
  - 持续时间 > 10 分钟
  - 影响用户 > 1000
```

## 🧪 如何测试

### 测试 Runbook 检索

```bash
# 测试工具
python tools/runbook_search.py

# 运行单元测试
pytest tests/test_runbooks.py -v

# 测试 Agent（现在会调用两个工具）
python src/agent.py
```

### 预期行为

```python
# 单独测试
from tools import search_runbooks

results = search_runbooks("支付接口 5xx", severity="P0")
print(results[0]['title'])  # → "支付 5xx 错误处理"
print(results[0]['check_steps'])  # → ["检查网关...", ...]
```

## 📊 工具对比

| 特性 | search_logs | search_runbooks |
|------|------------|-----------------|
| 用途 | 查证据 | 查方案 |
| 输入 | service, keyword | description, severity |
| 输出 | 日志列表 | Runbook 列表 |
| 数据源 | data/sample_logs.jsonl | runbooks/*.yaml |
| Day | Day 3 | Day 5 |

## 🎯 关键学习点

### 1. Agent 不只是"发现问题"

- ✅ 发现问题：search_logs
- ✅ 推荐方案：search_runbooks
- ✅ 完整闭环：诊断 → 分析 → 建议

### 2. 工具组合的威力

单个工具：能力有限
```
只有 logs → 只能看到错误
只有 runbooks → 只能查手册
```

多个工具：能力叠加
```
logs + runbooks → 能诊断 + 能建议
```

### 3. Runbook 是知识沉淀

- 老员工的经验 → YAML 文件
- 标准化流程 → 可复用
- 新人也能处理 → 降低门槛

### 4. 关键词匹配已经够用

不需要复杂的向量检索：
- ✅ 关键词匹配：简单、快速、可控
- ⚠️ 向量检索：复杂、慢、成本高

80% 的场景用关键词就够了。

## 📚 对应学习文档

参考 `outputs/ai-agent-engineer-day-5-v2.md`：

- **核心概念 1**：什么是 Runbook
- **核心概念 2**：简单检索 vs 向量检索
- **核心概念 3**：匹配算法
- **完整示例**：参考 tools/runbook_search.py

## ✅ Day 5 完成标志

- [x] 创建 tools/runbook_search.py
- [x] 创建 3 个 Runbook 文件
- [x] 更新工具定义和执行器
- [x] 创建测试文件
- [x] 所有测试通过

## 🔗 集成到 Agent

Agent 会自动使用新工具：

```python
# src/agent.py 中
tools=get_all_tool_definitions()  # 自动包含 search_runbooks

# LLM 会自己决定：
# - 是否需要查 Runbook
# - 什么时候查
# - 查询什么内容
```

无需修改 Agent 代码！

## 📝 Git 提交

```bash
# 添加所有文件
git add tools/runbook_search.py runbooks/ tests/test_runbooks.py REFACTOR_DAY5.md
git add tools/__init__.py tools/tool_definitions.py tools/executor.py

# 提交
git commit -m "Refactor Day 5: 添加 Runbook 检索工具

改动：
- 新增 tools/runbook_search.py（Runbook 检索）
- 新增 runbooks/ 目录（3 个 YAML 文件）
- 新增 tests/test_runbooks.py（Runbook 测试）
- 更新工具定义和执行器

Runbook 特性：
- 基于关键词匹配
- 返回标准化处理步骤
- 包含检查步骤和升级条件
- YAML 格式，易于维护

Agent 能力升级：
- 不仅能发现问题（logs）
- 还能推荐方案（runbooks）
- 完整的诊断 → 建议闭环

符合 Day 5 v2 规范

相关文档：outputs/ai-agent-engineer-day-5-v2.md
"
```

## 🎯 下一步：Day 6

Day 6 会验证 trace_manager：
- 现有的 trace_manager.py 已经很完善
- 验证与 Agent 的集成
- 确保轨迹记录完整

Day 6 应该会很快，因为代码已经存在！
