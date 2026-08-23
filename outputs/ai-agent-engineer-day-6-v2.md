# Day 6 - 调用轨迹管理

**预计学习时间**: 2 小时

## 🎯 学习目标

学完今天，你将：
- 理解调用轨迹的作用
- 掌握完整的轨迹记录系统
- 能审计和调试 Agent 行为
- 知道如何限制调用防止滥用

## 📖 核心概念

### 1. 为什么需要调用轨迹？

**问题场景**：

```python
用户: "分析支付故障"
Agent: "判断为 P0，建议重启服务"

问题：
- Agent 查了什么日志？
- 调用了几次工具？
- 为什么判断为 P0？
- 如果出错，怎么调试？
```

**有了轨迹**：

```
调用轨迹:
1. [10:30:00] search_logs(payment, ERROR) → 35 条错误
2. [10:30:02] search_runbooks(P0, availability) → 支付 5xx 处理

依据：
- 日志显示数据库超时 35 次
- 匹配到标准处理流程
- 判断为 P0
```

**作用**：
- ✅ **审计**：记录所有操作
- ✅ **调试**：出错时追溯
- ✅ **成本控制**：限制调用次数
- ✅ **性能分析**：找到瓶颈

### 2. 轨迹应该记录什么？

**完整轨迹**：

```python
{
    "trace_id": "trace_12345",
    "user_query": "支付服务报错",
    "start_time": "2024-01-20T10:30:00",
    "end_time": "2024-01-20T10:30:05",
    "duration_ms": 5000,
    "tool_calls": [
        {
            "call_id": "call_1",
            "tool_name": "search_logs",
            "arguments": {"service": "payment", "level": "ERROR"},
            "result_summary": "35 条错误日志",
            "duration_ms": 150,
            "success": true,
            "timestamp": "2024-01-20T10:30:01"
        },
        {
            "call_id": "call_2",
            "tool_name": "search_runbooks",
            "arguments": {"description": "支付 5xx", "severity": "P0"},
            "result_summary": "1 个 Runbook",
            "duration_ms": 50,
            "success": true,
            "timestamp": "2024-01-20T10:30:02"
        }
    ],
    "final_result": {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": true
    },
    "total_cost": {
        "llm_calls": 2,
        "input_tokens": 1500,
        "output_tokens": 500
    }
}
```

### 3. 调用次数限制

**为什么限制？**

```python
# 场景 1: 无限循环
LLM 不停调用工具 → 成本失控 → 账单爆炸

# 场景 2: 性能问题
调用太多次 → 响应超时 → 用户等不及

# 场景 3: 滥用
恶意用户 → 故意触发大量调用 → DoS 攻击
```

**限制策略**：

```python
# 1. 单个工具限制
MAX_CALLS_PER_TOOL = 2

# 2. 总调用次数限制
MAX_TOTAL_CALLS = 5

# 3. 超时限制
MAX_DURATION_SECONDS = 30

# 4. Token 限制
MAX_TOKENS_PER_REQUEST = 10000
```

## 🔍 完整示例

Day 4 已经实现了基础版 TraceManager，今天完善它：

### 完善 TraceManager

