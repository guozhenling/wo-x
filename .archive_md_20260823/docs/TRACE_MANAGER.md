# TraceManager 轨迹管理器

## 概述

TraceManager 提供完整的调用轨迹记录和工具调用次数限制功能，用于：
1. **防止无限循环** - 限制最多 2 次工具调用
2. **审计追踪** - 记录用户输入、工具请求、工具结果、最终答案
3. **故障排查** - 完整的调用链路分析
4. **成本控制** - 避免过度调用 API

## 核心功能

### 1. 工具调用次数限制

**限制**: 最多 2 次工具调用

**超过限制时**: 返回 "证据不足" 错误并记录轨迹

**典型场景**:
- 第 1 次: LLM 分类
- 第 2 次: Policy 引擎修正

```python
# 检查是否可以调用工具
if trace_manager.can_call_tool():
    # 执行工具调用
    trace_manager.record_tool_call(...)
else:
    # 已达上限
    raise ValueError("证据不足：已达最大工具调用次数限制")
```

### 2. 完整调用轨迹

每次分类都会记录：

```json
{
  "trace_id": "20260819_143022_123456",
  "timestamp": "2026-08-19T14:30:22.123456",
  "user_input": "支付接口错误率 35%",
  "tool_calls": [
    {
      "timestamp": "2026-08-19T14:30:22.234567",
      "tool_name": "llm_chat",
      "tool_input": {
        "message": "请对以下故障进行分类...",
        "system_prompt": "你是一个专业的故障分类助手...",
        "temperature": 0.3
      },
      "tool_output": "{\"severity\":\"P0\",\"category\":\"availability\",...}",
      "success": true,
      "error_message": null
    },
    {
      "timestamp": "2026-08-19T14:30:23.345678",
      "tool_name": "policy_engine",
      "tool_input": {
        "original": {"needs_human_review": false}
      },
      "tool_output": {
        "corrected": {"needs_human_review": true},
        "violations": [
          {
            "policy_name": "高优先级必须人工复核",
            "level": "CRITICAL",
            "message": "P0/P1 故障必须人工审核",
            "original_value": false,
            "corrected_value": true
          }
        ]
      },
      "success": true,
      "error_message": null
    }
  ],
  "final_answer": {
    "severity": "P0",
    "category": "availability",
    "needs_human_review": true,
    "rationale": "支付接口错误率 35%，直接影响收入..."
  },
  "status": "success",
  "error_message": null,
  "total_tool_calls": 2,
  "max_tool_calls_reached": true,
  "max_tool_calls_limit": 2
}
```

## 使用方法

### 基础用法

```python
from client import LLMClient
from incident_triage import IncidentClassifier

# 初始化（指定轨迹保存目录）
client = LLMClient()
classifier = IncidentClassifier(client, trace_dir="traces")

# 分类故障（自动记录轨迹）
result = classifier.classify("支付接口错误率 35%")

# 轨迹自动保存到 traces/trace_YYYYMMDD_HHMMSS_ffffff.json
```

### 查看轨迹

```python
import json
from pathlib import Path

# 读取轨迹文件
trace_file = "traces/trace_20260819_143022_123456.json"
with open(trace_file, 'r', encoding='utf-8') as f:
    trace = json.load(f)

# 分析轨迹
print(f"用户输入: {trace['user_input']}")
print(f"工具调用次数: {trace['total_tool_calls']}")
print(f"最终状态: {trace['status']}")

for call in trace['tool_calls']:
    print(f"  - {call['tool_name']}: {call['success']}")
```

## 轨迹状态

| 状态 | 说明 |
|------|------|
| `success` | 分类成功完成 |
| `insufficient_evidence` | 达到最大工具调用次数限制 |
| `error` | 发生错误（JSON 解析失败、校验失败等） |
| `in_progress` | 进行中（不应该出现在保存的文件中） |

## TraceManager API

### 核心方法

```python
class TraceManager:
    MAX_TOOL_CALLS = 2  # 最大工具调用次数

    def start_trace(self, user_input: str) -> str:
        """开始新的轨迹记录，返回 trace_id"""

    def can_call_tool(self) -> bool:
        """检查是否还能调用工具"""

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """记录工具调用，返回是否记录成功"""

    def finish_trace(
        self,
        final_answer: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """结束轨迹并保存，返回文件路径"""
```

