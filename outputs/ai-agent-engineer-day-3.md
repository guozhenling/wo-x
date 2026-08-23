# AI Agent 工程师：Day 3 — 第一个受控工具

目标：把“查询日志”写成一个可校验、可测试、只读的 Python 工具。

预计：2.5–3 小时。

## 为什么今天要做工具

模型不会天然知道你的日志内容。Agent 的能力来自受控工具，而不是更长的 Prompt。

## 最低完成线

- [ ] 建立 10–20 行模拟日志数据。
- [ ] 实现 `search_logs(service, keyword)`。
- [ ] 返回匹配日志，不修改任何数据。

## 标准任务

1. 创建 `data/logs.jsonl`，包含时间、服务名、级别、消息和 trace ID。
2. 用 Pydantic 定义 `SearchLogsInput` 与 `SearchLogsResult`。
3. 工具只接收 `service`、`keyword`、`limit` 三个参数。
4. 校验：空服务名、过长关键字、`limit > 20` 都要拒绝。
5. 加入 1 秒超时保护或显式的超时接口设计。
6. 用 `pytest` 覆盖成功查询、无结果、非法参数、超出上限四种情况。

## 工具契约

```text
输入：明确、有限、可校验
输出：带来源、可追踪、可消费
副作用：无；只读
```

## 完成证明

- 一份小型日志 fixture。
- 工具函数及输入、输出 Schema。
- 至少 4 个通过的工具测试。

## 明天的入口

Day 4 让模型在需要证据时提出 `search_logs` 调用；Python 负责验证并执行它。
