# 生产环境决策指南

## 问题 1：哪些判断交给模型，哪些必须由确定性规则兜底？

### 决策矩阵

| 判断类型 | 交给模型 | 确定性规则兜底 | 理由 |
|---------|---------|---------------|------|
| **故障类别识别** | ✅ 主要 | ⚠️ 部分 | 模型理解自然语言描述能力强，但关键词需规则兜底 |
| **严重程度初判** | ✅ 主要 | ✅ 必须 | 模型提供初判，规则强制修正关键场景 |
| **业务影响判断** | ❌ 不可 | ✅ 必须 | 涉及收入、数据安全必须用规则 |
| **人工审核判断** | ❌ 不可 | ✅ 必须 | P0/P1 必须人工，这是硬性规则 |
| **分类理由生成** | ✅ 完全 | ❌ 无需 | 这是模型擅长的，只需长度校验 |

---

### 详细分析

#### 1.1 交给模型的判断

##### ✅ 故障类别识别（有规则兜底）

**为什么交给模型**：
- 故障描述千变万化，规则难以穷举
- 模型能理解同义词、上下文、隐含信息
- 例如："Redis 主节点 OOM" vs "缓存服务内存溢出" → 模型都能识别为 database

**示例**：
```python
# 模型擅长处理的多样化描述
descriptions = [
    "Redis OOM 崩溃",
    "缓存服务内存不足导致重启",
    "主存储节点内存溢出",
    "Cache server ran out of memory"
]
# 模型都能识别为 category="database"
```

**规则兜底**：
```python
# 关键词强制规则（防止模型漏判）
DB_KEYWORDS = ["MySQL", "Redis", "PostgreSQL", "MongoDB", "数据库", "OOM", "缓存"]
DEPLOY_KEYWORDS = ["CSS", "JS", "静态资源", "部署", "发布", "配置", "灰度"]

def _enforce_category_rules(description: str, model_result: str) -> str:
    # 规则1：数据库关键词 → 强制 database
    if any(kw in description for kw in DB_KEYWORDS):
        if model_result != "database":
            logger.warning(f"规则修正: 检测到数据库关键词，修正为 database")
            return "database"
    
    # 规则2：部署关键词 → 强制 deployment
    if any(kw in description for kw in DEPLOY_KEYWORDS):
        if model_result == "availability":  # 只修正明显错误
            logger.warning(f"规则修正: 检测到部署关键词，修正为 deployment")
            return "deployment"
    
    return model_result
```

##### ✅ 严重程度初判（规则强制修正）

**为什么交给模型**：
- 需要综合考虑错误率、持续时间、影响范围
- 模型能理解"持续 8 分钟"比"偶发"更严重

**示例**：
```python
# 模型能理解复杂场景
"支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟"
# 模型会综合考虑：
# - 35% 错误率（高）
# - 支付相关（关键）
# - 持续 8 分钟（不是瞬时）
# → 判断为 P0
```

**规则强制修正（兜底）**：
```python
def _enforce_severity_rules(description: str, model_result: str) -> str:
    """关键场景强制规则，不信任模型判断"""
    
    # 规则1：支付/交易 + 高错误率 → 强制 P0
    payment_keywords = ["支付", "交易", "订单", "结算"]
    if any(kw in description for kw in payment_keywords):
        # 提取错误率
        import re
        match = re.search(r'(\d+)%', description)
        if match and int(match.group(1)) >= 20:
            if model_result != "P0":
                logger.critical(f"规则强制修正: 支付相关 + {match.group(1)}% 错误率 → P0")
                return "P0"
    
    # 规则2：完全不可用 → 强制 P0
    unavailable_keywords = ["完全不可用", "宕机", "崩溃", "服务中断"]
    if any(kw in description for kw in unavailable_keywords):
        core_services = ["支付", "登录", "注册", "数据库", "主站"]
        if any(svc in description for svc in core_services):
            if model_result not in ["P0", "P1"]:
                logger.critical(f"规则强制修正: 核心服务完全不可用 → P0")
                return "P0"
    
    # 规则3：内部工具 + 慢 → 最高 P2
    if "内部" in description and any(kw in description for kw in ["慢", "延迟"]):
        if model_result in ["P0", "P1"]:
            logger.warning(f"规则降级: 内部工具性能问题不应高于 P2")
            return "P2"
    
    return model_result
```

