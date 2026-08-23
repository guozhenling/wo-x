# AI Agent 工程师：Day 1 启动任务

目标：在今天结束前，你能让模型稳定产出机器可校验的故障分类结果，并知道它与普通聊天机器人的区别。这是一个独立小练习，不要求你现在设计完整项目。

预计：2.5–3 小时。

## 今天的完成定义

**最低完成线**

- [ ] 建立一个 Python 虚拟环境，能调用一个 LLM API。
- [ ] 让模型把一条故障描述输出为约定的 JSON。

**标准任务**

- [ ] 为 3 条模拟故障报告手动检查结果。
- [ ] 用 Pydantic 校验模型输出；不合法时打印错误而不是继续运行。

**进阶任务**

- [ ] 为 10 条模拟故障报告写自动化断言。
- [ ] 记录至少 2 条失败样例及其修复手段。

## 要理解的最小模型

```text
用户请求 → 模型 →（可能的）工具调用 → 工具结果 → 模型 → 可校验结果
```

普通聊天机器人只生成文字。Agent 在受控边界内选择并调用工具；工程师的工作是定义边界、校验输入输出、处理失败，并用测试证明行为可信。

## 练习：故障分类器

输入是一段故障描述；输出必须满足：

```python
from typing import Literal
from pydantic import BaseModel

class IncidentTriage(BaseModel):
    severity: Literal["P0", "P1", "P2", "P3"]
    category: Literal["availability", "latency", "database", "deployment", "unknown"]
    needs_human_review: bool
    rationale: str
```

先不要加入日志、数据库或复杂 RAG。先掌握结构化输出；第 4 周再将它整合进完整作品。

### 验收样例

| 输入 | 期望关键字段 |
|---|---|
| `支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟` | `P0`, `availability`, `true` |
| `发布后订单查询 p99 从 200ms 升至 5s` | `P1`, `latency`, `true` |
| `凌晨批处理偶发死锁，已自动重试成功` | `P2`, `database`, `false` |

## 推荐实现顺序

1. 创建 `python -m venv .venv`，使用官方 Python SDK 发出最简单的一次请求。
2. 定义 `IncidentTriage` JSON Schema，并要求结构化输出。
3. 在应用代码中用 Pydantic 或 JSON Schema 再校验一次，绝不直接信任模型输出。
4. 为十条输入建立 fixture；断言枚举字段和人工升级逻辑。
5. 写 `failures.md`：模型何时输出空理由、误判严重性，怎样通过上下文、Schema 或规则修正。

## 复盘问题

1. 哪些判断交给模型，哪些必须由确定性规则兜底？
2. 如果这个结果触发了 PagerDuty，你会增加什么审批或阈值？
3. 当模型没有按 Schema 返回时，系统应重试、降级还是拒绝？为什么？

## 明天的入口

把“分类结果”作为输入，让 Agent 在只读的 `searchLogs` 和 `getMetrics` 两个模拟工具间选择；每个工具都必须有参数 Schema、超时和审计日志。
