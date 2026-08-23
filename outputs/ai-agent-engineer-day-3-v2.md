# Day 3 - 第一个工具：日志搜索

**预计学习时间**: 2.5-3 小时

## 🎯 学习目标

学完今天，你将：
- 理解什么是工具（Tool）
- 掌握只读工具的设计原则
- 能实现一个安全的日志搜索工具
- 知道工具定义（Tool Definition）的关键要素

## 📖 核心概念

### 1. 什么是工具（Tool）？

**目前的问题**：Agent 只能"猜测"

```python
用户: "支付服务为什么报错？"
Agent: "可能是数据库连接问题，建议查看日志..."  ← 瞎猜
```

**有了工具**：Agent 能"查证据"

```python
用户: "支付服务为什么报错？"
Agent: "让我查一下日志..."
  ↓
调用 search_logs("payment", "ERROR")  ← 实际查询
  ↓
Agent: "根据日志，发现 5xx 错误 35 条，主要是数据库超时"  ← 基于证据
```

**定义**：工具是 Agent 能调用的 Python 函数，用于获取信息或执行操作。

**类比你熟悉的 Java**：
```java
// Agent = Service
// Tool = DAO/Repository

public class IncidentAnalyzer {  // Agent
    private LogRepository logRepo;  // Tool
    
    public Analysis analyze(String incident) {
        // 调用工具获取数据
        List<Log> logs = logRepo.searchLogs("payment", "ERROR");
        
        // 基于数据分析
        return analyzeWithEvidence(logs);
    }
}
```

### 2. 工具的分类

**按读写性质**：

| 类型 | 特点 | 例子 | 风险 |
|------|------|------|------|
| 只读工具 | 不修改系统状态 | search_logs, get_metrics | 低 |
| 写入工具 | 修改系统状态 | restart_service, rollback | 高 |

**按数据来源**：

| 类型 | 例子 | 今天学习 |
|------|------|----------|
| 内部数据 | 查日志、查数据库 | ✓ |
| 外部 API | 调用监控系统 | Day 8 |
| 执行命令 | 重启服务、回滚 | Day 11 |

**今天只做只读工具**，原因：
- ✅ 安全：不会改坏东西
- ✅ 幂等：多次调用结果一样
- ✅ 简单：适合入门

### 3. 工具定义的三要素

**要素 1：函数签名（做什么）**
```python
def search_logs(
    service: str,          # 必需参数
    level: str = "ERROR",  # 可选参数（有默认值）
    time_range: Optional[int] = None
) -> List[Dict[str, Any]]:
    """搜索服务日志"""
    pass
```

**要素 2：工具描述（什么时候用）**
```python
description = """搜索指定服务的日志。

使用场景：
- 分析错误原因时查看错误日志
- 统计错误频率
- 查找特定时间段的异常

不能做：
- 不能修改日志
- 不能查询敏感信息（密码、token）
"""
```

**要素 3：参数 Schema（参数规范）**
```json
{
  "type": "object",
  "properties": {
    "service": {
      "type": "string",
      "description": "服务名，如 payment, order, user",
      "enum": ["payment", "order", "user", "recommendation"]
    },
    "level": {
      "type": "string",
      "description": "日志级别",
      "enum": ["ERROR", "WARN", "INFO"],
      "default": "ERROR"
    },
    "time_range": {
      "type": "integer",
      "description": "时间范围（分钟），如 60 表示最近1小时",
      "minimum": 1,
      "maximum": 1440
    }
  },
  "required": ["service"]
}
```

**为什么需要这三要素？**

1. **函数签名** → Python 能调用
2. **工具描述** → LLM 知道什么时候用
3. **参数 Schema** → 校验参数合法性

### 4. 工具的安全边界

**只读工具也有风险**：

❌ **风险 1：信息泄露**
```python
# 危险：可能返回密码、token
def search_logs(service, keyword):
    logs = db.query(f"SELECT * FROM logs WHERE message LIKE '%{keyword}%'")
    return logs  # 可能包含敏感信息
```

✅ **安全做法**：
```python
def search_logs(service, level="ERROR"):
    logs = db.query(...)
    # 过滤敏感字段
    return [{
        "timestamp": log.timestamp,
        "service": log.service,
        "level": log.level,
        "message": redact_sensitive(log.message)  # 脱敏
    } for log in logs]
```