##### ✅ 分类理由生成（完全交给模型）

**为什么完全交给模型**：
- 这是生成任务，模型最擅长
- 只需要校验长度和非空
- 规则无法生成有意义的自然语言

```python
# 只需要简单校验
@field_validator('rationale')
def validate_rationale(cls, v: str) -> str:
    if len(v.strip()) < 10:
        raise ValueError("rationale 必须提供充分理由（至少10个字符）")
    return v.strip()
```

---

#### 1.2 必须由确定性规则兜底的判断

##### ✅ 业务影响判断（不可交给模型）

**为什么不能交给模型**：
- 模型不知道你的业务哪些功能影响收入
- 模型不知道你的服务架构和依赖关系
- 这些是组织特定的知识，必须编码为规则

**反例（危险）**：
```python
# ❌ 错误：让模型判断业务影响
prompt = "判断这个故障是否影响收入：{description}"
# 模型可能：
# - 不知道你的支付服务具体是什么
# - 不知道某个内部 API 其实被支付依赖
# - 给出不一致的判断
```

**正确做法**：
```python
# ✅ 正确：用确定性规则判断业务影响
REVENUE_CRITICAL_SERVICES = {
    "支付": ["支付接口", "支付网关", "payment-service"],
    "交易": ["交易系统", "订单服务", "order-service"],
    "核心用户流程": ["登录", "注册", "用户认证"]
}

def _is_revenue_critical(description: str) -> bool:
    """确定性判断是否影响收入"""
    for category, keywords in REVENUE_CRITICAL_SERVICES.items():
        if any(kw in description for kw in keywords):
            logger.info(f"检测到收入关键服务: {category}")
            return True
    return False

# 强制规则
if _is_revenue_critical(description):
    if model_result.severity not in ["P0", "P1"]:
        logger.critical("规则强制修正: 影响收入的故障最低 P1")
        model_result.severity = "P1"
    model_result.needs_human_review = True
```

##### ✅ 人工审核判断（不可交给模型）

**为什么不能交给模型**：
- 这是流程规则，不是判断任务
- P0/P1 必须人工介入是硬性要求，不容商量
- 模型可能"认为"某个 P0 不需要人工审核

**错误示例**：
```python
# ❌ 危险：让模型决定是否需要人工审核
# 模型可能返回：
{
  "severity": "P0",
  "needs_human_review": false  # ← 这是灾难！
}
```

**正确做法**：
```python
# ✅ 硬性规则，不信任模型
def _enforce_human_review_policy(result: IncidentTriage) -> None:
    """强制执行人工审核策略"""
    
    # 规则1：P0/P1 必须人工审核（无例外）
    if result.severity in ["P0", "P1"]:
        if not result.needs_human_review:
            logger.critical(f"规则强制修正: {result.severity} 必须人工审核")
            result.needs_human_review = True
    
    # 规则2：P3 不应该人工审核（除非安全相关）
    if result.severity == "P3":
        security_keywords = ["安全", "泄露", "攻击", "漏洞", "数据丢失"]
        if not any(kw in result.rationale for kw in security_keywords):
            if result.needs_human_review:
                logger.info(f"规则修正: P3 非安全问题无需人工审核")
                result.needs_human_review = False
    
    # 规则3：影响收入 → 必须人工审核
    if _is_revenue_critical(description):
        result.needs_human_review = True
```

---

### 1.3 最佳实践总结

#### 决策流程

```
输入故障描述
    ↓
┌────────────────────────────────────┐
│  模型初判（擅长自然语言理解）        │
│  - category 初判                    │
│  - severity 初判                    │
│  - 生成 rationale                   │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│  确定性规则强制修正（兜底）         │
│  - 业务影响判断（收入、安全）       │
│  - 严重程度修正（关键服务）         │
│  - 人工审核策略（P0/P1 强制）       │
│  - 分类优先级修正（关键词）         │
└────────────────────────────────────┘
    ↓
安全的分类结果
```

#### 原则

1. **模型负责理解，规则负责兜底**
   - 模型：理解复杂的自然语言描述
   - 规则：确保关键决策不出错

2. **规则覆盖高风险场景**
   - 影响收入 → 规则强制
   - 数据安全 → 规则强制
   - 流程要求 → 规则强制

