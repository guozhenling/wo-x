# 工具调用 (Function Calling) 文档

## 概述

本项目支持 OpenAI/Anthropic 协议的工具调用（Function Calling），允许模型主动调用外部工具来获取信息或执行操作。

## 核心概念

### 什么是工具调用？

工具调用让 LLM 能够：
1. **识别需求** - 理解用户问题需要外部工具
2. **选择工具** - 从可用工具中选择合适的
3. **生成参数** - 根据用户输入生成工具参数
4. **使用结果** - 基于工具返回结果生成最终回复

### 工作流程

```
用户提问
   ↓
LLM 分析（第一轮）
   ↓
决定调用工具 + 生成参数
   ↓
执行工具（你的代码）
   ↓
工具结果返回给 LLM（第二轮）
   ↓
LLM 基于结果生成回复
```

## 工具定义规范

### 基本结构

```python
tool_definition = {
    "type": "function",
    "function": {
        "name": "工具名称",
        "description": "清晰的工具描述，说明何时使用、能做什么、不能做什么",
        "parameters": {
            "type": "object",
            "properties": {
                "参数名": {
                    "type": "string",  # 或 number, boolean, array, object
                    "description": "参数说明",
                    "enum": ["可选值1", "可选值2"]  # 可选
                }
            },
            "required": ["必填参数列表"]
        }
    }
}
```

### 示例：日志搜索工具

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": """搜索应用日志，用于故障排查和问题调查。

## 何时使用
- 故障发生时，需要查看相关日志
- 需要查找特定服务的错误日志
- 分析问题时需要查看日志详情

## 返回内容
返回匹配的日志条目，包含时间戳、服务名、日志级别、消息和 trace_id。

## 限制
- 只能搜索最近 24 小时内的日志
- 最多返回 100 条日志
- 不支持复杂的正则表达式搜索""",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "服务名称，如 payment, order, user",
                        "enum": ["payment", "order", "user", "notification"]
                    },
                    "level": {
                        "type": "string",
                        "description": "日志级别",
                        "enum": ["ERROR", "WARN", "INFO", "DEBUG"]
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词（可选）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回日志数量，默认 10，最大 100"
                    }
                },
                "required": ["service_name", "level"]
            }
        }
    }
]
```

## 工具执行器

### Pydantic 参数验证

使用 Pydantic 验证工具参数：

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal

class SearchLogsParams(BaseModel):
    """search_logs 工具参数"""
    service_name: Literal["payment", "order", "user", "notification"] = Field(
        description="服务名称"
    )
    level: Literal["ERROR", "WARN", "INFO", "DEBUG"] = Field(
        description="日志级别"
    )
    keyword: Optional[str] = Field(
        None,
        description="搜索关键词"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="返回日志数量"
    )

    @validator('keyword')
    def validate_keyword(cls, v):
        if v and len(v) < 2:
            raise ValueError("关键词至少 2 个字符")
        return v
```

### 工具执行器类

```python
class ToolExecutor:
    """工具执行器"""

    def execute_search_logs(self, params: dict) -> dict:
        """
        执行 search_logs 工具
        
        Args:
            params: 工具参数字典
            
        Returns:
            {
                "success": bool,
                "result": {...} 或 None,
                "error": str 或 None
            }
        """
        try:
            # 1. Pydantic 验证参数
            validated_params = SearchLogsParams(**params)
            
            # 2. 执行实际逻辑
            logs = self._search_logs_impl(
                service=validated_params.service_name,
                level=validated_params.level,
                keyword=validated_params.keyword,
                limit=validated_params.limit
            )
            
            # 3. 返回结果
            return {
                "success": True,
                "result": {
                    "total": len(logs),
                    "logs": logs
                },
                "error": None
            }
            
        except ValidationError as e:
            return {
                "success": False,
                "result": None,
                "error": f"参数验证失败: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"工具执行失败: {str(e)}"
            }

    def _search_logs_impl(self, service, level, keyword, limit):
        """实际的日志搜索逻辑"""
        # 这里实现真实的日志搜索
        # 可以查询数据库、文件、日志系统等
        pass
```

## 完整调用流程

### 1. 准备工具定义和执行器

```python
from src.client import LLMClient
from tools import TOOLS, ToolExecutor

client = LLMClient()
executor = ToolExecutor()
```

### 2. 第一轮：让模型决定是否调用工具

```python
messages = [
    {"role": "user", "content": "支付服务最近有什么错误？"}
]

response = client.chat_with_messages(
    messages=messages,
    tools=TOOLS,
    tool_choice="auto"
)

print(f"模型回复类型: {response['finish_reason']}")
# 输出: tool_calls
```

### 3. 执行工具调用

```python
if response['finish_reason'] == 'tool_calls':
    for tool_call in response['tool_calls']:
        tool_name = tool_call['function']['name']
        tool_args_str = tool_call['function']['arguments']
        
        # 解析参数
        tool_args = json.loads(tool_args_str)
        
        # 执行工具
        if tool_name == 'search_logs':
            result = executor.execute_search_logs(tool_args)
            
            if result['success']:
                print(f"工具执行成功: {result['result']}")
            else:
                print(f"工具执行失败: {result['error']}")
```

### 4. 第二轮：将结果返回给模型

```python
# 添加 assistant 的工具调用消息
messages.append({
    "role": "assistant",
    "content": "",
    "tool_calls": response['tool_calls']
})

# 添加工具执行结果
messages.append({
    "role": "tool",
    "tool_call_id": tool_call['id'],
    "content": json.dumps(result['result'], ensure_ascii=False)
})

# 再次调用模型
final_response = client.chat_with_messages(messages=messages)

print(f"最终回复: {final_response['content']}")
# 输出: 支付服务最近有 5 条错误日志，主要是网关超时和连接失败...
```

## 最佳实践

### 1. 工具描述要清晰

❌ **不好的描述**：
```python
"description": "搜索日志"
```

✅ **好的描述**：
```python
"description": """搜索应用日志，用于故障排查。

