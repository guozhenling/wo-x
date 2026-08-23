# 工具调用快速上手指南

## 🚀 5分钟快速体验

### 1. 运行演示（最快方式）

```bash
source venv/bin/activate
python examples/demo_tools.py
```

你会看到：
- ✅ 模型决定调用 `search_logs` 工具
- ✅ 工具返回真实的日志数据
- ✅ 模型基于日志给出分析和建议

### 2. 核心代码（不到10行）

```python
from src.client import LLMClient
from src.tools import get_tool_definitions, execute_tool

client = LLMClient()

# 第一轮：让模型决定是否调用工具
messages = [{"role": "user", "content": "查询支付服务的错误日志"}]
response = client.chat(messages, tools=get_tool_definitions())

# 如果模型要调用工具
if response.get("tool_calls"):
    for tool_call in response["tool_calls"]:
        # 执行工具（自动参数校验）
        result = execute_tool(tool_call)
        print(f"工具返回: {result}")
```

## 📖 理解工具调用

### 工具是什么？

工具就是 Python 函数，让模型能够：
- 查询日志（search_logs）
- 查询指标（query_metrics）← 未来
- 查询服务状态（get_service_status）← 未来

### 为什么需要工具？

**没有工具**：
```
用户: 支付服务有什么问题？
模型: 可能是网关超时... [猜测，不可靠]
```

**有工具**：
```
用户: 支付服务有什么问题？
模型: [调用 search_logs 查询真实日志]
模型: 根据日志显示，有2次网关超时... [基于事实，可靠]
```

## 🔧 添加新工具（3步）

### 步骤 1：定义参数 Schema

```python
from pydantic import BaseModel, Field

class GetWeatherInput(BaseModel):
    """查询天气的参数"""
    city: str = Field(..., description="城市名称")
    date: str = Field(None, description="日期（可选）")
```

### 步骤 2：实现工具函数

```python
def get_weather_tool(city: str, date: str = None) -> str:
    """查询指定城市的天气"""
    # 这里是你的业务逻辑
    return f"{city}的天气：晴天，25度"
```

### 步骤 3：注册工具

```python
from src.tools import TOOL_REGISTRY

TOOL_REGISTRY["get_weather"] = {
    "function": get_weather_tool,
    "schema": GetWeatherInput
}
```

完成！现在模型可以调用 `get_weather` 了。

## 🛡️ 安全保证

### 三层防护

1. **OpenAI Schema** - API 层面定义参数类型和范围
2. **Pydantic 校验** - 执行前强制验证所有参数
3. **超时保护** - 防止工具执行时间过长

### 示例

```python
# 用户输入: {"service_name": "", "limit": 999}

# 第一层：OpenAI Schema 就会拒绝（service_name 不能为空）
# 第二层：Pydantic 再次校验（limit 不能超过20）
# 第三层：即使通过，5秒后自动超时

# 结果：绝不会执行不安全的操作
```

## 📊 当前可用工具

### search_logs

查询应用日志，用于故障排查。

**参数**：
- `service_name` (必需): 服务名称，如 "payment"
- `keyword` (可选): 关键词过滤
- `level` (可选): 日志级别 (ERROR/WARN/INFO)
- `limit` (可选): 返回数量，默认10，最多20

**示例**：
```python
from src.tools import execute_tool

result = execute_tool({
    "function": {"name": "search_logs"},
    "arguments": '{"service_name": "payment", "level": "ERROR", "limit": 5}'
})

print(f"找到 {result['total']} 条日志")
for log in result['logs']:
    print(f"[{log['level']}] {log['message']}")
```

## 🧪 测试你的工具

```python
import pytest
from src.tools import execute_tool

def test_my_tool():
    """测试工具调用"""
    result = execute_tool({
        "function": {"name": "search_logs"},
        "arguments": '{"service_name": "payment", "limit": 5}'
    })
    
    assert result['total'] <= 5
    assert all('service' in log for log in result['logs'])
```

运行测试：
```bash
pytest tests/test_log_search.py -v
```

## 📚 进阶学习

### 1. 多轮对话

让模型多次调用工具：

```python
messages = [{"role": "user", "content": "分析支付服务问题"}]

# 第一轮：模型查询日志
response1 = client.chat(messages, tools=get_tool_definitions())
# 执行工具...

# 第二轮：基于日志查询指标
response2 = client.chat(messages, tools=get_tool_definitions())
# 执行工具...

# 第三轮：给出最终分析
response3 = client.chat(messages)
```

### 2. 工具组合

多个工具协作：

```python
# 先查日志发现超时
logs = search_logs(service="payment", keyword="timeout")

# 再查延迟指标
metrics = query_metrics(service="payment", metric="latency")

# 最后查历史故障
history = search_incidents(keywords=["payment", "timeout"])
```

### 3. 条件工具调用

```python
# 只在特定条件下提供工具
if user_role == "admin":
    tools = get_tool_definitions()  # 管理员有所有工具
else:
    tools = [get_tool_definitions()["search_logs"]]  # 普通用户只能查日志
```

## 🔍 调试技巧

### 1. 查看工具定义

```python
from src.tools import get_tool_definitions

tools = get_tool_definitions()
print(json.dumps(tools, indent=2, ensure_ascii=False))
```

### 2. 模拟工具调用

```python
from src.tools import execute_tool

# 手动构造 tool_call 测试
tool_call = {
    "id": "test_123",
    "function": {
        "name": "search_logs",
        "arguments": '{"service_name": "payment", "limit": 5}'
    }
}

result = execute_tool(tool_call)
print(result)
```

### 3. 查看参数校验错误

```python
try:
    execute_tool({
        "function": {"name": "search_logs"},
        "arguments": '{"service_name": "", "limit": 999}'  # 故意错误
    })
except ValueError as e:
    print(f"参数错误: {e}")
```

## 💡 最佳实践

### 1. 工具描述要清晰

```python
class SearchLogsInput(BaseModel):
    """搜索应用日志，用于故障排查和问题调查"""  # ← 好的描述
    service_name: str = Field(..., description="服务名称，如 payment、order")
```

### 2. 参数校验要严格

```python
class SearchLogsInput(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=50)  # ← 限制长度
    limit: int = Field(10, ge=1, le=20)  # ← 限制范围
```

### 3. 错误处理要完整

```python
def my_tool(param: str) -> str:
    try:
        # 业务逻辑
        result = do_something(param)
        return json.dumps(result)
    except TimeoutError:
        return json.dumps({"error": "操作超时"})
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        return json.dumps({"error": str(e)})
```

## 📞 遇到问题？

### 常见问题

**Q: 模型不调用工具？**
A: 检查工具描述是否清晰，确保问题和工具功能匹配。

**Q: 参数校验失败？**
A: 查看 Pydantic ValidationError，修正参数定义。

**Q: 工具执行超时？**
A: 检查工具逻辑，优化性能，或增加超时时间。

### 获取帮助

1. 查看完整文档：`docs/TOOLS.md`
2. 查看测试用例：`tests/test_log_search.py`
3. 运行演示代码：`examples/demo_tools.py`

## 🎉 下一步

- ✅ 运行演示：`python examples/demo_tools.py`
- ✅ 查看文档：`docs/TOOLS.md`
- ✅ 添加新工具：按照上面的3步指南
- ✅ 编写测试：参考 `tests/test_log_search.py`

**开始使用工具调用，让你的 LLM 应用更强大！**