3. **日志记录所有修正**
   - 便于审计
   - 发现模型系统性偏差
   - 持续优化规则

---

## 问题 2：如果这个结果触发了 PagerDuty，你会增加什么审批或阈值？

### 背景

PagerDuty 会立即通知 on-call 工程师，打断他们的工作（甚至睡眠）。**误报的代价极高**：
- 工程师疲劳 → 真正的 P0 响应变慢
- 信任度下降 → 开始忽略告警
- 团队士气受挫

**核心原则：宁可漏报 P2，不可误报 P0**

---

### 2.1 增加的审批机制

#### 方案 A：人工确认（推荐用于初期）

```python
class PagerDutyTrigger:
    """PagerDuty 触发器（带人工确认）"""
    
    def trigger_if_critical(self, result: IncidentTriage, description: str) -> bool:
        """
        触发 PagerDuty 的多层防护
        
        Returns:
            bool: 是否实际触发了 PagerDuty
        """
        
        # 第一层：只有 P0 才考虑触发 PagerDuty
        if result.severity != "P0":
            logger.info(f"非 P0 故障，不触发 PagerDuty: {result.severity}")
            return False
        
        # 第二层：业务影响确认
        if not self._confirm_revenue_impact(description):
            logger.warning(f"P0 故障但未确认影响收入，不触发 PagerDuty")
            return False
        
        # 第三层：模型置信度检查（如果有）
        if hasattr(result, 'confidence') and result.confidence < 0.8:
            logger.warning(f"模型置信度低 ({result.confidence})，需要人工确认")
            if not self._ask_human_confirmation(result, description):
                return False
        
        # 第四层：人工确认（初期强制，后期可选）
        if not self._ask_human_confirmation(result, description):
            logger.info("人工拒绝触发 PagerDuty")
            return False
        
        # 所有检查通过，触发 PagerDuty
        self._do_trigger_pagerduty(result, description)
        logger.critical(f"已触发 PagerDuty: {description}")
        return True
    
    def _confirm_revenue_impact(self, description: str) -> bool:
        """确认是否影响收入"""
        revenue_keywords = ["支付", "交易", "订单", "结算"]
        return any(kw in description for kw in revenue_keywords)
    
    def _ask_human_confirmation(self, result: IncidentTriage, description: str) -> bool:
        """人工确认（命令行或 Slack）"""
        print("\n" + "="*80)
        print("⚠️  PagerDuty 触发确认")
        print("="*80)
        print(f"故障描述: {description}")
        print(f"严重程度: {result.severity}")
        print(f"故障类别: {result.category}")
        print(f"分类理由: {result.rationale}")
        print("="*80)
        
        # 命令行确认
        response = input("\n是否触发 PagerDuty 通知 on-call 工程师？[yes/no]: ")
        return response.lower() in ['yes', 'y']
        
        # 或者通过 Slack 确认
        # return self._slack_confirm(result, description, timeout=60)
```

#### 方案 B：双模型确认（自动化）

```python
class DualModelPagerDutyTrigger:
    """双模型确认 PagerDuty 触发"""
    
    def __init__(self, primary_classifier, secondary_classifier):
        self.primary = primary_classifier
        self.secondary = secondary_classifier
    
    def trigger_if_critical(self, description: str) -> bool:
        """双模型确认"""
        
        # 主模型分类
        primary_result = self.primary.classify(description)
        
        # 只有主模型判断为 P0 才继续
        if primary_result.severity != "P0":
            return False
        
        # 次模型二次确认
        secondary_result = self.secondary.classify(description)
        
        # 必须两个模型都判断为 P0 或 P1
        if secondary_result.severity not in ["P0", "P1"]:
            logger.warning(
                f"双模型判断不一致: primary={primary_result.severity}, "
                f"secondary={secondary_result.severity}，不触发 PagerDuty"
            )
            # 标记需要人工审核
            return self._escalate_to_human(primary_result, secondary_result, description)
        
        # 两个模型一致，触发 PagerDuty
        self._do_trigger_pagerduty(primary_result, description)
        return True
```

---

### 2.2 增加的阈值

#### 阈值 1：错误率阈值（硬性规则）

