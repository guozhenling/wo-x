# 故障模式与修正策略

本文档记录 LLM 在故障分类中的常见失败模式，以及对应的修正策略。

## 目录

- [常见失败模式](#常见失败模式)
- [修正策略](#修正策略)
- [实战案例](#实战案例)
- [最佳实践](#最佳实践)

---

## 常见失败模式

### 1. 输出空理由或过于简短

**表现**：
```json
{
  "severity": "P1",
  "category": "availability",
  "needs_human_review": true,
  "rationale": ""  // 空字符串
}
```

或

```json
{
  "rationale": "有问题"  // 过于简短，无实际信息
}
```

**发生原因**：
- 模型对任务理解不充分
- 温度参数设置过低导致过度简化
- prompt 未明确要求详细理由
- 模型在某些边界情况下"懒惰"

**影响**：
- 无法审计分类依据
- 难以发现误判
- 降低系统可信度

---

### 2. 误判严重程度

**表现**：

| 故障描述 | 期望 | 实际 | 问题 |
|---------|------|------|------|
| 支付接口 5xx 35% | P0 | P1 | 低估影响 |
| 内部工具慢 | P3 | P1 | 高估影响 |
| 数据库主库宕机 | P0 | P2 | 严重低估 |

**发生原因**：
- 缺少业务上下文（不知道支付=收入）
- 关键词误导（"内部"被过度关注）
- 百分比理解偏差（12% vs 35%）
- 模型对"完全不可用"vs"部分不可用"区分不清

---

### 3. 分类类别错误

**表现**：

| 故障描述 | 期望 category | 实际 category | 问题 |
|---------|--------------|--------------|------|
| Redis OOM 崩溃 | database | availability | 混淆根因和症状 |
| CSS 加载失败 | deployment | availability | 混淆发布问题和可用性 |
| 404 日志增多 | unknown | availability | 原因不明但被归为可用性 |
| 数据同步延迟 10 分钟 | latency | database | 关键词优先级错误 |

**发生原因**：
- 关键词匹配优先级不清晰
- 根因和表象混淆
- category 定义在 prompt 中不够明确

---

### 4. needs_human_review 判断不合理

**表现**：

| 故障 | severity | needs_human_review | 问题 |
|-----|----------|-------------------|------|
| 支付接口 35% 失败 | P0 | false ❌ | P0 必须人工介入 |
| 日志输出格式错误 | P3 | true ❌ | P3 不需要人工 |
| 推荐算法不准 | P2 | true ❌ | 非关键功能不需要 |

**发生原因**：
- 模型对"人工审核"的理解与业务定义不一致
- 缺少明确的规则映射（severity → needs_human_review）

---

### 5. JSON 格式不合规

**表现**：
```json
{
  "severity": "高",  // 应该是 P1 而非中文
  "category": "网络",  // 应该是英文枚举值
  "needs_human_review": "是"  // 应该是 boolean
}
```

或返回非 JSON 格式：
```
这是一个P1级别的可用性故障...
```

**发生原因**：
- prompt 中语言混用（中文描述 + 英文字段）
- 模型"创造性"地扩展了枚举值
- 未明确要求返回纯 JSON

---

## 修正策略

### 策略 1：通过 Prompt 修正

#### 1.1 明确要求详细理由

**问题**：rationale 为空或过短

**修正**：
```python
system_prompt = """
...
CRITICAL: rationale 字段必须包含：
1. 你识别到的关键信息（错误率、持续时间、影响范围）
2. 为什么选择这个严重程度（引用判定标准）
3. 为什么选择这个类别（根因是什么）

示例：
"支付接口5xx错误率达35%，超过P0阈值（20%），且持续8分钟，直接影响收入，属于可用性故障（核心服务不可用）"
"""
```

#### 1.2 提供业务上下文

**问题**：误判严重程度

**修正**：
```python
system_prompt = """
核心业务功能（直接影响收入）：
- 支付、交易、订单、结算
- 用户登录、注册（无法使用产品）
- 数据写入（数据丢失风险）

非核心功能：
- 推荐系统、搜索排序优化
- 报表、导出
- 内部工具、管理后台
"""
```

#### 1.3 明确分类优先级

**问题**：category 分类错误

**修正**：
```python
system_prompt = """
分类优先级（从高到低）：
1. database - 数据库、缓存、存储层问题
2. deployment - 发布、配置、代码问题
3. latency - 性能慢但仍可用
4. availability - 服务完全不可用或大面积失败
5. unknown - 原因不明、信息不足

判定规则：
- Redis/MySQL 崩溃 → database（不是 availability）
- CSS/JS 加载失败 → deployment（不是 availability）
- 原因不明 → unknown（不是 availability）
"""
```

#### 1.4 使用思维链（Chain of Thought）

**问题**：复杂判断出错

**修正**：
```python
prompt = f"""
请按以下步骤分析：

步骤1：提取关键信息
- 错误率/影响范围：
- 持续时间：
- 影响的功能：

步骤2：判断严重程度
- 是否影响收入？
- 错误率是否 >20%？
- 是否完全不可用？

步骤3：判断故障类别
- 根本原因是什么？
- 属于哪一层的问题？

步骤4：输出分类结果
{{JSON}}
"""
```

---

### 策略 2：通过 Schema 约束

#### 2.1 使用 Pydantic 强制校验

**问题**：JSON 格式不合规、枚举值创造

**修正**：
```python
from pydantic import BaseModel, Field
from typing import Literal

class IncidentTriage(BaseModel):
    severity: Literal["P0", "P1", "P2", "P3"]  # 只能是这4个值
    category: Literal["availability", "latency", "database", "deployment", "unknown"]
    needs_human_review: bool
    rationale: str = Field(min_length=10, max_length=500)
```

**效果**：
- ❌ `severity="高"` → ValidationError
- ❌ `category="network"` → ValidationError
- ❌ `needs_human_review="是"` → ValidationError
- ❌ `rationale=""` → ValidationError

#### 2.2 自定义字段验证器

**问题**：rationale 为空或无意义

**修正**：
```python
@field_validator('rationale')
@classmethod
def validate_rationale(cls, v: str) -> str:
    if not v or v.strip() == "":
        raise ValueError("rationale 不能为空")
    
    # 检查是否包含关键信息
    if len(v.strip()) < 20:
        raise ValueError("rationale 必须提供充分的分类理由（至少20个字符）")
    
    # 可选：检查是否包含必要的关键词
    keywords = ["错误率", "持续", "影响", "不可用", "延迟", "故障"]
    if not any(kw in v for kw in keywords):
        raise ValueError("rationale 必须包含故障分析关键信息")
    
    return v.strip()
```

#### 2.3 使用 OpenAI Function Calling / Structured Outputs

**问题**：模型频繁返回非 JSON 格式

**修正**（使用 OpenAI SDK）：
```python
from openai import OpenAI

client = OpenAI(base_url="...", api_key="...")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": incident_description}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "incident_triage",
            "schema": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                    "category": {"type": "string", "enum": ["availability", "latency", "database", "deployment", "unknown"]},
                    "needs_human_review": {"type": "boolean"},
                    "rationale": {"type": "string", "minLength": 10}
                },
                "required": ["severity", "category", "needs_human_review", "rationale"]
            }
        }
    }
)
```

**效果**：模型**保证**返回符合 schema 的 JSON

---

### 策略 3：通过业务规则自动修正

#### 3.1 严重程度一致性修正

**问题**：P0 故障但 needs_human_review=false

**修正**：
```python
def _validate_business_logic(self, result: IncidentTriage) -> None:
    # 规则1: P0 和 P1 必须需要人工审核
    if result.severity in ["P0", "P1"] and not result.needs_human_review:
        logger.warning(f"自动修正: {result.severity} 级别故障设置为需要人工审核")
        result.needs_human_review = True
    
    # 规则2: P3 级别不应该需要人工审核（除非涉及安全）
    if result.severity == "P3" and result.needs_human_review:
        if "安全" not in result.rationale and "数据" not in result.rationale:
            logger.warning(f"自动修正: P3 级别故障设置为不需要人工审核")
            result.needs_human_review = False
```

#### 3.2 关键词规则增强

**问题**：支付故障被低估

**修正**：
```python
def _apply_keyword_rules(self, description: str, result: IncidentTriage) -> None:
    # 规则：支付/交易相关且错误率>20% 强制P0
    payment_keywords = ["支付", "交易", "订单", "结算", "pay", "transaction"]
    if any(kw in description for kw in payment_keywords):
        # 提取错误率
        import re
        match = re.search(r'(\d+)%', description)
        if match and int(match.group(1)) > 20:
            if result.severity != "P0":
                logger.warning(f"自动修正: 支付相关故障且错误率>{match.group(1)}% 提升为P0")
                result.severity = "P0"
                result.needs_human_review = True
```

#### 3.3 分类优先级修正

**问题**：Redis OOM 被分类为 availability 而非 database

**修正**：
```python
def _fix_category_priority(self, description: str, result: IncidentTriage) -> None:
    # 数据库/缓存关键词优先
    db_keywords = ["MySQL", "Redis", "PostgreSQL", "MongoDB", "数据库", "OOM", "缓存"]
    if any(kw in description for kw in db_keywords) and result.category != "database":
        logger.warning(f"自动修正: 检测到数据库相关关键词，修正为 database 分类")
        result.category = "database"
    
    # 部署/配置关键词
    deploy_keywords = ["CSS", "JS", "静态资源", "部署", "发布", "配置", "灰度"]
    if any(kw in description for kw in deploy_keywords) and result.category == "availability":
        logger.warning(f"自动修正: 检测到部署相关关键词，修正为 deployment 分类")
        result.category = "deployment"
```

---

### 策略 4：多模型投票 / 人工确认

#### 4.1 多模型投票

**问题**：单个模型不稳定

**修正**：
```python
def classify_with_voting(self, description: str, models: list[str] = None) -> IncidentTriage:
    if models is None:
        models = ["gpt-4", "claude-3", "gpt-3.5-turbo"]
    
    results = []
    for model in models:
        try:
            result = self.classify(description, model=model)
            results.append(result)
        except Exception as e:
            logger.error(f"模型 {model} 分类失败: {e}")
    
    # 投票：选择最常见的 severity
    from collections import Counter
    severities = [r.severity for r in results]
    final_severity = Counter(severities).most_common(1)[0][0]
    
    # 如果有分歧，标记需要人工审核
    needs_review = len(set(severities)) > 1
    
    return results[0]._replace(
        severity=final_severity,
        needs_human_review=needs_review
    )
```

#### 4.2 置信度评分

**问题**：难以判断模型输出的可信度

**修正**：
```python
class IncidentTriageWithConfidence(BaseModel):
    severity: Literal["P0", "P1", "P2", "P3"]
    category: Literal["availability", "latency", "database", "deployment", "unknown"]
    needs_human_review: bool
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1 之间

# 在 prompt 中要求
prompt += """
请在 confidence 字段中给出你对这次分类的置信度（0-1）：
- 1.0: 非常确定，信息充分
- 0.7-0.9: 比较确定，有明确证据
- 0.4-0.6: 不太确定，信息不足
- 0.0-0.3: 很不确定，需要更多信息
"""

# 低置信度自动标记需要人工审核
if result.confidence < 0.6:
    result.needs_human_review = True
```

---

## 实战案例

### 案例 1：支付接口故障被低估

**原始输入**：
```
支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟
```

**模型初次输出**：
```json
{
  "severity": "P1",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "接口错误率升高"
}
```

**问题分析**：
1. ❌ severity 应该是 P0（涉及收入）
2. ❌ rationale 过于简短
3. ⚠️ 未考虑 35% 错误率的严重性

**应用修正**：

1. **Prompt 增强**（添加业务上下文）：
```python
system_prompt += """
核心规则：支付、交易、订单相关功能错误率 >20% 必须判定为 P0
"""
```

2. **关键词规则**：
```python
if "支付" in description and "35%" in description:
    result.severity = "P0"
```

3. **字段验证器**：
```python
@field_validator('rationale')
def validate_rationale(cls, v):
    if len(v) < 20:
        raise ValueError("rationale 过短")
    return v
```

**修正后输出**：
```json
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "支付接口5xx错误率达35%，超过P0阈值（20%），且持续8分钟，直接影响收入，属于P0级紧急故障"
}
```

---

### 案例 2：Redis OOM 分类错误

**原始输入**：
```
Redis 主实例 OOM，服务不可用，已触发主从切换
```

**模型初次输出**：
```json
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "服务不可用"
}
```

**问题分析**：
1. ✅ severity 正确
2. ❌ category 应该是 database（根因）而非 availability（症状）
3. ❌ rationale 未提及 OOM 根因

**应用修正**：

1. **Prompt 明确分类优先级**：
```python
system_prompt += """
分类优先级：
1. database - 数据库/缓存层问题（Redis, MySQL）
2. deployment - 代码/配置问题
3. latency - 性能问题
4. availability - 其他导致不可用的问题
"""
```

2. **关键词规则**：
```python
db_keywords = ["Redis", "MySQL", "OOM", "数据库"]
if any(kw in description for kw in db_keywords):
    result.category = "database"
```

**修正后输出**：
```json
{
  "severity": "P0",
  "category": "database",
  "needs_human_review": true,
  "rationale": "Redis主实例OOM导致服务不可用，属于数据库层故障，虽然已主从切换但需排查OOM根因"
}
```

---

### 案例 3：内部工具慢被高估

**原始输入**：
```
内部管理后台查询慢，从 2 秒增加到 10 秒
```

**模型初次输出**：
```json
{
  "severity": "P1",
  "category": "latency",
  "needs_human_review": true,
  "rationale": "查询性能下降严重"
}
```

**问题分析**：
1. ❌ severity 应该是 P3（内部工具，非核心功能）
2. ✅ category 正确
3. ⚠️ needs_human_review 对 P3 应该是 false

**应用修正**：

1. **Prompt 业务上下文**：
```python
system_prompt += """
功能优先级：
- 核心用户功能（P0/P1）：登录、支付、交易、数据写入
- 核心内部功能（P1/P2）：监控告警、核心服务API
- 非核心功能（P2/P3）：报表、导出、内部工具、管理后台
"""
```

2. **业务规则修正**：
```python
if "内部" in description and "管理" in description:
    if result.severity in ["P0", "P1"]:
        result.severity = "P3"
        result.needs_human_review = False
```

**修正后输出**：
```json
{
  "severity": "P3",
  "category": "latency",
  "needs_human_review": false,
  "rationale": "内部管理后台查询从2秒增至10秒，影响仅限内部人员，不影响用户体验，优先级较低"
}
```

---

## 最佳实践

### 1. 分层防护策略

```
Layer 1: Prompt Engineering
  ↓ 失败
Layer 2: Pydantic Schema Validation
  ↓ 失败
Layer 3: Business Rule Correction
  ↓ 失败
Layer 4: Human Review
```

**永远不要依赖单层防护**

### 2. 日志与监控

```python
# 记录所有修正操作
logger.warning(f"自动修正: {before} → {after}, 原因: {reason}")

# 统计失败率
metrics.increment("llm_classification_failed")
metrics.increment(f"category_corrected_{original}_{corrected}")
```

**目标**：
- 修正率 < 10% → Prompt 足够好
- 修正率 > 30% → 需要优化 Prompt 或切换模型

### 3. 持续优化流程

1. **收集失败案例** → failures.jsonl
2. **分析失败模式** → 归类根本原因
3. **更新 Prompt** → 添加相关规则
4. **更新测试集** → test_cases.py
5. **回归测试** → 验证准确率提升
6. **部署新版本**

### 4. 何时使用哪种策略

| 失败模式 | 首选策略 | 次选策略 | 最后手段 |
|---------|---------|---------|---------|
| 空理由 | Pydantic min_length | Prompt 要求 | 拒绝分类 |
| 误判严重性 | Prompt 业务上下文 | 关键词规则 | 多模型投票 |
| 分类错误 | Prompt 优先级 | 关键词规则 | 人工标注 |
| needs_human_review | 业务规则自动修正 | Prompt 明确规则 | - |
| JSON 格式 | Pydantic 校验 | Structured Outputs | - |

### 5. 模型选择建议

| 模型 | 准确率 | 速度 | 成本 | 适用场景 |
|-----|-------|------|------|---------|
| GPT-4 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💰💰💰 | 生产环境 |
| Claude 3 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💰💰💰 | 生产环境 |
| GPT-3.5 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 💰 | 开发/测试 |

**建议**：
- 生产环境使用 GPT-4 / Claude 3
- 配合 Pydantic + 业务规则多层防护
- 监控修正率，持续优化

### 6. 温度参数调优

```python
# 分类任务建议低温度（更确定、更一致）
temperature = 0.1  # 最确定，适合严格分类
temperature = 0.3  # 平衡，推荐
temperature = 0.7  # 较创造性，不推荐
```

### 7. 测试驱动开发

```python
# 每次发现失败案例，立即添加到测试集
test_cases.append({
    "description": "支付接口 5xx 35%",
    "expected": {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": True
    }
})

# 确保回归测试通过
assert accuracy > 0.90  # 90% 准确率阈值
```

---

## 总结

### 核心教训

1. **LLM 不可靠** - 永远需要多层防护
2. **业务规则优先** - 关键决策不能完全依赖模型
3. **持续监控** - 记录修正率，及时发现问题
4. **测试覆盖** - 失败案例必须加入测试集

### 修正优先级

1. **Pydantic Schema** - 最硬的防线，拦截格式问题
2. **业务规则修正** - 修正已知的系统性偏差
3. **Prompt Engineering** - 减少失败发生率
4. **模型选择/投票** - 提升基础能力

### 目标指标

- ✅ JSON 格式合规率：100%（Pydantic 保证）
- ✅ Severity 准确率：>95%
- ✅ Category 准确率：>85%
- ✅ 综合准确率：>90%
- ✅ 业务规则修正率：<10%

---

**记住**：绝不直接信任模型输出，永远校验、修正、记录。
