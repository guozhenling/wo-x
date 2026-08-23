# Day 4 - Tool-Calling Loop（工具调用循环）

**预计学习时间**: 3 小时

## 🎯 学习目标

学完今天，你将：
- 理解完整的工具调用循环流程
- 掌握 LLM 如何主动决定调用工具
- 能实现多轮对话（带工具调用）
- 知道如何限制调用次数防止无限循环

## 📖 核心概念

### 1. 什么是 Tool-Calling Loop？

**目前的问题**：工具和 LLM 是分离的

```python
# Day 1-2: LLM 分类
result = classifier.classify("支付报错")

# Day 3: 手动调用工具
logs = search_logs("payment")

# 问题：LLM 不知道有工具，只能瞎猜
```

**Tool-Calling Loop**：LLM 能主动决定并调用工具

```
用户问题："支付服务为什么报错？"
    ↓
[Round 1] LLM 分析
    ↓
LLM: "我需要查看支付服务的日志"
    ↓
    tool_call: search_logs(service="payment", level="ERROR")
    ↓
[执行工具] Python 查询日志
    ↓
    返回: [{timestamp: ..., message: "DB timeout"}, ...]
    ↓
[Round 2] LLM 基于工具结果分析
    ↓
LLM: "根据日志，发现数据库超时错误 35 条，判断为 P0..."
```

**类比你熟悉的场景**：

**人类助理**：
```
你: "帮我查一下昨天的销售数据"
助理: "我去查一下..." [查数据库]
助理: "昨天销售额 100 万，同比增长 20%"
```

**Agent**：
```
用户: "支付服务为什么报错？"
LLM: "让我查一下日志..." [调用 search_logs]
LLM: "根据日志，发现 5xx 错误..."
```

### 2. 完整流程解析

**核心概念**：Tool-Calling 是**多轮对话**

```python
# Round 1: 用户提问 + LLM 决策
messages = [
    {"role": "user", "content": "支付服务为什么报错？"}
]

response = llm.chat(messages, tools=[search_logs_def])

# LLM 返回:
{
    "role": "assistant",
    "content": null,  # 没有文字回复
    "tool_calls": [{
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "search_logs",
            "arguments": '{"service": "payment", "level": "ERROR"}'
        }
    }]
}
```

```python
# 执行工具
tool_result = search_logs("payment", "ERROR")
# 返回: [{"timestamp": "...", "message": "DB timeout"}, ...]
```

```python
# Round 2: 工具结果 + LLM 分析
messages.append({
    "role": "assistant",
    "tool_calls": [...]  # 上面的 tool_calls
})

messages.append({
    "role": "tool",
    "tool_call_id": "call_123",
    "content": json.dumps(tool_result)
})

final_response = llm.chat(messages)

# LLM 返回:
{
    "role": "assistant",
    "content": "根据日志分析，发现数据库超时错误..."
}
```

**关键点**：
1. **LLM 不能直接运行 Python**，只能"请求"工具
2. **你的代码负责执行**工具并返回结果
3. **消息历史必须完整**：user → assistant(tool_calls) → tool → assistant

### 3. 消息格式详解

**OpenAI 消息格式**：

```python
messages = [
    # 1. 用户消息
    {
        "role": "user",
        "content": "支付服务为什么报错？"
    },
    
    # 2. Assistant 的工具调用
    {
        "role": "assistant",
        "content": null,  # 可选：描述性文字
        "tool_calls": [{
            "id": "call_abc123",  # 唯一标识
            "type": "function",
            "function": {
                "name": "search_logs",
                "arguments": '{"service": "payment"}'  # JSON 字符串
            }
        }]
    },
    
    # 3. 工具返回结果
    {
        "role": "tool",
        "tool_call_id": "call_abc123",  # 对应上面的 id
        "content": '[{"timestamp": "...", "message": "..."}]'  # JSON 字符串
    },
    
    # 4. Assistant 的最终回复
    {
        "role": "assistant",
        "content": "根据日志，发现..."
    }
]
```

**为什么要这么设计？**
- **tool_call_id**：关联请求和结果（可能有多个并发工具调用）
- **JSON 字符串**：统一格式，便于传输
- **完整历史**：LLM 需要看到完整对话才能理解上下文

### 4. 为什么需要限制调用次数？

**问题场景**：无限循环

