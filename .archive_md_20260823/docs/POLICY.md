# Policy 规则引擎文档

## 概述

Policy 模块提供确定性规则引擎，用于修正和验证模型输出，避免模型幻觉导致的错误决策。

**核心理念**：关键决策不能完全依赖模型，必须由确定性规则兜底。

## 架构

```
故障描述
    ↓
模型分类（LLM）
    ↓
JSON 格式校验
    ↓
Pydantic Schema 校验
    ↓
Policy 规则引擎 ← 新增层
    ↓
业务逻辑校验（兜底）
    ↓
最终结果
```

## 规则列表

### 规则 1: 高优先级必须人工复核 ⭐⭐⭐

**优先级**: CRITICAL

**说明**: P0 和 P1 级别的故障必须标记为需要人工审核，无例外。

**触发条件**:
- `severity` 为 `P0` 或 `P1`
- `needs_human_review` 为 `false`

**修正动作**:
```python
result['needs_human_review'] = True
```

**示例**:
```python
# 输入
{
    "severity": "P0",
    "needs_human_review": False  # 错误
}

# 修正后
{
    "severity": "P0",
    "needs_human_review": True  # 自动修正
}
```

---

### 规则 2: 未知原因谦逊原则 ⭐⭐⭐

**优先级**: HIGH

**说明**: 描述中明确说明原因不明时，不能假装已经找到根因。避免模型强行给出一个看似合理但可能错误的分类。

**触发条件**:
- 描述包含："原因不明"、"不确定"、"不清楚"、"未知"、"怀疑"、"可能"等关键词
- `category` 不是 `unknown`

**修正动作**:
```python
result['category'] = 'unknown'
result['needs_human_review'] = True
result['rationale'] = "[Policy修正] 原因不明确，需进一步调查。" + rationale
```

**示例**:
```python
# 输入
描述: "数据库偶发连接失败，原因不明"
{
    "category": "database"  # 错误：假装知道是数据库问题
}

# 修正后
{
    "category": "unknown",  # 承认不知道根因
    "needs_human_review": True
}
```

**为什么重要**: 防止模型"过度自信"，避免误导调查方向。

---

### 规则 3: 收入影响高优先级 ⭐⭐⭐

**优先级**: CRITICAL (错误率 >= 20%), HIGH (其他)

**说明**: 涉及支付、交易、订单等直接影响收入的故障，必须高优先级处理。

**触发条件**:
- 描述包含："支付"、"交易"、"订单"、"结算"等关键词

**修正规则**:
1. 错误率 >= 20% → 强制 `P0`
2. 其他收入相关 → 最低 `P1`
3. 强制 `needs_human_review = true`

**示例**:
```python
# 输入
描述: "支付接口错误率 25%"
{
    "severity": "P2"  # 错误
}

# 修正后
{
    "severity": "P0",  # 强制 P0
    "needs_human_review": True
}
```

---

### 规则 4: 内部工具优先级限制 ⭐⭐

**优先级**: HIGH

**说明**: 内部工具、管理后台等不直接影响用户的功能，最高只能是 P2。

**触发条件**:
- 描述包含："内部"、"管理后台"、"内部工具"等关键词
- `severity` 为 `P0` 或 `P1`

**修正动作**:
```python
result['severity'] = 'P2'
result['needs_human_review'] = False
```

**示例**:
```python
# 输入
描述: "内部管理后台响应慢"
{
    "severity": "P1"  # 错误
}

# 修正后
{
    "severity": "P2",  # 降级
    "needs_human_review": False
}
```

---

### 规则 5: 核心服务宕机必须 P0 ⭐⭐⭐

**优先级**: CRITICAL

**说明**: 核心服务（支付、登录、主站等）完全不可用时，必须是 P0。

**触发条件**:
- 描述包含核心服务关键词：["支付", "登录", "注册", "主站", "数据库主库"]
- 描述包含宕机关键词：["完全不可用", "宕机", "崩溃", "down", "crash"]
- `severity` 不是 `P0`

**修正动作**:
```python
result['severity'] = 'P0'
result['needs_human_review'] = True
```

---

### 规则 6: 数据安全必须审核 ⭐⭐⭐

**优先级**: CRITICAL

**说明**: 涉及数据泄露、数据丢失、安全漏洞等，无论严重程度如何，都必须人工审核。

**触发条件**:
- 描述包含："数据泄露"、"数据丢失"、"安全"、"漏洞"、"攻击"、"权限"、"越权"、"注入"、"XSS"、"CSRF"等关键词
- `needs_human_review` 为 `false`

**修正动作**:
```python
result['needs_human_review'] = True
```

**示例**:
```python
# 输入
描述: "发现用户数据泄露风险"
{
    "needs_human_review": False  # 错误
}

# 修正后
{
    "needs_human_review": True  # 强制审核
}
```

---

### 规则 7: 错误率阈值强制规则 ⭐⭐

**优先级**: HIGH

**说明**: 根据错误率自动判断严重程度，防止模型低估高错误率的影响。