## 应用场景

### 1. 审计和合规

```python
# 定期审查轨迹
for trace_file in Path("traces").glob("trace_*.json"):
    with open(trace_file) as f:
        trace = json.load(f)
    
    # 检查是否有高优先级故障未审核
    if trace['status'] == 'success':
        answer = trace['final_answer']
        if answer['severity'] in ['P0', 'P1'] and not answer['needs_human_review']:
            print(f"⚠️ 高优先级故障未标记审核: {trace['trace_id']}")
```

### 2. 故障排查

```python
# 分析失败的分类
failed_traces = []
for trace_file in Path("traces").glob("trace_*.json"):
    with open(trace_file) as f:
        trace = json.load(f)
    
    if trace['status'] == 'error':
        failed_traces.append(trace)

# 分析失败原因
for trace in failed_traces:
    print(f"失败原因: {trace['error_message']}")
    print(f"用户输入: {trace['user_input']}")
```

### 3. 性能分析

```python
# 统计工具调用次数分布
from collections import Counter

call_counts = []
for trace_file in Path("traces").glob("trace_*.json"):
    with open(trace_file) as f:
        trace = json.load(f)
    call_counts.append(trace['total_tool_calls'])

distribution = Counter(call_counts)
print(f"工具调用次数分布: {distribution}")
# 输出: Counter({1: 150, 2: 45, 0: 5})
```

### 4. Prompt 优化

```python
# 找出需要多次修正的案例
high_correction_traces = []

for trace_file in Path("traces").glob("trace_*.json"):
    with open(trace_file) as f:
        trace = json.load(f)
    
    policy_calls = [c for c in trace['tool_calls'] if c['tool_name'] == 'policy_engine']
    
    if policy_calls:
        violations = policy_calls[0]['tool_output'].get('violations', [])
        if len(violations) >= 2:
            high_correction_traces.append({
                'user_input': trace['user_input'],
                'violations': [v['policy_name'] for v in violations]
            })

# 分析哪些规则经常被触发，优化 Prompt
```

## 配置

### 修改最大调用次数

```python
# 在 trace_manager.py 中修改
class TraceManager:
    MAX_TOOL_CALLS = 3  # 改为 3 次
```

### 自定义保存目录

```python
classifier = IncidentClassifier(
    client,
    trace_dir="custom_traces"  # 自定义目录
)
```

## 最佳实践

1. **定期清理旧轨迹** - 避免磁盘占用过多
   ```bash
   # 删除 30 天前的轨迹
   find traces/ -name "trace_*.json" -mtime +30 -delete
   ```

2. **敏感信息脱敏** - 生产环境中可能需要脱敏
   ```python
   # 在记录前脱敏敏感信息
   def sanitize_input(text: str) -> str:
       # 移除敏感信息
       return re.sub(r'\d{16}', '****', text)  # 脱敏卡号
   ```

3. **监控轨迹质量** - 定期检查异常轨迹
   ```python
   # 监控证据不足的情况
   insufficient_count = sum(
       1 for f in Path("traces").glob("trace_*.json")
       if json.loads(f.read_text())['status'] == 'insufficient_evidence'
   )
   
   if insufficient_count > 10:
       alert("证据不足错误过多，检查系统配置")
   ```

4. **轨迹归档** - 长期存储到对象存储
   ```python
   # 按月归档
   import tarfile
   
   archive_name = f"traces_{datetime.now().strftime('%Y%m')}.tar.gz"
   with tarfile.open(archive_name, "w:gz") as tar:
       tar.add("traces/", arcname="traces")
   
   # 上传到 S3/OSS
   upload_to_s3(archive_name)
   ```

## 总结

TraceManager 通过 **限制调用次数** 和 **完整轨迹记录** 两个核心功能，提供：

✅ **可靠性** - 防止无限循环，快速失败  
✅ **可观测性** - 完整的调用链路  
✅ **可审计性** - 所有决策都有记录  
✅ **可优化性** - 基于数据改进系统