```python
用户: "查一下所有服务的状态"
  ↓
LLM: 调用 search_logs("payment")
  ↓
LLM: "还需要查 order" → 调用 search_logs("order")
  ↓
LLM: "还需要查 user" → 调用 search_logs("user")
  ↓
LLM: "还需要查 recommendation" → ...
  ↓
无限循环！
```

**解决方案**：限制调用次数

```python
MAX_TOOL_CALLS = 2  # 每个工具最多调用 2 次

if tool_call_count[tool_name] >= MAX_TOOL_CALLS:
    return "证据不足，无法判断"
```

**合理的限制**：
- **单个工具**：最多 2 次（第一次查，第二次补充）
- **总调用次数**：最多 5 次（防止跨工具循环）
- **超时时间**：30 秒（防止卡住）

### 5. 错误处理

**可能的错误**：

❌ **错误 1：JSON 解析失败**
```python
arguments = '{"service": "payment"'  # 缺少 }
json.loads(arguments)  # JSONDecodeError
```

✅ **处理**：
```python
try:
    args = json.loads(tool_call.function.arguments)
except json.JSONDecodeError:
    return "参数格式错误，无法调用工具"
```

❌ **错误 2：参数不合法**
```python
search_logs(service="unknown_service")  # 不存在的服务
```

✅ **处理**：
```python
from pydantic import ValidationError

try:
    params = SearchLogsParams(**args)
    result = search_logs(**params.dict())
except ValidationError as e:
    return f"参数校验失败: {e}"
```

❌ **错误 3：工具执行失败**
```python
def search_logs(...):
    raise DatabaseConnectionError()  # 数据库挂了
```

✅ **处理**：
```python
try:
    result = execute_tool(tool_name, args)
except Exception as e:
    logging.error(f"工具执行失败: {e}")
    return "工具执行失败，请稍后重试"
```

## 🔍 完整示例

让我们实现完整的 Tool-Calling Loop：

### 步骤 1: 实现 Agent

