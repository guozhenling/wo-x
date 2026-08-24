# 评测系统说明

## 📊 评测数据集

**位置**: `data/evaluation_dataset.jsonl`

**格式**:
```json
{
  "id": "eval_001",
  "description": "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
  "expected": {
    "severity": "P0",
    "category": "availability",
    "needs_human_review": false
  },
  "reason": "收入相关，高错误率"
}
```

**字段说明**:
- `id`: 评测案例唯一标识
- `description`: 故障描述（输入）
- `expected`: 期望的分类结果
  - `severity`: P0/P1/P2/P3
  - `category`: availability/latency/database/deployment/unknown
  - `needs_human_review`: true/false
- `reason`: 为什么这样分类（说明）

**当前数据集**: 20 个评测案例，覆盖：
- P0 案例: 4 个（支付、订单等核心功能）
- P1 案例: 8 个（核心服务延迟、数据库问题）
- P2 案例: 6 个（非核心服务、用户体验）
- P3 案例: 2 个（低影响、需观察）

---

## 🚀 运行评测

### 快速评测（前 5 个案例）
```bash
python scripts/evaluate.py --limit 5
```

### 完整评测（所有 20 个案例）
```bash
python scripts/evaluate.py
```

### 使用自定义数据集
```bash
python scripts/evaluate.py --dataset path/to/your_dataset.jsonl
```

---

## 📈 评测指标

评测脚本会计算以下准确率：

1. **严重程度准确率**: Agent 判断的 severity 与预期是否一致
2. **类别准确率**: Agent 判断的 category 与预期是否一致
3. **审核标记准确率**: Agent 判断的 needs_human_review 与预期是否一致
4. **完全匹配率**: 三个字段都正确的案例占比

示例输出：
```
评测结果汇总
================================================================================

总案例数: 20

严重程度准确率: 18/20 (90.0%)
类别准确率: 17/20 (85.0%)
审核标记准确率: 16/20 (80.0%)

完全匹配: 15/20 (75.0%)

详细结果已保存: evaluation_results.json
```

---

## 📄 评测结果

评测完成后会生成 `evaluation_results.json`，包含：

```json
{
  "summary": {
    "total": 20,
    "severity_correct": 18,
    "category_correct": 17,
    "review_correct": 16,
    "all_correct": 15,
    "severity_accuracy": 0.9,
    "category_accuracy": 0.85,
    "review_accuracy": 0.8,
    "overall_accuracy": 0.75
  },
  "details": [
    {
      "case_id": "eval_001",
      "description": "...",
      "expected": {...},
      "predicted": {...},
      "evaluation": {
        "severity_match": true,
        "category_match": true,
        "review_match": true
      },
      "tools_called": 2
    }
  ]
}
```

---

## 🔧 添加新的评测案例

编辑 `data/evaluation_dataset.jsonl`，添加新的一行：

```json
{"id": "eval_021", "description": "新的故障描述", "expected": {"severity": "P1", "category": "latency", "needs_human_review": false}, "reason": "说明"}
```

**注意**:
- 每行一个完整的 JSON 对象
- `expected` 字段是人工标注的"正确答案"
- 标注时考虑业务影响、紧急程度、是否需要人工介入

---

## 📊 评测数据集设计原则

### 覆盖维度

1. **严重程度分布**:
   - P0: 20% （核心收入、数据安全）
   - P1: 40% （核心服务、明显影响）
   - P2: 30% （非核心服务、部分影响）
   - P3: 10% （低影响、观察）

2. **故障类别**:
   - availability: 40%
   - latency: 30%
   - database: 15%
   - deployment: 10%
   - unknown: 5%

3. **边界案例**:
   - 模糊边界（P1/P2 之间）
   - 需要人工判断的案例
   - 多种可能分类的案例

### 标注质量

- ✅ 清晰的故障描述
- ✅ 一致的分类标准
- ✅ 合理的期望结果
- ✅ 说明分类理由

---

## 🎯 目标准确率

- **严重程度**: ≥ 85%
- **类别**: ≥ 80%
- **审核标记**: ≥ 75%
- **完全匹配**: ≥ 70%

---

## 🔄 持续改进

1. **收集真实案例**: 从生产环境收集故障案例
2. **人工标注**: 由专家标注正确分类
3. **定期评测**: 每次改进 Agent 后重新评测
4. **分析错误**: 找出分类错误的模式
5. **优化 Prompt**: 根据错误模式调整系统提示词
6. **调整 Policy**: 更新策略规则

---

## 📝 评测报告模板

```markdown
# Agent 评测报告 - YYYY-MM-DD

## 测试配置
- 模型: claude-opus-4-6
- 数据集: evaluation_dataset.jsonl (20 cases)
- 日期: 2026-08-23

## 评测结果
- 严重程度准确率: 90%
- 类别准确率: 85%
- 审核标记准确率: 80%
- 完全匹配率: 75%

## 错误分析
1. eval_015: 预测 P2，实际 P3 - 低错误率案例判断偏严格
2. eval_013: 预测 availability，实际 unknown - Redis 内存问题分类不准

## 改进建议
1. 调整低错误率案例的判断阈值
2. 优化 Redis/缓存相关问题的分类逻辑
```