❌ **风险 2：性能问题**
```python
# 危险：无限制查询
def search_logs(service):
    return db.query("SELECT * FROM logs")  # 可能返回百万条
```

✅ **安全做法**：
```python
def search_logs(service, limit=100):
    if limit > 1000:
        limit = 1000  # 强制上限
    return db.query(f"... LIMIT {limit}")
```

❌ **风险 3：SQL 注入**
```python
# 危险：拼接字符串
def search_logs(service):
    return db.query(f"SELECT * FROM logs WHERE service='{service}'")
    # service = "'; DROP TABLE logs; --"
```

✅ **安全做法**：
```python
def search_logs(service: str):
    # 参数化查询
    return db.query("SELECT * FROM logs WHERE service=?", (service,))
    # 或 Pydantic 校验
```

**安全原则**：
1. **最小权限**：只返回必需信息
2. **数据脱敏**：隐藏密码、token
3. **限制范围**：限制查询条数、时间范围
4. **参数校验**：用 Pydantic 校验类型和值域
5. **幂等性**：多次调用结果一致

### 5. 工作流程

```
┌─────────────────────────────────────┐
│ Step 1: 定义工具                     │
│                                     │
│ def search_logs(service, level):    │
│     """搜索日志"""                   │
│     return query_database(...)      │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 2: 创建工具描述（给 LLM）        │
│                                     │
│ {                                   │
│   "name": "search_logs",            │
│   "description": "搜索服务日志...", │
│   "parameters": {...}               │
│ }                                   │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 3: LLM 决定调用（Day 4 学习）    │
│                                     │
│ LLM: "需要查日志"                   │
│ → tool_calls: [{                    │
│     name: "search_logs",            │
│     arguments: {service: "payment"} │
│   }]                                │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 4: Python 执行工具              │
│                                     │
│ result = search_logs("payment")     │
│ # 返回日志数据                       │
└─────────────────────────────────────┘
```

**今天重点**：Step 1 + Step 2（实现工具和定义）  
**明天学习**：Step 3 + Step 4（LLM 调用流程）

## 🔍 完整示例

让我们实现一个安全的日志搜索工具：

### 步骤 1: 实现工具函数