```python
# agent.py
import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from tools.tool_definitions import get_all_tool_definitions
from tools.executor import execute_tool

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncidentAgent:
    """
    故障分析 Agent（带工具调用）
    
    功能：
    - 接收故障描述
    - 决定是否需要查日志
    - 调用工具获取证据
    - 基于证据分析
    """
    
    def __init__(self, max_tool_calls: int = 2):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.max_tool_calls = max_tool_calls
        self.tool_call_count = {}
    
    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """
        分析故障
        
        Args:
            incident_description: 故障描述
            
        Returns:
            分析结果，包含：
            - analysis: 最终分析
            - tool_calls_made: 调用的工具列表
            - messages: 完整对话历史
        """
        self.tool_call_count.clear()
        
        # 构造消息
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "user",
                "content": f"分析以下故障：\n\n{incident_description}"
            }
        ]
        
        tool_calls_made = []
        max_rounds = 5  # 最多 5 轮对话
        
        for round_num in range(max_rounds):
            logger.info(f"\n{'='*60}")
            logger.info(f"Round {round_num + 1}")
            logger.info(f"{'='*60}")
            
            # 调用 LLM
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=get_all_tool_definitions(),
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            # 检查是否有工具调用
            if not message.tool_calls:
                # 没有工具调用，返回最终答案
                logger.info("✓ 得到最终答案")
                return {
                    "analysis": message.content,
                    "tool_calls_made": tool_calls_made,
                    "messages": messages + [message.model_dump()]
                }
            
            # 有工具调用
            logger.info(f"→ LLM 请求调用 {len(message.tool_calls)} 个工具")
            
            # 添加 assistant 消息
            messages.append(message.model_dump())
            
            # 执行每个工具调用
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
                
                logger.info(f"  工具: {tool_name}")
                logger.info(f"  参数: {tool_args_str}")
                
                # 检查调用次数限制
                if self._is_tool_call_limit_reached(tool_name):
                    logger.warning(f"  ⚠️  {tool_name} 调用次数达到上限")
                    tool_result = {
                        "error": f"工具 {tool_name} 调用次数超限，证据不足"
                    }
                else:
                    # 执行工具
                    tool_result = self._execute_tool_safe(
                        tool_name,
                        tool_args_str
                    )
                    
                    # 记录调用
                    tool_calls_made.append({
                        "tool": tool_name,
                        "arguments": tool_args_str,
                        "result_summary": f"{len(tool_result)} 条记录" if isinstance(tool_result, list) else "执行成功"
                    })
                
                # 添加工具结果消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
                
                logger.info(f"  ✓ 工具执行完成")
        
        # 超过最大轮数
        logger.warning("⚠️  达到最大轮数，返回当前结果")
        return {
            "analysis": "分析超时，建议人工介入",
            "tool_calls_made": tool_calls_made,
            "messages": messages
        }
    
    def _get_system_prompt(self) -> str:
        """系统提示词"""
        return """你是一个故障分析专家。

你的任务是分析故障并给出建议。

可用工具：
- search_logs: 搜索服务日志

分析流程：
1. 理解故障描述
2. 如果需要更多证据，调用 search_logs 查看日志
3. 基于证据给出分析结果

输出格式：
- 故障严重程度: P0/P1/P2/P3
- 故障类别: availability/latency/database/deployment
- 是否需要人工审核: true/false
- 分析依据: 基于日志的具体证据

注意：
- 最多调用 2 次工具
- 如果证据不足，明确说明
- 基于实际日志数据，不要猜测"""
    
    def _is_tool_call_limit_reached(self, tool_name: str) -> bool:
        """检查工具调用次数是否达到上限"""
        count = self.tool_call_count.get(tool_name, 0)
        return count >= self.max_tool_calls
    
    def _execute_tool_safe(
        self,
        tool_name: str,
        arguments_str: str
    ) -> Any:
        """
        安全执行工具
        
        处理所有可能的异常
        """
        try:
            # 解析参数
            arguments = json.loads(arguments_str)
            
            # 执行工具
            result = execute_tool(tool_name, arguments)
            
            # 更新调用计数
            self.tool_call_count[tool_name] = self.tool_call_count.get(tool_name, 0) + 1
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return {"error": f"参数格式错误: {e}"}
            
        except ValueError as e:
            logger.error(f"参数校验失败: {e}")
            return {"error": f"参数不合法: {e}"}
            
        except Exception as e:
            logger.error(f"工具执行异常: {e}")
            return {"error": f"工具执行失败: {e}"}

# 测试
if __name__ == "__main__":
    agent = IncidentAgent()
    
    print("=" * 80)
    print("测试 1: 需要查日志的故障")
    print("=" * 80)
    
    result = agent.analyze("支付服务报错，用户无法完成支付")
    
    print("\n" + "=" * 80)
    print("分析结果")
    print("=" * 80)
    print(result['analysis'])
    
    print("\n工具调用记录:")
    for call in result['tool_calls_made']:
        print(f"  - {call['tool']}: {call['result_summary']}")
    
    print("\n" + "=" * 80)
    print("测试 2: 不需要查日志的故障")
    print("=" * 80)
    
    result2 = agent.analyze("推荐系统响应慢，但功能正常")
    
    print("\n" + "=" * 80)
    print("分析结果")
    print("=" * 80)
    print(result2['analysis'])
    
    if result2['tool_calls_made']:
        print("\n工具调用记录:")
        for call in result2['tool_calls_made']:
            print(f"  - {call['tool']}: {call['result_summary']}")
    else:
        print("\n✓ 无需调用工具")
```

**运行测试**：
```bash
python agent.py
```

### 步骤 2: 添加轨迹记录