```python
def _check_error_rate_threshold(description: str) -> tuple[bool, str]:
    """
    检查错误率是否达到 PagerDuty 阈值
    
    Returns:
        (是否达到阈值, 理由)
    """
    import re
    
    # 提取错误率
    match = re.search(r'(\d+(?:\.\d+)?)%', description)
    if not match:
        return False, "未检测到明确的错误率"
    
    error_rate = float(match.group(1))
    
    # 硬性阈值：支付相关至少 20%
    if any(kw in description for kw in ["支付", "交易", "订单"]):
        if error_rate < 20:
            return False, f"支付相关错误率 {error_rate}% < 20% 阈值"
        return True, f"支付相关错误率 {error_rate}% ≥ 20% 阈值"
    
    # 硬性阈值：核心服务至少 30%
    if any(kw in description for kw in ["登录", "注册", "主站"]):
        if error_rate < 30:
            return False, f"核心服务错误率 {error_rate}% < 30% 阈值"
        return True, f"核心服务错误率 {error_rate}% ≥ 30% 阈值"
    
    # 其他服务：至少 50%
    if error_rate < 50:
        return False, f"非核心服务错误率 {error_rate}% < 50% 阈值"
    return True, f"错误率 {error_rate}% ≥ 50% 阈值"
```

#### 阈值 2：持续时间阈值

```python
def _check_duration_threshold(description: str) -> tuple[bool, str]:
    """
    检查故障持续时间是否达到 PagerDuty 阈值
    
    避免瞬时抖动触发 PagerDuty
    """
    import re
    
    # 提取持续时间（分钟）
    match = re.search(r'持续\s*(\d+)\s*分钟', description)
    if not match:
        match = re.search(r'(\d+)\s*分钟', description)
    
    if not match:
        # 未明确持续时间，默认通过（可能是刚发生）
        return True, "未指定持续时间，默认通过"
    
    duration_minutes = int(match.group(1))
    
    # 阈值：至少持续 3 分钟（避免瞬时抖动）
    if duration_minutes < 3:
        return False, f"持续时间 {duration_minutes} 分钟 < 3 分钟阈值，可能是瞬时抖动"
    
    return True, f"持续时间 {duration_minutes} 分钟 ≥ 3 分钟阈值"
```

#### 阈值 3：影响用户数阈值

```python
def _check_affected_users_threshold(description: str) -> tuple[bool, str]:
    """检查影响用户数是否达到阈值"""
    import re
    
    # 提取影响用户数
    match = re.search(r'影响\s*(\d+)\s*(?:个|位)?用户', description)
    if not match:
        # 未明确用户数，检查是否有"所有用户"等关键词
        if any(kw in description for kw in ["所有用户", "全部用户", "完全不可用"]):
            return True, "影响所有用户"
        # 默认不通过（保守策略）
        return False, "未指定影响用户数，默认不触发"
    
    affected_users = int(match.group(1))
    
    # 阈值：至少影响 100 个用户
    threshold = 100
    if affected_users < threshold:
        return False, f"影响用户 {affected_users} < {threshold} 阈值"
    
    return True, f"影响用户 {affected_users} ≥ {threshold} 阈值"
```

---

### 2.3 完整的 PagerDuty 触发流程

```python
class SafePagerDutyTrigger:
    """安全的 PagerDuty 触发器（多层防护）"""
    
    def should_trigger(self, result: IncidentTriage, description: str) -> dict:
        """
        判断是否应该触发 PagerDuty
        
        Returns:
            {
                "should_trigger": bool,
                "reason": str,
                "checks": dict  # 每个检查的结果
            }
        """
        checks = {}
        
        # 检查 1：必须是 P0
        checks["severity"] = result.severity == "P0"
        if not checks["severity"]:
            return {
                "should_trigger": False,
                "reason": f"非 P0 故障 ({result.severity})，不触发 PagerDuty",
                "checks": checks
            }
        
        # 检查 2：业务影响确认
        checks["revenue_impact"] = self._is_revenue_critical(description)
        if not checks["revenue_impact"]:
            return {
                "should_trigger": False,
                "reason": "未检测到对收入的直接影响",
                "checks": checks
            }
        
        # 检查 3：错误率阈值
        checks["error_rate"], reason = self._check_error_rate_threshold(description)
        if not checks["error_rate"]:
            return {
                "should_trigger": False,
                "reason": reason,
                "checks": checks
            }
        
        # 检查 4：持续时间阈值
        checks["duration"], reason = self._check_duration_threshold(description)
        if not checks["duration"]:
            return {
                "should_trigger": False,
                "reason": reason,
                "checks": checks
            }
        
        # 检查 5：模型置信度（如果有）
        if hasattr(result, 'confidence'):
            checks["confidence"] = result.confidence >= 0.8
            if not checks["confidence"]:
                return {
                    "should_trigger": False,
                    "reason": f"模型置信度低 ({result.confidence})",
                    "checks": checks
                }
        
        # 检查 6：最近触发频率（防止风暴）
        checks["rate_limit"] = self._check_rate_limit()
        if not checks["rate_limit"]:
            return {
                "should_trigger": False,
                "reason": "PagerDuty 触发频率过高（5分钟内已触发3次）",
                "checks": checks
            }
        
        # 所有检查通过
        return {
            "should_trigger": True,
            "reason": "所有阈值和检查通过",
            "checks": checks
        }
    
    def _check_rate_limit(self) -> bool:
        """防止 PagerDuty 风暴"""
        # 检查最近 5 分钟内触发次数
        recent_triggers = self._get_recent_triggers(minutes=5)
        if len(recent_triggers) >= 3:
            logger.warning(f"5分钟内已触发 {len(recent_triggers)} 次 PagerDuty")
            return False
        return True
```