## 何时使用
- 需要查看特定服务的错误日志
- 分析故障时需要日志详情

## 返回内容
包含时间戳、服务名、日志级别、消息的日志条目。

## 限制
- 只能搜索最近 24 小时
- 最多返回 100 条"""
```

### 2. 参数验证三层防护

```python
# 第一层：工具定义中的 enum 限制
"enum": ["payment", "order", "user"]

# 第二层：Pydantic 验证
class Params(BaseModel):
    service: Literal["payment", "order", "user"]

# 第三层：业务逻辑验证
def execute(params):
    if params.service not in VALID_SERVICES:
        raise ValueError("无效的服务名")
```

### 3. 错误处理

```python
try:
    # 参数验证
    validated = Params(**params)
except ValidationError as e:
    return {"success": False, "error": f"参数错误: {e}"}

try:
    # 工具执行
    result = do_something(validated)
except PermissionError:
    return {"success": False, "error": "权限不足"}
except TimeoutError:
    return {"success": False, "error": "执行超时"}
except Exception as e:
    return {"success": False, "error": f"未知错误: {e}"}
```

### 4. 返回结果要规范

```python
# 统一的返回格式
{
    "success": True,          # 是否成功
    "result": {...},          # 成功时的结果
    "error": None             # 失败时的错误信息
}
```

### 5. 工具调用的安全考虑

```python
class ToolExecutor:
    """工具执行器（带安全控制）"""
    
    def execute_search_logs(self, params: dict, user_id: str) -> dict:
        """执行日志搜索（带权限检查）"""
        
        # 1. 验证用户权限
        if not self.check_permission(user_id, "read_logs"):
            return {
                "success": False,
                "error": "权限不足：您没有查看日志的权限"
            }
        
        # 2. 参数验证
        try:
            validated = SearchLogsParams(**params)
        except ValidationError as e:
            return {"success": False, "error": str(e)}
        
        # 3. 速率限制
        if not self.check_rate_limit(user_id, "search_logs"):
            return {
                "success": False,
                "error": "请求过于频繁，请稍后再试"
            }
        
        # 4. 执行工具
        try:
            result = self._do_search(validated)
            
            # 5. 审计日志
            self.log_audit(
                user_id=user_id,
                action="search_logs",
                params=params,
                success=True
            )
            
            return {"success": True, "result": result}
            
        except Exception as e:
            self.log_audit(
                user_id=user_id,
                action="search_logs",
                params=params,
                success=False,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
```

## 常见问题

### Q1: 模型不调用工具怎么办？

**原因**：
- 工具描述不清晰，模型不知道何时用
- 工具名称不直观
- 用户问题太模糊

**解决**：
```python
# 改进工具描述
"description": """明确说明：
1. 这个工具是做什么的
2. 什么时候应该用它
3. 它能返回什么结果
4. 它有什么限制"""

# 或者在 system prompt 中引导
system_prompt = """你是一个助手，当用户询问日志或错误时，
必须使用 search_logs 工具来查看实际日志，不要凭空猜测。"""
```

### Q2: 参数格式错误怎么办？

**解决**：使用 Pydantic 验证并返回清晰的错误信息

```python
try:
    params = SearchLogsParams(**raw_params)
except ValidationError as e:
    # 返回清晰的错误信息
    errors = []
    for error in e.errors():
        field = error['loc'][0]
        msg = error['msg']
        errors.append(f"{field}: {msg}")
    
    return {
        "success": False,
        "error": f"参数验证失败: {', '.join(errors)}"
    }
```

### Q3: 工具执行太慢怎么办？

**解决**：
1. 添加超时控制
2. 异步执行
3. 缓存结果

```python
import asyncio
from functools import lru_cache

class ToolExecutor:
    async def execute_search_logs_async(self, params: dict):
        """异步执行工具"""
        try:
            result = await asyncio.wait_for(
                self._search_logs_async(params),
                timeout=5.0  # 5秒超时
            )
            return {"success": True, "result": result}
        except asyncio.TimeoutError:
            return {"success": False, "error": "执行超时"}
    
    @lru_cache(maxsize=100)
    def _get_cached_result(self, service, level, timestamp_range):
        """缓存结果"""
        pass
```

## 示例代码

完整示例请参考：
- `examples/demo_tools.py` - 工具调用演示
- `tools/log_search.py` - 日志搜索工具实现
- `tools/executor.py` - 工具执行器

## 下一步

1. 阅读 `examples/demo_tools.py` 了解完整流程
2. 实现自己的工具定义和执行器
3. 添加权限控制和审计日志
4. 测试边界情况和错误处理

---

**核心理念**：工具调用让 LLM 从"只能说"变成"能做事"，但你必须严格验证参数和控制权限。
