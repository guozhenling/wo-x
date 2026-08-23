# 日志搜索工具

基于服务名和关键字的日志搜索工具，带有完整的参数校验和超时保护。

## 📁 文件结构

```
.
├── data/
│   └── logs.jsonl          # 日志数据（JSONL 格式）
├── src/
│   └── log_search.py       # 日志搜索工具实现
├── tests/
│   └── test_log_search.py  # 完整测试用例（27个）
└── examples/
    └── demo_log_search.py  # 使用示例
```

## 🚀 快速开始

### 基础搜索

```python
from src.log_search import search_logs

# 查询 payment 服务的日志
result = search_logs(service="payment", limit=10)
print(f"找到 {result.total} 条日志")

for log in result.logs:
    print(f"[{log.level}] {log.message}")
```

### 关键字搜索

```python
# 查询包含 "timeout" 的日志
result = search_logs(service="payment", keyword="timeout", limit=10)

for log in result.logs:
    print(f"{log.timestamp} - {log.message}")
    print(f"trace_id: {log.trace_id}")
```

## 📊 数据模型

### SearchLogsInput（输入参数）

```python
{
    "service": str,           # 服务名，不能为空
    "keyword": str | None,    # 关键字（可选），最长100字符
    "limit": int              # 返回结果数量，范围 1-20，默认10
}
```

### SearchLogsResult（搜索结果）

```python
{
    "logs": List[LogEntry],   # 日志列表
    "total": int,             # 匹配的日志总数
    "search_time_ms": float   # 搜索耗时（毫秒）
}
```

### LogEntry（单条日志）

```python
{
    "timestamp": str,         # 时间戳
    "service": str,           # 服务名
    "level": str,             # 日志级别（ERROR/WARN/INFO）
    "message": str,           # 日志消息
    "trace_id": str           # Trace ID
}
```

## 🛡️ 参数校验

工具内置严格的参数校验，保证输入合法性：

| 参数 | 校验规则 | 错误提示 |
|------|---------|---------|
| service | 不能为空或纯空格 | "服务名不能为空" |
| keyword | 最长100字符 | "关键字长度不能超过100字符" |
| limit | 必须在 1-20 之间 | "limit 不能超过20" / "limit 必须大于0" |

### 校验示例

```python
from pydantic import ValidationError

try:
    # 空服务名 - 会被拒绝
    result = search_logs(service="", limit=10)
except ValidationError as e:
    print(f"参数校验失败: {e}")

try:
    # limit 超过20 - 会被拒绝
    result = search_logs(service="payment", limit=25)
except ValidationError as e:
    print(f"参数校验失败: {e}")
```

## ⏱️ 超时保护

搜索操作有1秒超时保护，防止长时间阻塞：

```python
from src.log_search import LogSearchTool

# 自定义超时时间
tool = LogSearchTool(log_file_path="data/logs.jsonl", timeout_seconds=2.0)

try:
    result = tool.search(service="payment", limit=100)
except TimeoutError:
    print("搜索超时")
```

## 🧪 测试

运行完整测试套件（27个测试用例）：

```bash
pytest tests/test_log_search.py -v
```

### 测试覆盖

- ✅ 成功查询（带/不带关键字）
- ✅ 无结果场景
- ✅ 非法参数（空服务名、过长关键字、limit超限）
- ✅ limit 限制验证
- ✅ 大小写不敏感搜索
- ✅ 多服务查询
- ✅ 超时保护
- ✅ 参数化测试（7种参数组合）

**测试结果**: 27 passed in 0.08s ✅

## 📝 使用示例

运行完整演示：

```bash
python examples/demo_log_search.py
```

演示包含8个场景：
1. 基础搜索
2. 关键字搜索
3. 无结果场景
4. 参数校验错误
5. 超出限制错误
6. 多服务查询
7. 错误分析
8. Trace 搜索

## 🎯 功能特性

- **严格参数校验** - Pydantic 驱动的类型安全
- **超时保护** - 1秒默认超时，可配置
- **高性能** - 提前退出，搜索时间 < 1ms
- **大小写不敏感** - 关键字搜索自动忽略大小写
- **完整测试** - 27个测试用例，100%覆盖
- **类型安全** - 完整的类型标注和 Pydantic 模型

## 🔧 高级用法

### 自定义日志文件路径

```python
from src.log_search import LogSearchTool

tool = LogSearchTool(
    log_file_path="custom/path/logs.jsonl",
    timeout_seconds=2.0
)

result = tool.search(service="payment", limit=10)
```

### 错误日志分析

```python
# 查询所有 payment 服务的日志
result = search_logs(service="payment", limit=20)

# 过滤 ERROR 级别
error_logs = [log for log in result.logs if log.level == "ERROR"]

print(f"发现 {len(error_logs)} 条错误日志")
for log in error_logs:
    print(f"  {log.message}")
```

### Trace 追踪

```python
# 通过关键字找到相关 trace
result = search_logs(service="payment", keyword="gateway", limit=5)

trace_ids = [log.trace_id for log in result.logs]
print(f"相关 trace: {trace_ids}")
```

## 📦 依赖

- Python 3.10+
- Pydantic 2.x
- pytest 7.x（测试）

## 🔐 安全特性

- **输入校验** - 所有参数严格校验，防止注入
- **超时保护** - 防止恶意请求长时间占用资源
- **异常处理** - 完善的错误处理，不会因单条日志格式错误而中断

## 📈 性能指标

基于20条日志的测试数据集：

| 操作 | 平均耗时 | 说明 |
|------|---------|------|
| 无关键字搜索 | < 0.2ms | 服务名过滤 + limit 提前退出 |
| 关键字搜索 | < 0.1ms | 大小写不敏感全文匹配 |
| 无结果查询 | < 0.05ms | 快速遍历整个数据集 |

## 🚀 未来扩展

潜在功能扩展方向：

1. **时间范围过滤** - 支持按时间戳筛选
2. **日志级别过滤** - 支持按 ERROR/WARN/INFO 过滤
3. **正则表达式搜索** - 更强大的模式匹配
4. **聚合统计** - 错误分布、时间分布等
5. **多关键字搜索** - AND/OR 逻辑组合
6. **流式读取** - 支持大文件（GB级）日志

---

**版本**: v1.0  
**状态**: ✅ 生产就绪  
**测试覆盖**: 27/27 通过