```python
# trace_manager.py
from typing import List, Dict, Any
from datetime import datetime
import json

class TraceManager:
    """
    调用轨迹管理器
    
    功能：
    - 记录所有工具调用
    - 限制调用次数
    - 生成调用报告
    """
    
    def __init__(self, max_calls_per_tool: int = 2):
        self.traces: List[Dict[str, Any]] = []
        self.max_calls_per_tool = max_calls_per_tool
    
    def record_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool = True,
        error: Optional[str] = None
    ):
        """记录一次工具调用"""
        self.traces.append({
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result if success else None,
            "success": success,
            "error": error,
            "call_number": self._get_call_count(tool_name) + 1
        })
    
    def can_call(self, tool_name: str) -> bool:
        """检查是否可以调用工具"""
        return self._get_call_count(tool_name) < self.max_calls_per_tool
    
    def _get_call_count(self, tool_name: str) -> int:
        """获取工具调用次数"""
        return sum(
            1 for trace in self.traces
            if trace['tool_name'] == tool_name and trace['success']
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取调用摘要"""
        total = len(self.traces)
        success = sum(1 for t in self.traces if t['success'])
        
        by_tool = {}
        for trace in self.traces:
            tool = trace['tool_name']
            if tool not in by_tool:
                by_tool[tool] = {"total": 0, "success": 0}
            by_tool[tool]["total"] += 1
            if trace['success']:
                by_tool[tool]["success"] += 1
        
        return {
            "total_calls": total,
            "successful_calls": success,
            "failed_calls": total - success,
            "by_tool": by_tool,
            "traces": self.traces
        }
    
    def print_summary(self):
        """打印调用摘要"""
        summary = self.get_summary()
        
        print("\n调用轨迹摘要")
        print("=" * 60)
        print(f"总调用次数: {summary['total_calls']}")
        print(f"成功: {summary['successful_calls']}")
        print(f"失败: {summary['failed_calls']}")
        
        print("\n按工具统计:")
        for tool, stats in summary['by_tool'].items():
            print(f"  {tool}: {stats['success']}/{stats['total']} 成功")
        
        print("\n详细轨迹:")
        for i, trace in enumerate(summary['traces'], 1):
            status = "✓" if trace['success'] else "✗"
            print(f"  {i}. {status} {trace['tool_name']} - {trace['timestamp']}")
            if not trace['success']:
                print(f"     错误: {trace['error']}")

# 测试
if __name__ == "__main__":
    trace = TraceManager(max_calls_per_tool=2)
    
    # 模拟调用
    trace.record_call(
        "search_logs",
        {"service": "payment", "level": "ERROR"},
        [{"message": "DB timeout"}],
        success=True
    )
    
    trace.record_call(
        "search_logs",
        {"service": "payment", "level": "WARN"},
        [{"message": "Slow query"}],
        success=True
    )
    
    # 第三次调用（应该被拒绝）
    if not trace.can_call("search_logs"):
        print("⚠️  search_logs 调用次数已达上限")
    
    trace.print_summary()
```

**运行测试**：
```bash
python trace_manager.py
```

### 步骤 3: 集成 Agent + TraceManager

```python
# agent_with_trace.py
import os
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from tools.tool_definitions import get_all_tool_definitions
from tools.executor import execute_tool
from trace_manager import TraceManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncidentAgentV2:
    """带轨迹管理的 Agent"""
    
    def __init__(self, max_tool_calls: int = 2):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.trace = TraceManager(max_calls_per_tool=max_tool_calls)
    
    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """分析故障（带轨迹记录）"""
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"分析: {incident_description}"}
        ]
        
        for round_num in range(5):
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=get_all_tool_definitions(),
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            if not message.tool_calls:
                # 最终答案
                return {
                    "analysis": message.content,
                    "trace_summary": self.trace.get_summary()
                }
            
            # 处理工具调用
            messages.append(message.model_dump())
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
                
                # 检查调用限制
                if not self.trace.can_call(tool_name):
                    logger.warning(f"⚠️  {tool_name} 调用次数超限")
                    tool_result = {"error": "调用次数超限"}
                    self.trace.record_call(
                        tool_name,
                        json.loads(tool_args_str),
                        None,
                        success=False,
                        error="调用次数超限"
                    )
                else:
                    # 执行工具
                    try:
                        arguments = json.loads(tool_args_str)
                        tool_result = execute_tool(tool_name, arguments)
                        
                        # 记录成功
                        self.trace.record_call(
                            tool_name,
                            arguments,
                            tool_result,
                            success=True
                        )
                    except Exception as e:
                        logger.error(f"工具执行失败: {e}")
                        tool_result = {"error": str(e)}
                        self.trace.record_call(
                            tool_name,
                            json.loads(tool_args_str) if tool_args_str else {},
                            None,
                            success=False,
                            error=str(e)
                        )
                
                # 添加工具结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
        
        return {
            "analysis": "分析超时",
            "trace_summary": self.trace.get_summary()
        }
    
    def _get_system_prompt(self) -> str:
        return """你是故障分析专家。

可用工具：search_logs

分析流程：
1. 判断是否需要查日志
2. 如果需要，调用 search_logs
3. 基于日志给出分析

最多调用 2 次工具。"""

# 测试
if __name__ == "__main__":
    agent = IncidentAgentV2()
    
    result = agent.analyze("支付服务报错")
    
    print("\n分析结果:")
    print(result['analysis'])
    
    print("\n" + "=" * 60)
    agent.trace.print_summary()
```