---

### 2.4 分阶段部署策略

#### 阶段 1：初期（1-2 周）- 严格人工确认

```python
# 所有 P0 都需要人工确认
if result.severity == "P0":
    if not human_confirms():
        # 不触发 PagerDuty，但记录为"待审查"
        escalate_to_slack_channel(result, description)
        return False
```

**目标**：
- 观察误报率
- 收集人工决策数据
- 调整阈值

#### 阶段 2：过渡期（2-4 周）- 部分自动化

```python
# 明确的 P0 自动触发，模糊的需要确认
if result.severity == "P0":
    if result.confidence >= 0.9 and error_rate >= 30:
        # 自动触发
        trigger_pagerduty()
    else:
        # 需要确认
        if not human_confirms(timeout=60):
            escalate_to_slack_channel()
```

**目标**：
- 误报率 < 5%
- 自动触发占比 > 70%

#### 阶段 3：成熟期（4 周后）- 基本自动化

```python
# 只有低置信度需要确认
if result.severity == "P0":
    decision = should_trigger(result, description)
    if decision["should_trigger"]:
        trigger_pagerduty()
    else:
        logger.info(f"未触发 PagerDuty: {decision['reason']}")
        escalate_to_slack_channel()
```

**目标**：
- 误报率 < 2%
- 漏报率 < 1%
- 自动触发占比 > 90%

---

### 2.5 误报补救机制

```python
class PagerDutyFalsePosiveFeedback:
    """误报反馈系统"""
    
    def report_false_positive(self, incident_id: str, reason: str):
        """报告误报"""
        # 记录到数据库
        self._log_false_positive(incident_id, reason)
        
        # 立即调整规则
        self._adjust_rules_immediately(incident_id, reason)
        
        # 标记为训练数据
        self._add_to_training_set(incident_id, correct_label="P2")
        
        logger.critical(f"误报已记录: {incident_id} - {reason}")
    
    def _adjust_rules_immediately(self, incident_id: str, reason: str):
        """根据误报立即调整规则"""
        incident = self._get_incident(incident_id)
        
        # 如果是某个关键词导致的误判，加入排除列表
        if "内部工具" in incident.description:
            INTERNAL_TOOLS_KEYWORDS.add(extract_tool_name(incident.description))
            logger.warning(f"已将该工具加入内部工具列表，未来最高 P2")
```

---

### 2.6 建议配置

```python
PAGERDUTY_CONFIG = {
    # 触发阈值
    "thresholds": {
        "revenue_services": {
            "error_rate": 20,  # 20%
            "duration_minutes": 3,
        },
        "core_services": {
            "error_rate": 30,  # 30%
            "duration_minutes": 5,
        },
        "other_services": {
            "error_rate": 50,  # 50%
            "duration_minutes": 10,
        }
    },
    
    # 频率限制
    "rate_limit": {
        "max_triggers_per_5min": 3,
        "max_triggers_per_hour": 10,
    },
    
    # 人工确认
    "human_confirmation": {
        "required_for_low_confidence": True,  # 置信度 < 0.8
        "required_for_initial_deployment": True,  # 初期部署
        "timeout_seconds": 60,
    },
    
    # 双模型确认
    "dual_model": {
        "enabled": True,
        "primary_model": "gpt-4",
        "secondary_model": "claude-3-opus",
        "require_both_p0": True,
    }
}
```

