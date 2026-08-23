# Day 2 重构说明

## 📋 改动概览

### 验证结果

✅ **src/policy.py 已经符合 v2 规范！**

现有的 `policy.py` 已经包含：
- PolicyEngine 类
- 7 条规则（高优先级审核、收入影响、内部工具限制等）
- 规则优先级系统（CRITICAL, HIGH, MEDIUM, LOW）
- PolicyViolation 记录
- 结构化日志监控
- 完善的测试覆盖（tests/test_policy.py）

**无需重构！** 只需要：
1. 创建集成示例
2. 验证与新 classifier 的兼容性

### 新增文件

1. **src/classifier_with_policy.py** - Classifier + Policy 集成示例
   - 展示完整流程：LLM 分类 → Policy 修正
   - 包含 4 个测试案例
   - 清晰显示修正过程

## 🔄 与 Day 1 的集成

**完整流程**：
```
用户输入
    ↓
[Day 1] classifier.py
    ↓ LLM 初步分类
IncidentResult (可能不准确)
    ↓
[Day 2] policy.py
    ↓ 规则修正
IncidentResult (可靠)
```

## 🧪 如何测试

### 测试 Policy 单独运行

```bash
# 运行现有的 Policy 测试
pytest tests/test_policy.py -v

# 查看 Policy 监控日志分析
python tests/analyze_policy_logs.py
```

### 测试 Classifier + Policy 集成

```bash
# 运行集成示例
python src/classifier_with_policy.py
```

预期输出：
```
案例 1: 支付接口 5xx 35%
  [Step 1] LLM 输出: P1, needs_human_review=False
  [Step 2] Policy 修正: P0, needs_human_review=True
  触发规则: 收入影响高优先级

案例 2: 内部管理后台响应慢
  [Step 1] LLM 输出: P0
  [Step 2] Policy 修正: P2
  触发规则: 内部工具优先级限制
```

## 📚 对应学习文档

参考 `outputs/ai-agent-engineer-day-2-v2.md`：

- **核心概念**：为什么需要 Policy 规则
- **模型会犯什么错**：LLM 的常见错误
- **规则设计**：什么该用规则，什么该用模型
- **完整示例**：参考 `classifier_with_policy.py`

## ✅ Day 2 完成标志

- [x] 验证 policy.py 符合 v2 规范 ✅
- [x] 创建 Classifier + Policy 集成示例 ✅
- [x] 现有测试仍然通过 ✅
- [x] 集成测试可以运行 ✅

## 🎯 Day 2 的关键学习点

1. **Policy 是 LLM 的安全网**
   - LLM 会犯错（低估严重程度、忘记标记审核）
   - Policy 用确定性规则兜底

2. **规则优先级**
   - CRITICAL：必须执行（P0/P1 人工审核）
   - HIGH：重要但可协商（内部工具降级）
   - MEDIUM/LOW：建议性规则

3. **什么该用规则？**
   - ✅ 业务硬性要求（支付故障必须 P0）
   - ✅ 安全合规（数据泄露必须审核）
   - ✅ 一致性保证（P0 必须人工审核）

4. **什么该用模型？**
   - ✅ 模糊判断（是否延迟问题）
   - ✅ 自然语言理解（提取关键信息）
   - ✅ 生成人类可读的依据

## 📊 Policy 规则列表

当前 policy.py 包含的规则：

1. **高优先级必须审核** (CRITICAL)
   - P0/P1 必须 needs_human_review=True

2. **分类未知时保持谦逊** (HIGH)
   - category=unknown 时不假装已找到根因

3. **收入影响高优先级** (CRITICAL)
   - 支付/交易高错误率必须 P0

4. **内部工具优先级限制** (HIGH)
   - 内部工具不应高于 P2

5. **核心服务宕机必须 P0** (CRITICAL)
   - 支付/登录完全不可用必须 P0

6. **数据安全必须审核** (CRITICAL)
   - 数据泄露/SQL 注入必须人工审核

7. **错误率阈值强制** (CRITICAL)
   - 错误率 >20% 必须 P0
   - 错误率 5-20% 至少 P1

## 🔗 与现有代码的关系

- **保持兼容**：policy.py 不需要改动
- **新增集成**：classifier_with_policy.py 展示如何组合使用
- **测试覆盖**：现有测试继续有效

## 📝 Git 提交

```bash
# 添加新文件
git add src/classifier_with_policy.py REFACTOR_DAY2.md

# 提交
git commit -m "Refactor Day 2: 验证 policy.py 并创建集成示例

改动：
- 验证 src/policy.py 符合 v2 规范（无需修改）
- 新增 src/classifier_with_policy.py（集成示例）
- 展示 LLM + Policy 完整流程
- 包含 4 个测试案例

说明：
policy.py 已经很完善，包含 7 条规则、优先级系统、
结构化日志等，完全符合 Day 2 v2 要求。

相关文档：outputs/ai-agent-engineer-day-2-v2.md
"
```

## 🎯 下一步：Day 3

Day 3 会重构工具系统：
- 创建 `tools/` 目录
- 移动 `log_search.py` → `tools/log_search.py`
- 添加 `tools/tool_definitions.py`
- 添加 `tools/executor.py`
- 创建示例数据 `data/sample_logs.jsonl`