**运行测试**：
```bash
python agent_with_trace.py
```

## 💪 动手练习

### Level 1: 最低完成线（1 小时）

**任务**：
- [ ] 完成 `agent.py`
- [ ] 运行测试，看到工具调用流程
- [ ] 理解消息格式（user → assistant → tool → assistant）

**验证**：能看到完整的工具调用循环

### Level 2: 标准任务（1 小时）

**任务**：
1. 测试 3 个场景：
   ```python
   # 场景 1: 需要查日志
   "支付服务报错，用户无法支付"
   
   # 场景 2: 不需要查日志（信息充分）
   "推荐系统 P99 延迟 2 秒，但功能正常"
   
   # 场景 3: 多次查询
   "多个服务报错，请分析"
   ```

2. 对每个场景记录：
   - LLM 是否调用工具
   - 调用了几次
   - 最终分析是否合理

3. 实现 TraceManager

**验证**：
- 3 个场景都测试通过
- TraceManager 正常工作

### Level 3: 进阶任务（1 小时）

**任务**：
1. 添加测试：验证调用次数限制
   ```python
   def test_tool_call_limit():
       agent = IncidentAgent(max_tool_calls=2)
       # 构造会触发多次调用的场景
       result = agent.analyze("...")
       # 验证不超过 2 次
   ```

2. 添加超时机制：
   ```python
   import signal
   
   def with_timeout(seconds):
       def decorator(func):
           def wrapper(*args, **kwargs):
               signal.alarm(seconds)
               try:
                   return func(*args, **kwargs)
               finally:
                   signal.alarm(0)
           return wrapper
       return decorator
   ```

3. 保存调用轨迹到文件：
   ```python
   trace.save_to_file("traces/trace_001.json")
   ```

**验证**：
- 调用次数限制生效
- 超时机制工作
- 轨迹文件可读

## 🐛 常见问题

### Q1: LLM 不调用工具

**问题**：LLM 直接猜测，不查日志

**解决**：
1. 在 System Prompt 中明确说明"必须查日志"
2. 提供工具使用示例
3. 降低 temperature（减少随机性）

### Q2: 工具调用无限循环

**问题**：一直调用工具，不给最终答案

**解决**：
1. 限制最大轮数（5 轮）
2. 限制每个工具调用次数（2 次）
3. 在 Prompt 中说明"最多调用 N 次"

### Q3: 工具返回结果太大

**问题**：日志返回 1000 条，超过 token 限制

**解决**：
1. 在工具中限制返回条数（最多 100 条）
2. 只返回关键字段（timestamp, message）
3. 总结日志而不是原样返回

### Q4: 如何调试消息历史？

**答案**：
```python
# 打印完整消息历史
for i, msg in enumerate(messages):
    print(f"\n[{i}] Role: {msg['role']}")
    if 'content' in msg:
        print(f"Content: {msg['content'][:100]}...")
    if 'tool_calls' in msg:
        print(f"Tool calls: {len(msg['tool_calls'])}")
```

## ✅ 完成检查清单

概念理解：
- [ ] 理解 Tool-Calling Loop 的完整流程
- [ ] 知道消息格式（4 种 role）
- [ ] 理解为什么需要限制调用次数
- [ ] 知道如何处理工具调用错误

实践检查：
- [ ] 实现了 IncidentAgent
- [ ] 能正确处理工具调用
- [ ] 实现了 TraceManager
- [ ] 测试了多个场景
- [ ] 验证了调用次数限制

## 📚 延伸阅读（可选）

**OpenAI Function Calling 文档**：
- https://platform.openai.com/docs/guides/function-calling

**LangChain Agent**：
- https://python.langchain.com/docs/modules/agents/

## 🎯 明天预告

**Day 5: 第二个工具 - Runbook 检索**

今天 Agent 能查日志了，但只有"问题证据"，没有"解决方案"。

明天你会学习：
- 如何实现 Runbook 检索（不用向量数据库）
- 基于关键词的简单匹配
- 如何给 Agent 提供处理步骤

有了 Runbook，Agent 就能从"发现问题"进化到"推荐方案"！

休息一下，明天见！🚀