```python
# tools/log_search.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import re

def search_logs(
    service: str,
    level: str = "ERROR",
    time_range: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    搜索服务日志（模拟实现）
    
    Args:
        service: 服务名（payment, order, user, recommendation）
        level: 日志级别（ERROR, WARN, INFO）
        time_range: 时间范围（分钟），None 表示不限
        keyword: 关键词过滤
        limit: 最大返回条数（1-1000）
        
    Returns:
        日志列表，每条包含：
        - timestamp: 时间戳
        - service: 服务名
        - level: 级别
        - message: 消息（已脱敏）
        
    实际生产环境应该：
        - 连接 Elasticsearch/Splunk
        - 使用参数化查询
        - 实现真正的脱敏逻辑
    """
    # 参数校验
    if limit > 1000:
        limit = 1000
    if limit < 1:
        limit = 1
    
    valid_services = ["payment", "order", "user", "recommendation"]
    if service not in valid_services:
        return []
    
    valid_levels = ["ERROR", "WARN", "INFO", "DEBUG"]
    if level not in valid_levels:
        level = "ERROR"
    
    # 读取示例日志数据
    data_file = Path(__file__).parent.parent / "data" / "sample_logs.jsonl"
    
    if not data_file.exists():
        # 如果没有数据文件，返回模拟数据
        return _generate_mock_logs(service, level, limit)
    
    # 解析日志文件
    logs = []
    with open(data_file, 'r') as f:
        for line in f:
            try:
                log = json.loads(line)
                
                # 过滤服务
                if log.get('service') != service:
                    continue
                
                # 过滤级别
                if log.get('level') != level:
                    continue
                
                # 过滤时间范围
                if time_range:
                    log_time = datetime.fromisoformat(log['timestamp'])
                    cutoff = datetime.now() - timedelta(minutes=time_range)
                    if log_time < cutoff:
                        continue
                
                # 过滤关键词
                if keyword and keyword not in log.get('message', ''):
                    continue
                
                # 脱敏
                log['message'] = _redact_sensitive(log['message'])
                
                logs.append(log)
                
                if len(logs) >= limit:
                    break
                    
            except json.JSONDecodeError:
                continue
    
    return logs

def _redact_sensitive(message: str) -> str:
    """
    脱敏敏感信息
    
    隐藏：
    - 密码
    - Token
    - 信用卡号
    - 身份证号
    """
    # 隐藏密码
    message = re.sub(
        r'(password|pwd|passwd)[=:]\s*\S+',
        r'\1=***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # 隐藏 token
    message = re.sub(
        r'(token|auth|key)[=:]\s*\S+',
        r'\1=***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # 隐藏信用卡号（简单示例）
    message = re.sub(
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        '****-****-****-****',
        message
    )
    
    return message

def _generate_mock_logs(
    service: str,
    level: str,
    limit: int
) -> List[Dict[str, Any]]:
    """生成模拟日志（用于演示）"""
    import random
    
    messages = {
        "payment": [
            "Database connection timeout after 30s",
            "Payment gateway returned 503",
            "Transaction rollback: insufficient balance",
            "Rate limit exceeded for user 12345"
        ],
        "order": [
            "Order creation failed: invalid product_id",
            "Inventory check timeout",
            "Order status update failed",
            "Redis connection lost"
        ],
        "user": [
            "User authentication failed",
            "Session expired",
            "Password reset token invalid",
            "Email sending failed"
        ],
        "recommendation": [
            "Model inference timeout",
            "Feature extraction failed",
            "Cache miss rate 95%",
            "ML model version mismatch"
        ]
    }
    
    logs = []
    now = datetime.now()
    
    for i in range(min(limit, 10)):
        logs.append({
            "timestamp": (now - timedelta(minutes=random.randint(1, 60))).isoformat(),
            "service": service,
            "level": level,
            "message": random.choice(messages.get(service, ["Unknown error"])),
            "trace_id": f"trace_{random.randint(10000, 99999)}"
        })
    
    return sorted(logs, key=lambda x: x['timestamp'], reverse=True)

# 测试
if __name__ == "__main__":
    print("测试日志搜索工具\n")
    
    # 测试 1: 查询支付错误
    print("1. 查询支付服务错误日志:")
    logs = search_logs("payment", "ERROR", limit=5)
    for log in logs:
        print(f"  [{log['timestamp']}] {log['message']}")
    
    print("\n2. 查询订单服务最近1小时警告:")
    logs = search_logs("order", "WARN", time_range=60, limit=3)
    for log in logs:
        print(f"  [{log['timestamp']}] {log['message']}")
    
    print("\n3. 测试脱敏:")
    sensitive_msg = "Login failed: password=secret123, token=abc-xyz-123"
    print(f"  原始: {sensitive_msg}")
    print(f"  脱敏: {_redact_sensitive(sensitive_msg)}")
```

**运行测试**：
```bash
python tools/log_search.py
```

### 步骤 2: 创建示例日志数据

```bash
# 创建数据目录
mkdir -p data

# 创建示例日志
cat > data/sample_logs.jsonl << 'EOF'
{"timestamp": "2024-01-20T10:30:00", "service": "payment", "level": "ERROR", "message": "Database connection timeout after 30s", "trace_id": "trace_12345"}
{"timestamp": "2024-01-20T10:31:00", "service": "payment", "level": "ERROR", "message": "Payment gateway returned 503", "trace_id": "trace_12346"}
{"timestamp": "2024-01-20T10:32:00", "service": "payment", "level": "ERROR", "message": "Transaction failed: insufficient balance", "trace_id": "trace_12347"}
{"timestamp": "2024-01-20T10:33:00", "service": "order", "level": "WARN", "message": "Order creation slow: 3.2s", "trace_id": "trace_12348"}
{"timestamp": "2024-01-20T10:34:00", "service": "order", "level": "ERROR", "message": "Inventory check timeout", "trace_id": "trace_12349"}
{"timestamp": "2024-01-20T10:35:00", "service": "user", "level": "ERROR", "message": "User authentication failed", "trace_id": "trace_12350"}
{"timestamp": "2024-01-20T10:36:00", "service": "recommendation", "level": "ERROR", "message": "Model inference timeout", "trace_id": "trace_12351"}
{"timestamp": "2024-01-20T10:37:00", "service": "payment", "level": "ERROR", "message": "Redis connection lost", "trace_id": "trace_12352"}
{"timestamp": "2024-01-20T10:38:00", "service": "payment", "level": "ERROR", "message": "Payment processing failed: gateway timeout", "trace_id": "trace_12353"}
{"timestamp": "2024-01-20T10:39:00", "service": "order", "level": "ERROR", "message": "Order status update failed", "trace_id": "trace_12354"}
EOF
```