---

## 问题 3：当模型没有按 Schema 返回时，系统应重试、降级还是拒绝？为什么？

### 3.1 策略矩阵

| 错误类型 | 重试 | 降级 | 拒绝 | 理由 |
|---------|-----|------|------|------|
| **JSON 格式错误** | ✅ 是 (1次) | ❌ 否 | ✅ 最终 | 可能是临时问题，重试1次 |
| **枚举值错误** | ✅ 是 (1次) | ⚠️ 可选 | ✅ 最终 | 模型可能理解错了，重试1次 |
| **缺失字段** | ✅ 是 (1次) | ❌ 否 | ✅ 最终 | 必填字段不能降级 |
| **字段长度不符** | ✅ 是 (1次) | ⚠️ 可选 | ❌ 否 | rationale 太短可以用默认值 |
| **连续失败** | ❌ 否 | ✅ 是 | ❌ 否 | 转人工分类或使用规则 |

---

### 3.2 推荐策略：**重试1次 → 降级 → 拒绝**

#### 为什么是这个顺序？

1. **重试1次**：给模型第二次机会
   - 第一次可能是网络抖动
   - 第一次可能是模型"走神"
   - 但**只重试1次**，避免浪费时间

2. **降级**：使用规则兜底
   - 总比拒绝好
   - 规则可以给出一个"保守"的分类
   - 标记需要人工审核

3. **拒绝**：最后手段
   - 无法保证质量时，拒绝比误判好
   - 避免错误分类导致更大问题

---

### 3.3 完整实现