```python
# trace_manager.py（完整版）
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class ToolCall:
    """单次工具调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str]
    duration_ms: float
    timestamp: str
    call_number: int  # 该工具的第几次调用

class TraceManager:
    """
    调用轨迹管理器
    
    功能：
    - 记录所有工具调用
    - 限制调用次数
    - 生成调用报告
    - 保存轨迹到文件
    """
    
    def __init__(
        self,
        max_calls_per_tool: int = 2,
        max_total_calls: int = 5,
        max_duration_seconds: int = 30
    ):
        self.max_calls_per_tool = max_calls_per_tool
        self.max_total_calls = max_total_calls
        self.max_duration_seconds = max_duration_seconds
        
        self.trace_id = self._generate_trace_id()
        self.start_time = time.time()
        self.tool_calls: List[ToolCall] = []
    
    def _generate_trace_id(self) -> str:
        """生成唯一轨迹 ID"""
        import uuid
        return f"trace_{uuid.uuid4().hex[:8]}"
    
    def can_call(self, tool_name: str) -> bool:
        """
        检查是否可以调用工具
        
        检查：
        1. 单个工具调用次数
        2. 总调用次数
        3. 执行时间
        """
        # 检查单个工具次数
        tool_count = self._get_call_count(tool_name)
        if tool_count >= self.max_calls_per_tool:
            return False
        
        # 检查总调用次数
        if len(self.tool_calls) >= self.max_total_calls:
            return False
        
        # 检查执行时间
        elapsed = time.time() - self.start_time
        if elapsed > self.max_duration_seconds:
            return False
        
        return True
    
    def record_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """记录一次工具调用"""
        call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result if success else None,
            success=success,
            error=error,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
            call_number=self._get_call_count(tool_name) + 1
        )
        self.tool_calls.append(call)
    
    def _get_call_count(self, tool_name: str) -> int:
        """获取工具成功调用次数"""
        return sum(
            1 for call in self.tool_calls
            if call.tool_name == tool_name and call.success
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取调用摘要"""
        total = len(self.tool_calls)
        success = sum(1 for c in self.tool_calls if c.success)
        duration = (time.time() - self.start_time) * 1000
        
        by_tool = {}
        for call in self.tool_calls:
            tool = call.tool_name
            if tool not in by_tool:
                by_tool[tool] = {
                    "total": 0,
                    "success": 0,
                    "avg_duration_ms": 0,
                    "total_duration_ms": 0
                }
            by_tool[tool]["total"] += 1
            by_tool[tool]["total_duration_ms"] += call.duration_ms
            if call.success:
                by_tool[tool]["success"] += 1
        
        # 计算平均耗时
        for stats in by_tool.values():
            if stats["total"] > 0:
                stats["avg_duration_ms"] = round(
                    stats["total_duration_ms"] / stats["total"],
                    2
                )
        
        return {
            "trace_id": self.trace_id,
            "total_calls": total,
            "successful_calls": success,
            "failed_calls": total - success,
            "total_duration_ms": round(duration, 2),
            "by_tool": by_tool
        }
    
    def save_to_file(self, directory: str = "traces"):
        """保存轨迹到文件"""
        Path(directory).mkdir(exist_ok=True)
        
        filepath = Path(directory) / f"{self.trace_id}.json"
        
        data = {
            **self.get_summary(),
            "calls": [
                {
                    "tool_name": call.tool_name,
                    "arguments": call.arguments,
                    "success": call.success,
                    "error": call.error,
                    "duration_ms": call.duration_ms,
                    "timestamp": call.timestamp,
                    "call_number": call.call_number
                }
                for call in self.tool_calls
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def print_summary(self):
        """打印调用摘要"""
        summary = self.get_summary()
        
        print(f"\n{'='*60}")
        print(f"调用轨迹: {summary['trace_id']}")
        print(f"{'='*60}")
        print(f"总调用: {summary['total_calls']}")
        print(f"成功: {summary['successful_calls']}")
        print(f"失败: {summary['failed_calls']}")
        print(f"总耗时: {summary['total_duration_ms']} ms")
        
        print("\n按工具统计:")
        for tool, stats in summary['by_tool'].items():
            print(f"  {tool}:")
            print(f"    调用: {stats['success']}/{stats['total']}")
            print(f"    平均耗时: {stats['avg_duration_ms']} ms")
        
        print("\n详细调用:")
        for i, call in enumerate(self.tool_calls, 1):
            status = "✓" if call.success else "✗"
            print(f"  {i}. {status} {call.tool_name} #{call.call_number}")
            print(f"     参数: {call.arguments}")
            print(f"     耗时: {call.duration_ms} ms")
            if not call.success:
                print(f"     错误: {call.error}")

# 测试
if __name__ == "__main__":
    trace = TraceManager(max_calls_per_tool=2)
    
    # 模拟调用
    trace.record_call(
        "search_logs",
        {"service": "payment"},
        [{"message": "error 1"}, {"message": "error 2"}],
        150.5,
        success=True
    )
    
    trace.record_call(
        "search_runbooks",
        {"description": "payment 5xx"},
        [{"title": "Payment 5xx handling"}],
        50.2,
        success=True
    )
    
    # 尝试第三次调用 search_logs
    if trace.can_call("search_logs"):
        print("✓ 可以调用")
        trace.record_call(
            "search_logs",
            {"service": "order"},
            [{"message": "error 3"}],
            120.0,
            success=True
        )
    else:
        print("✗ search_logs 调用次数已达上限")
    
    # 打印摘要
    trace.print_summary()
    
    # 保存到文件
    filepath = trace.save_to_file()
    print(f"\n✓ 轨迹已保存: {filepath}")
```

**运行测试**：
```bash
python trace_manager.py
```

## 💪 动手练习

### Level 1: 最低完成线（30 分钟）

**任务**：
- [ ] 完善 TraceManager
- [ ] 测试调用次数限制
- [ ] 保存轨迹到文件

**验证**：调用次数限制生效

### Level 2: 标准任务（1 小时）

**任务**：
1. 集成到 Agent（Day 4 的代码）
2. 运行完整流程，生成轨迹文件
3. 分析轨迹，找出性能瓶颈

**验证**：完整的轨迹文件

### Level 3: 进阶任务（30 分钟）

**任务**：
1. 添加成本估算：
   ```python
   def estimate_cost(self) -> float:
       """估算 API 调用成本"""
       cost = 0
       for call in self.tool_calls:
           # 假设每次调用 0.01 元
           cost += 0.01
       return cost
   ```

2. 添加轨迹可视化（HTML）

**验证**：成本估算、可视化

## ✅ 完成检查清单

- [ ] 理解轨迹的作用
- [ ] 实现了完整的 TraceManager
- [ ] 测试了调用次数限制
- [ ] 能保存和分析轨迹

## 🎯 明天预告

**Day 7: 第一周总结与集成**

前 6 天学了很多独立模块，明天把它们串起来：
- 完整的故障分析 Agent
- 从输入到输出的全流程
- 第一周作业

明天是第一周的收官之作！🚀