### 步骤 3: 定义工具描述（给 LLM）

```python
# tools/tool_definitions.py
from typing import Dict, Any

def get_search_logs_definition() -> Dict[str, Any]:
    """
    返回 search_logs 的工具定义
    
    这个定义会传给 LLM，告诉它：
    - 这个工具叫什么
    - 什么时候该用
    - 有哪些参数
    - 参数的类型和限制
    """
    return {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": """搜索指定服务的日志，用于分析故障原因。

使用场景：
- 当需要查看具体错误信息时
- 当需要统计错误频率时
- 当需要查找特定时间段的异常时

返回：
- 日志列表，包含时间、级别、消息等信息
- 最多返回 100 条（性能考虑）

注意：
- 不能查询敏感信息（密码、token 已脱敏）
- 只能查询最近 24 小时的日志""",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "服务名",
                        "enum": ["payment", "order", "user", "recommendation"]
                    },
                    "level": {
                        "type": "string",
                        "description": "日志级别",
                        "enum": ["ERROR", "WARN", "INFO"],
                        "default": "ERROR"
                    },
                    "time_range": {
                        "type": "integer",
                        "description": "时间范围（分钟），如 60 表示最近 1 小时，不提供则查询所有",
                        "minimum": 1,
                        "maximum": 1440
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最大返回条数",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    }
                },
                "required": ["service"]
            }
        }
    }

def get_all_tool_definitions() -> list:
    """返回所有工具定义（目前只有一个）"""
    return [get_search_logs_definition()]

# 测试
if __name__ == "__main__":
    import json
    
    definition = get_search_logs_definition()
    print("工具定义（JSON）:")
    print(json.dumps(definition, indent=2, ensure_ascii=False))
```

**运行测试**：
```bash
python tools/tool_definitions.py
```

### 步骤 4: 工具注册和调用

```python
# tools/executor.py
from typing import Dict, Any
import json
from tools.log_search import search_logs

def execute_tool(
    tool_name: str,
    tool_arguments: Dict[str, Any]
) -> Any:
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        tool_arguments: 工具参数（JSON 对象）
        
    Returns:
        工具执行结果
        
    Raises:
        ValueError: 工具不存在或参数不合法
    """
    # 工具映射表
    TOOL_REGISTRY = {
        "search_logs": search_logs,
        # 未来添加更多工具...
    }
    
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"未知工具: {tool_name}")
    
    tool_function = TOOL_REGISTRY[tool_name]
    
    try:
        # 执行工具
        result = tool_function(**tool_arguments)
        return result
    except TypeError as e:
        raise ValueError(f"参数错误: {e}")
    except Exception as e:
        raise RuntimeError(f"工具执行失败: {e}")

# 测试
if __name__ == "__main__":
    print("测试工具执行器\n")
    
    # 测试 1: 正确调用
    print("1. 正确调用:")
    result = execute_tool("search_logs", {"service": "payment", "limit": 3})
    print(f"   返回 {len(result)} 条日志")
    
    # 测试 2: 错误的工具名
    print("\n2. 错误的工具名:")
    try:
        execute_tool("unknown_tool", {})
    except ValueError as e:
        print(f"   ✓ 捕获异常: {e}")
    
    # 测试 3: 错误的参数
    print("\n3. 错误的参数:")
    try:
        execute_tool("search_logs", {"invalid_param": "test"})
    except ValueError as e:
        print(f"   ✓ 捕获异常: {e}")
    
    print("\n✅ 测试通过！")
```

**运行测试**：
```bash
python tools/executor.py
```

## 💪 动手练习

### Level 1: 最低完成线（30 分钟）

**任务**：
- [ ] 完成 `tools/log_search.py`
- [ ] 创建 `data/sample_logs.jsonl`（至少 10 条）
- [ ] 运行测试，看到日志查询结果

**验证**：能成功查询并返回日志

### Level 2: 标准任务（1 小时）

**任务**：
1. 扩展日志数据到 50 条，覆盖 4 个服务