```python
class RobustIncidentClassifier:
    """鲁棒的故障分类器（带重试和降级）"""
    
    def __init__(self, llm_client, max_retries=1):
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.system_prompt = self._load_system_prompt()
    
    def classify(
        self, 
        description: str,
        allow_fallback: bool = True
    ) -> IncidentTriage:
        """
        分类故障（带重试和降级）
        
        Args:
            description: 故障描述
            allow_fallback: 是否允许降级到规则分类
        
        Returns:
            IncidentTriage 或抛出异常
        
        Raises:
            ClassificationError: 所有尝试都失败时
        """
        
        # 第一次尝试
        try:
            return self._classify_with_llm(description)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"首次分类失败: {e}")
            
            # 重试一次
            try:
                logger.info("正在重试...")
                return self._classify_with_llm(description, retry=True)
            except (ValidationError, json.JSONDecodeError) as e2:
                logger.error(f"重试后仍失败: {e2}")
                
                # 降级到规则分类
                if allow_fallback:
                    logger.warning("降级到规则分类")
                    return self._fallback_to_rules(description, 
                                                   reason=f"LLM失败: {e2}")
                
                # 拒绝分类
                raise ClassificationError(
                    f"无法分类故障，LLM连续失败: {e}, {e2}"
                )
    
    def _classify_with_llm(
        self, 
        description: str, 
        retry: bool = False
    ) -> IncidentTriage:
        """使用 LLM 分类"""
        
        # 重试时调整 prompt（更明确）
        if retry:
            prompt = self._get_strict_prompt(description)
            temperature = 0.1  # 降低温度，更确定
        else:
            prompt = self._get_normal_prompt(description)
            temperature = 0.3
        
        response = self.llm_client.chat(
            message=prompt,
            system_prompt=self.system_prompt,
            temperature=temperature
        )
        
        # 解析 JSON
        response_text = self._extract_json(response)
        result_dict = json.loads(response_text)  # 可能抛出 JSONDecodeError
        
        # Pydantic 校验
        result = IncidentTriage(**result_dict)  # 可能抛出 ValidationError
        
        # 业务规则修正
        self._apply_business_rules(result, description)
        
        return result
    
    def _fallback_to_rules(
        self, 
        description: str,
        reason: str
    ) -> IncidentTriage:
        """
        降级：使用确定性规则分类
        
        这不是理想结果，但总比拒绝好
        """
        logger.warning(f"使用规则降级分类: {reason}")
        
        # 规则1：检测严重程度
        severity = self._rule_based_severity(description)
        
        # 规则2：检测类别
        category = self._rule_based_category(description)
        
        # 规则3：人工审核
        needs_human_review = True  # 降级的结果总是需要人工审核
        
        # 规则4：生成理由
        rationale = (
            f"[规则降级分类] 因{reason}，使用规则判断为 {severity} 级 {category} 故障。"
            f"建议人工审核。"
        )
        
        result = IncidentTriage(
            severity=severity,
            category=category,
            needs_human_review=needs_human_review,
            rationale=rationale
        )
        
        # 记录降级事件
        self._log_fallback_event(description, result, reason)
        
        return result
    
    def _rule_based_severity(self, description: str) -> str:
        """基于规则判断严重程度（保守策略）"""
        
        # 规则1：支付/交易相关 + 高错误率 → P0
        if any(kw in description for kw in ["支付", "交易", "订单"]):
            if any(kw in description for kw in ["不可用", "崩溃", "宕机"]):
                return "P0"
            if self._extract_error_rate(description) >= 20:
                return "P0"
            return "P1"  # 支付相关但不严重 → P1
        
        # 规则2：完全不可用 → P0 或 P1
        if any(kw in description for kw in ["完全不可用", "宕机", "崩溃"]):
            if any(kw in description for kw in ["主站", "登录", "注册"]):
                return "P0"
            return "P1"
        
        # 规则3：性能慢 → P2 或 P3
        if any(kw in description for kw in ["慢", "延迟", "响应时间"]):
            if "内部" in description:
                return "P3"
            return "P2"
        
        # 默认：P2（保守，需要人工审核）
        return "P2"
    
    def _rule_based_category(self, description: str) -> str:
        """基于规则判断类别"""
        
        # 优先级1：database
        db_keywords = ["MySQL", "Redis", "PostgreSQL", "MongoDB", "数据库", "OOM"]
        if any(kw in description for kw in db_keywords):
            return "database"
        
        # 优先级2：deployment
        deploy_keywords = ["部署", "发布", "配置", "CSS", "JS"]
        if any(kw in description for kw in deploy_keywords):
            return "deployment"
        
        # 优先级3：latency
        if any(kw in description for kw in ["慢", "延迟", "响应时间", "超时"]):
            return "latency"
        
        # 优先级4：availability
        if any(kw in description for kw in ["不可用", "崩溃", "宕机", "5xx", "错误率"]):
            return "availability"
        
        # 默认：unknown
        return "unknown"
    
    def _extract_error_rate(self, description: str) -> float:
        """提取错误率"""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)%', description)
        return float(match.group(1)) if match else 0.0
    
    def _get_strict_prompt(self, description: str) -> str:
        """重试时使用更严格的 prompt"""
        return f"""
请严格按照以下 JSON Schema 返回结果，不要有任何其他内容：

{{
  "severity": "P0" | "P1" | "P2" | "P3",
  "category": "availability" | "latency" | "database" | "deployment" | "unknown",
  "needs_human_review": true | false,
  "rationale": "至少20个字符的详细分类理由"
}}

故障描述：
{description}

重要：只返回 JSON，不要返回任何其他文字。
"""
    
    def _log_fallback_event(
        self, 
        description: str, 
        result: IncidentTriage,
        reason: str
    ):
        """记录降级事件（用于监控和优化）"""
        logger.critical(
            f"规则降级分类事件",
            extra={
                "description": description,
                "fallback_result": result.dict(),
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # 可选：发送到监控系统
        # metrics.increment("classification.fallback")
        # metrics.increment(f"classification.fallback.reason.{reason}")
```

---

### 3.4 为什么是这个策略？

#### ✅ 重试1次的理由

**支持重试**：
- 网络抖动：API 调用可能失败
- 模型随机性：temperature > 0 时输出有随机性
- 成本低：只增加一次 API 调用

**只重试1次**：
- 避免浪费时间：故障分类有时效性
- 避免浪费成本：GPT-4 很贵
- 连续失败说明问题不是随机的

**实测数据**（假设）：
```
首次成功率：92%
重试后成功率：96% (+4%)
二次重试成功率：96.5% (+0.5%) ← 收益递减
```

---

#### ✅ 降级的理由

