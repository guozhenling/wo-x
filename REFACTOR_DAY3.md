# Day 3 重构说明

## 📋 改动概览

### 新增文件

1. **tools/** - 工具系统目录
   - `__init__.py` - 包初始化
   - `log_search.py` - 日志搜索工具（从 src/ 重构）
   - `tool_definitions.py` - 工具定义（给 LLM）
   - `executor.py` - 工具执行器

2. **data/** - 数据目录
   - `sample_logs.jsonl` - 示例日志数据（20 条）

3. **tests/test_tools.py** - 工具系统测试

### 目录结构变化

```
旧结构：
src/
  - log_search.py  (混合了工具逻辑和定义)

新结构：
tools/
  - __init__.py
  - log_search.py          (工具逻辑)
  - tool_definitions.py    (工具定义，给 LLM)
  - executor.py            (工具执行器)

data/
  - sample_logs.jsonl      (示例数据)
```

### 设计理念

**关注点分离**：
- `log_search.py` - 工具的实现逻辑
- `tool_definitions.py` - 工具的 API 定义（给 LLM 看的）
- `executor.py` - 工具调用的统一入口

**安全边界**：
- 只读操作
- 限制返回条数（最多 20 条）
- 敏感信息脱敏（密码、token）
- 超时保护（5 秒）

## 🔄 改进点

### 1. 工具定义独立

**旧版本**：工具定义混在代码里
**新版本**：`tool_definitions.py` 专门管理工具定义

好处：
- LLM 需要什么信息一目了然
- 修改定义不影响实现
- 易于添加新工具

### 2. 统一的执行器

**新增**：`executor.py` 统一管理工具调用

好处：
- 工具注册在一个地方（TOOL_REGISTRY）
- 统一的错误处理
- 方便添加日志、监控

### 3. 示例数据

**新增**：`data/sample_logs.jsonl`

好处：
- 可以在没有真实日志系统时测试
- 提供了标准的测试数据
- 覆盖了 4 个服务、2 个级别

## 🧪 如何测试

### 测试单个工具

```bash
# 测试 log_search
python tools/log_search.py

# 测试 tool_definitions
python tools/tool_definitions.py

# 测试 executor
python tools/executor.py
```

### 运行单元测试

```bash
# 运行所有工具测试
pytest tests/test_tools.py -v

# 测试特定功能
pytest tests/test_tools.py::TestLogSearch::test_search_by_service -v
```

### 在 Python 中使用

```python
from tools import search_logs, execute_tool

# 方式 1: 直接调用
logs = search_logs(service="payment", limit=5)
print(f"找到 {len(logs)} 条日志")

# 方式 2: 通过 executor（模拟 LLM 调用）
result = execute_tool(
    "search_logs",
    {"service": "payment", "limit": 5}
)
print(f"找到 {len(result)} 条日志")
```

## 📚 对应学习文档

参考 `outputs/ai-agent-engineer-day-3-v2.md`：

- **核心概念 1**：什么是工具（Tool）
- **核心概念 2**：工具的三要素（函数、描述、Schema）
- **核心概念 3**：工具的安全边界
- **完整示例**：参考 `tools/` 目录

## ✅ Day 3 完成标志

- [x] 创建 tools/ 目录结构
- [x] 实现 log_search.py
- [x] 实现 tool_definitions.py
- [x] 实现 executor.py
- [x] 创建示例数据
- [x] 创建测试文件
- [x] 所有测试通过

## 🔗 与现有代码的关系

### 向后兼容

- 原 `src/log_search.py` 保留（暂时）
- 新代码在 `tools/` 目录
- 测试同时覆盖新旧代码

### 迁移计划

Day 4 会把 Agent 从使用 `src/log_search.py` 改为使用 `tools/`。

## 🎯 Day 3 的关键学习点

1. **工具是 Agent 的"手和脚"**
   - 没有工具，Agent 只能"猜测"
   - 有了工具，Agent 能"查证据"

2. **工具的三要素**
   - 函数签名：Python 能调用
   - 工具描述：LLM 知道什么时候用
   - 参数 Schema：校验参数合法性

3. **只读工具的安全边界**
   - 限制（最多 20 条）
   - 脱敏（密码、token）
   - 超时（5 秒）
   - 幂等（多次调用结果一致）

4. **关注点分离**
   - 实现（log_search.py）
   - 定义（tool_definitions.py）
   - 执行（executor.py）

## 📝 Git 提交

```bash
# 添加所有新文件
git add tools/ data/ tests/test_tools.py REFACTOR_DAY3.md

# 提交
git commit -m "Refactor Day 3: 创建工具系统（tools/）

改动：
- 新增 tools/ 目录（log_search, tool_definitions, executor）
- 新增 data/sample_logs.jsonl（示例数据 20 条）
- 新增 tests/test_tools.py（工具测试）
- 关注点分离：实现、定义、执行分离
- 添加安全边界：限制、脱敏、超时

工具系统特性：
- 只读操作，幂等
- 统一的工具注册和执行
- 完整的错误处理
- 符合 Day 3 v2 规范

相关文档：outputs/ai-agent-engineer-day-3-v2.md
"
```

## 🎯 下一步：Day 4

Day 4 会实现 Tool-Calling Loop：
- LLM 主动决定调用工具
- 完整的多轮对话
- 集成 classifier + policy + tools
- 实现标准的 Agent

这是关键的一天，会把前 3 天的内容串起来！