**触发条件**:
- 错误率 >= 50%
- `severity` 为 `P2` 或 `P3`

**修正动作**:
```python
result['severity'] = 'P1'
result['needs_human_review'] = True
```

---

## 使用方法

### 方式 1: 自动集成（推荐）

Policy 引擎已自动集成到 `IncidentClassifier`，无需额外代码：

```python
from client import LLMClient
from incident_triage import IncidentClassifier

client = LLMClient()
classifier = IncidentClassifier(client)

# Policy 引擎自动执行
result = classifier.classify("故障描述")

# 查看 Policy 修正记录
if classifier.policy_engine.violations:
    for v in classifier.policy_engine.violations:
        print(f"{v.policy_name}: {v.message}")
```

### 方式 2: 独立使用

```python
from policy import PolicyEngine

engine = PolicyEngine()

# 检查并修正
result = {
    "severity": "P0",
    "category": "availability",
    "needs_human_review": False,  # 将被修正
    "rationale": "..."
}

corrected = engine.check_and_enforce("故障描述", result)

# 查看修正记录
for v in engine.violations:
    print(f"{v.policy_name}: {v.original_value} → {v.corrected_value}")
```

## 规则优先级

| 优先级 | 说明 | 规则示例 |
|--------|------|----------|
| CRITICAL | 关键规则，必须执行 | 高优先级必须审核、数据安全审核 |
| HIGH | 高优先级规则 | 收入影响、未知原因谦逊 |
| MEDIUM | 中优先级规则 | - |
| LOW | 低优先级规则 | - |

## 规则执行顺序

所有规则按固定顺序执行，后续规则可以覆盖前面规则的修正：

1. 高优先级必须人工复核
2. 未知原因谦逊原则
3. 收入影响高优先级
4. 内部工具优先级限制
5. 核心服务宕机必须 P0
6. 数据安全必须审核
7. 错误率阈值强制规则

## PolicyViolation 记录

每次规则违反都会记录：

```python
@dataclass
class PolicyViolation:
    policy_name: str           # 规则名称
    level: PolicyLevel         # 优先级
    action: PolicyAction       # 动作类型
    message: str              # 违反说明
    original_value: Any       # 原始值
    corrected_value: Any      # 修正值
```

## 监控指标

建议监控的指标：

```python
# 规则触发率
policy.violations_total
policy.violations_by_rule{rule="高优先级必须人工复核"}

# 关键规则触发率
policy.critical_violations_total

# 修正类型分布
policy.corrections_by_field{field="severity"}
policy.corrections_by_field{field="needs_human_review"}
```

## 添加新规则

### 步骤

1. **在 `PolicyEngine` 中添加新方法**：

```python
def _enforce_new_rule(self, result: Dict[str, Any], description: str) -> Dict[str, Any]:
    """
    规则 N: 规则名称
    
    规则说明...
    """
    # 检查条件
    if condition:
        # 记录违反
        self.violations.append(PolicyViolation(
            policy_name="规则名称",
            level=PolicyLevel.HIGH,
            action=PolicyAction.ENFORCE,
            message="违反说明",
            original_value=old_value,
            corrected_value=new_value
        ))
        # 执行修正
        result['field'] = new_value
    
    return result
```

2. **在 `check_and_enforce` 方法中调用**：

```python
def check_and_enforce(self, description: str, result: Dict[str, Any]) -> Dict[str, Any]:
    self.violations.clear()
    
    # 已有规则...
    result = self._enforce_rule_1(result)
    result = self._enforce_rule_2(result, description)
    
    # 新规则
    result = self._enforce_new_rule(result, description)  # ← 添加这里
    
    return result
```

3. **编写测试**：

在 `tests/test_policy.py` 中添加测试用例。

## 最佳实践

1. **规则应该简单明确** - 易于理解和维护
2. **记录所有修正** - 便于审计和优化
3. **关键规则优先级设为 CRITICAL** - 确保执行
4. **定期审查规则效果** - 根据实际情况调整
5. **新规则先试运行** - 设为 WARN 模式观察

## 与其他防护层的关系

```
第一层: JSON 格式校验
   ↓
第二层: Pydantic Schema 校验
   ↓
第三层: Policy 规则引擎 ← 新增
   ↓
第四层: 业务逻辑校验（兜底）
```

- **Policy vs Pydantic**: Pydantic 校验数据类型和格式，Policy 校验业务逻辑
- **Policy vs 业务规则**: Policy 是主要的规则引擎，业务规则作为兜底
- **Policy 优势**: 集中管理、易于扩展、清晰的违反记录

## 总结

Policy 规则引擎通过 **7 条确定性规则**，确保：

1. ✅ 高优先级故障必须人工审核
2. ✅ 不假装知道不确定的根因
3. ✅ 收入相关故障高优先级
4. ✅ 内部工具不会误报高优
5. ✅ 核心服务宕机正确识别
6. ✅ 安全问题必须审核
7. ✅ 高错误率不被低估

**核心价值**: 避免模型幻觉，确保关键决策的可靠性。