**为什么要降级**：
- 总比拒绝好：规则分类虽然不完美，但能给出一个结果
- 保守策略：规则分类可以偏保守（P2 + needs_human_review=true）
- 避免阻塞：不能因为 LLM 失败就停止处理故障

**降级策略**：
- 使用规则给出"保守"的分类
- **强制** needs_human_review=true
- 在 rationale 中注明"规则降级分类"

**何时允许降级**：
- 非关键路径（如批量分类）
- 有人工审核流程
- 监控系统可以接受"保守"的分类

**何时不允许降级**：
- 自动触发 PagerDuty
- 自动执行修复操作
- 没有人工审核流程

---

#### ✅ 拒绝的理由

**何时拒绝**：
- allow_fallback=False（调用者明确要求）
- 规则也无法给出合理分类
- 涉及自动化操作（如自动触发 PagerDuty）

**拒绝优于错误分类**：
- 误报 P0 → 打断 on-call 工程师
- 漏报 P0 → 延迟响应，造成损失
- 拒绝 → 人工介入，不会出错

---

### 3.5 监控指标

```python
# 需要监控的指标
METRICS = {
    "classification.success": "首次分类成功",
    "classification.retry": "需要重试",
    "classification.retry.success": "重试后成功",
    "classification.fallback": "降级到规则",
    "classification.rejected": "拒绝分类",
    
    # 错误类型
    "classification.error.json": "JSON 格式错误",
    "classification.error.validation": "Pydantic 校验错误",
    "classification.error.enum": "枚举值错误",
    "classification.error.missing_field": "缺失字段",
}

# 告警阈值
ALERTS = {
    "fallback_rate > 10%": "降级率过高，需要优化 prompt",
    "retry_rate > 20%": "重试率过高，模型不稳定",
    "rejection_rate > 5%": "拒绝率过高，规则需要优化",
}
```

---

### 3.6 特殊情况处理

#### 情况1：JSON 格式错误但内容可解析

```python
# 模型返回了带注释的 JSON
response = """
{
  "severity": "P0",  // 这是支付故障
  "category": "availability",
  "needs_human_review": true,
  "rationale": "支付接口不可用"
}
"""

# 策略：尝试修复
def _try_fix_json(text: str) -> str:
    """尝试修复常见的 JSON 格式问题"""
    # 移除注释
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    # 移除多余的逗号
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text
```

#### 情况2：枚举值近似但不完全匹配

```python
# 模型返回 "P-0" 而不是 "P0"
response = {"severity": "P-0", ...}

# 策略：尝试映射
ENUM_MAPPING = {
    "P-0": "P0", "P-1": "P1", "P-2": "P2", "P-3": "P3",
    "p0": "P0", "p1": "P1",
    "高": "P1", "中": "P2", "低": "P3",
}

def _normalize_enum(value: str, field: str) -> str:
    """尝试标准化枚举值"""
    if field == "severity":
        return ENUM_MAPPING.get(value, value)
    return value
```

---

### 3.7 最终建议

```python
# 推荐配置
RETRY_CONFIG = {
    "max_retries": 1,  # 只重试1次
    "retry_delay": 0.5,  # 重试延迟（秒）
    "allow_fallback": True,  # 允许降级
    "fallback_severity": "P2",  # 降级默认严重程度
    "fallback_needs_review": True,  # 降级总是需要人工审核
}

# 不同场景的策略
STRATEGIES = {
    "interactive_tool": {
        "allow_fallback": True,
        "max_retries": 1,
    },
    "batch_processing": {
        "allow_fallback": True,
        "max_retries": 0,  # 批量处理不重试，节省时间
    },
    "pagerduty_trigger": {
        "allow_fallback": False,  # 不允许降级
        "max_retries": 2,  # 允许多次重试
    }
}
```

---

## 总结

### 核心原则

1. **模型负责理解，规则负责兜底**
   - 模型：自然语言理解、复杂判断
   - 规则：关键决策、高风险场景

2. **PagerDuty 触发要慎之又慎**
   - 宁可漏报 P2，不可误报 P0
   - 多层防护：阈值 + 双模型 + 人工确认

3. **重试→降级→拒绝**
   - 重试1次：给模型第二次机会
   - 降级：总比拒绝好
   - 拒绝：最后手段

4. **永远记录、监控、优化**
   - 记录所有修正
   - 监控关键指标
   - 持续优化规则和 prompt