2. 测试所有参数组合：
   ```python
   # 不同服务
   search_logs("payment")
   search_logs("order")
   
   # 不同级别
   search_logs("payment", "ERROR")
   search_logs("payment", "WARN")
   
   # 时间范围
   search_logs("payment", time_range=60)
   
   # 限制数量
   search_logs("payment", limit=5)
   ```

3. 测试脱敏功能：
   - 在日志中加入密码、token
   - 验证是否被脱敏

4. 完成工具定义：
   - `tools/tool_definitions.py`
   - 运行并查看 JSON 输出

**验证**：
- 50 条日志数据
- 所有参数组合都测试通过
- 脱敏功能正常

### Level 3: 进阶任务（1 小时）

**任务**：
1. 添加参数校验（Pydantic）：
   ```python
   from pydantic import BaseModel, Field
   
   class SearchLogsParams(BaseModel):
       service: str = Field(..., pattern="^(payment|order|user|recommendation)$")
       level: str = Field("ERROR", pattern="^(ERROR|WARN|INFO)$")
       time_range: Optional[int] = Field(None, ge=1, le=1440)
       limit: int = Field(10, ge=1, le=100)
   
   def search_logs_validated(**kwargs):
       params = SearchLogsParams(**kwargs)
       return search_logs(**params.dict())
   ```

2. 添加性能测试：
   - 创建 1000 条日志
   - 测试查询耗时
   - 确保 < 100ms

3. 添加单元测试：
   ```python
   # tests/test_log_search.py
   def test_search_logs():
       logs = search_logs("payment", limit=5)
       assert len(logs) <= 5
       assert all(log['service'] == 'payment' for log in logs)
   
   def test_redact_sensitive():
       msg = "password=secret123"
       redacted = _redact_sensitive(msg)
       assert "secret123" not in redacted
   ```

**验证**：
- Pydantic 校验通过
- 性能测试 < 100ms
- 单元测试全部通过

## 🐛 常见问题

### Q1: 找不到日志文件

**问题**：
```
FileNotFoundError: data/sample_logs.jsonl
```

**解决**：
1. 检查目录结构
2. 使用绝对路径：`Path(__file__).parent.parent / "data" / "sample_logs.jsonl"`
3. 或返回模拟数据（`_generate_mock_logs`）

### Q2: 脱敏规则太简单

**问题**：复杂格式的敏感信息没被脱敏

**解决**：
1. 添加更多正则模式
2. 使用专业脱敏库（如 `scrubadub`）
3. 在数据源头就不记录敏感信息

### Q3: 查询太慢

**问题**：查询 1000 条日志要 5 秒

**解决**：
1. 添加索引（数据库）
2. 使用专业日志系统（Elasticsearch）
3. 限制查询范围（时间、数量）
4. 缓存常见查询

### Q4: 如何连接真实日志系统？

**答案**：
```python
# Elasticsearch 示例
from elasticsearch import Elasticsearch

def search_logs_es(service, level="ERROR"):
    es = Elasticsearch(["http://localhost:9200"])
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"service": service}},
                    {"term": {"level": level}}
                ]
            }
        },
        "size": 100
    }
    
    result = es.search(index="logs", body=query)
    return [hit['_source'] for hit in result['hits']['hits']]
```

## ✅ 完成检查清单

概念理解：
- [ ] 知道什么是工具（Tool）
- [ ] 理解只读工具 vs 写入工具
- [ ] 知道工具定义的三要素
- [ ] 理解工具的安全边界

实践检查：
- [ ] 实现了 search_logs 函数
- [ ] 创建了示例日志数据
- [ ] 实现了脱敏功能
- [ ] 定义了工具描述（Tool Definition）
- [ ] 测试了各种参数组合

## 📚 延伸阅读（可选）

**OpenAI Function Calling**：
- https://platform.openai.com/docs/guides/function-calling

**工具设计最佳实践**：
- https://python.langchain.com/docs/modules/tools/

**日志脱敏**：
- https://github.com/LeapBeyond/scrubadub

## 🎯 明天预告

**Day 4: Tool-Calling Loop（工具调用循环）**

今天我们有了工具，但还是手动调用：
```python
logs = search_logs("payment")  # 手动
```

明天你会学习：
- LLM 如何"主动决定"调用工具
- 完整的调用循环流程
- 如何把工具结果返回给 LLM
- 为什么需要限制调用次数

明天是关键的一天，会把 Day 1-3 的内容串起来！

休息一下，明天见！🚀
