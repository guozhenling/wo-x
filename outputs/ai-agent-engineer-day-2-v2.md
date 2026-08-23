# Day 2 - 为什么需要 Policy 规则？

**预计学习时间**: 2.5-3 小时

## 🎯 学习目标

学完今天，你将：
- 理解为什么不能完全信任 LLM 输出
- 掌握确定性规则与模型判断的边界
- 能实现一个 Policy Engine
- 知道什么该让模型做，什么该用代码强制

## 📖 核心概念

### 1. 模型会犯什么错？

**昨天的问题**：我们完全信任 LLM 的输出

```python
result = classifier.classify(description)
# 直接使用，没有任何校验
if result.severity == "P0":
    send_urgent_alert()
```

**实际生产中的问题**：

❌ **错误 1: 低估严重程度**
```python
描述: "支付接口完全不可用，所有用户无法支付"
LLM 输出: severity="P1"  # 错了！应该是 P0
实际影响: 未触发紧急告警，损失 100 万
```

❌ **错误 2: 忘记标记人工审核**
```python
描述: "检测到用户数据泄露"
LLM 输出: needs_human_review=False  # 错了！数据安全必须人工审核
实际影响: 自动处理，未上报，违反合规要求
```

❌ **错误 3: 不了解业务规则**
```python
描述: "内部监控工具响应缓慢"
LLM 输出: severity="P0"  # 错了！内部工具不应该是 P0
实际影响: 触发不必要的紧急流程
```

**根本原因**：
1. LLM 是**概率模型**，不是确定性系统
2. LLM 不了解你的**业务规则**
3. LLM 会被**Prompt 注入**攻击

### 2. Policy 规则是什么？

**定义**：在模型输出基础上，用确定性代码强制执行的业务规则

**类比你熟悉的 Java**：
```java
// 模型 = Service 层（业务逻辑，可能有 bug）
IncidentResult result = llmService.classify(description);

// Policy = Validator/Interceptor（强制校验）
if (result.getSeverity() == Severity.P0 && 
    !result.isNeedsHumanReview()) {
    // 强制修正
    result.setNeedsHumanReview(true);
    log.warn("P0 must require human review");
}

// 类似于 Spring 的 @Validated 或拦截器
```

**工作流程**：
```
用户输入
   ↓
LLM 分析 → 初步结果
   ↓
Policy Engine 检查
   ↓
├─ 规则 1: P0/P1 必须人工审核 ✓
├─ 规则 2: 支付故障错误率 > 20% 必须 P0 ✓
├─ 规则 3: 内部工具不应该是 P0 ✓
   ↓
最终结果（可靠）
```

### 3. 什么该用规则？什么该用模型？

**模型擅长**（模糊判断）：
- ✅ 从自然语言提取信息
- ✅ 判断故障类别（availability/latency/database）
- ✅ 生成人类可读的依据
- ✅ 初步的严重程度判断

**规则擅长**（硬性要求）：
- ✅ 业务规则（支付故障必须 P0）
- ✅ 安全规则（数据泄露必须人工审核）
- ✅ 合规要求（P0/P1 必须上报）
- ✅ 一致性保证（P0 必须设置 needs_human_review）

**决策边界**：
| 场景 | 用什么 | 原因 |
|------|--------|------|
| 识别"支付"关键词 | 模型 | 可能有多种表达方式 |
| 支付故障 → P0 | 规则 | 业务硬性要求 |
| 判断是否延迟问题 | 模型 | 需要理解语义 |
| P0 → 人工审核 | 规则 | 不容商量 |

**原则**：
- **模型做模糊判断**，规则守底线
- **规则处理高风险**，模型处理一般情况
- **规则可测试**，模型需要监控

### 4. Policy 规则的优先级

**场景**：规则之间可能冲突

```python
LLM 输出: severity="P2", category="availability"
描述: "支付接口 5xx 错误率 30%"

规则冲突:
- 规则 A: 支付故障 → P0
- 规则 B: P2 不需要人工审核

哪个优先？
```

**优先级设计**：
```
CRITICAL (关键) > HIGH (高) > MEDIUM (中) > LOW (低)

例子:
1. [CRITICAL] P0/P1 必须人工审核
2. [CRITICAL] 支付错误率 >= 20% 必须 P0
3. [HIGH] 内部工具最高 P2
4. [MEDIUM] category=unknown 时标记证据不足
```

**执行顺序**：
```python
result = llm_classify(description)

# 按优先级执行规则
result = policy.enforce_critical_rules(result)
result = policy.enforce_high_rules(result)
result = policy.enforce_medium_rules(result)

return result
```

## 🔍 完整示例

让我们在昨天的分类器基础上添加 Policy Engine：

### 步骤 1: 定义规则结构

```python
# policy.py
from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass
import re

class PolicyLevel(Enum):
    """规则优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class PolicyAction(Enum):
    """规则动作"""
    ENFORCE = "enforce"  # 强制修改
    WARN = "warn"        # 记录警告
    REJECT = "reject"    # 拒绝

@dataclass
class PolicyViolation:
    """规则违反记录"""
    policy_name: str
    level: PolicyLevel
    action: PolicyAction
    message: str
    original_value: Any
    corrected_value: Any

class PolicyEngine:
    """规则引擎"""
    
    def __init__(self):
        self.violations: List[PolicyViolation] = []
    
    def check_and_enforce(
        self,
        description: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查并执行所有规则
        
        Args:
            description: 故障描述
            result: LLM 的原始输出
            
        Returns:
            修正后的结果
        """
        self.violations.clear()
        
        # 规则 1: 高优先级必须人工审核
        result = self._enforce_high_priority_review(result)
        
        # 规则 2: 支付故障高优先级
        result = self._enforce_payment_priority(result, description)
        
        # 规则 3: 内部工具优先级限制
        result = self._enforce_internal_tool_limit(result, description)
        
        # 记录违反
        if self.violations:
            print(f"\n⚠️  检测到 {len(self.violations)} 个规则违反:")
            for v in self.violations:
                print(f"  [{v.level.value}] {v.policy_name}: {v.message}")
        
        return result
    
    def _enforce_high_priority_review(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        规则 1: P0 和 P1 必须人工审核
        
        这是硬性要求，不容商量
        """
        severity = result.get('severity')
        needs_review = result.get('needs_human_review')
        
        if severity in ['P0', 'P1'] and not needs_review:
            self.violations.append(PolicyViolation(
                policy_name="高优先级必须人工审核",
                level=PolicyLevel.CRITICAL,
                action=PolicyAction.ENFORCE,
                message=f"{severity} 级别必须人工审核",
                original_value=needs_review,
                corrected_value=True
            ))
            
            result['needs_human_review'] = True
            print(f"🔧 强制修正: {severity} 必须人工审核")
        
        return result
    
    def _enforce_payment_priority(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 2: 支付相关故障必须高优先级
        
        关键词: 支付、交易、订单、结算、payment
        错误率 >= 20%: 必须 P0
        """
        payment_keywords = ["支付", "交易", "订单", "结算", "payment"]
        severity = result.get('severity')
        
        # 检查是否是支付相关
        if any(kw in description for kw in payment_keywords):
            # 提取错误率
            error_rate = self._extract_error_rate(description)
            
            if error_rate >= 20 and severity != 'P0':
                self.violations.append(PolicyViolation(
                    policy_name="支付高错误率必须P0",
                    level=PolicyLevel.CRITICAL,
                    action=PolicyAction.ENFORCE,
                    message=f"支付错误率 {error_rate}% >= 20%，必须 P0",
                    original_value=severity,
                    corrected_value='P0'
                ))
                
                result['severity'] = 'P0'
                result['needs_human_review'] = True
                print(f"🔧 强制修正: 支付高错误率提升为 P0")
        
        return result
    
    def _enforce_internal_tool_limit(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 3: 内部工具不应该是 P0/P1
        
        关键词: 内部、监控、管理后台、工具
        """
        internal_keywords = ["内部", "监控工具", "管理后台", "内部系统"]
        severity = result.get('severity')
        
        if any(kw in description for kw in internal_keywords):
            if severity in ['P0', 'P1']:
                self.violations.append(PolicyViolation(
                    policy_name="内部工具优先级限制",
                    level=PolicyLevel.HIGH,
                    action=PolicyAction.ENFORCE,
                    message=f"内部工具不应该是 {severity}，降级为 P2",
                    original_value=severity,
                    corrected_value='P2'
                ))
                
                result['severity'] = 'P2'
                print(f"🔧 强制修正: 内部工具降级为 P2")
        
        return result
    
    def _extract_error_rate(self, description: str) -> float:
        """
        从描述中提取错误率
        
        例子: "5xx 从 0.1% 升到 35%" -> 35.0
        """
        match = re.search(r'升到\s*(\d+(?:\.\d+)?)%', description)
        if match:
            return float(match.group(1))
        
        match = re.search(r'错误率\s*(\d+(?:\.\d+)?)%', description)
        if match:
            return float(match.group(1))
        
        return 0.0
    
    def get_violations(self) -> List[PolicyViolation]:
        """获取所有规则违反记录"""
        return self.violations

# 测试
if __name__ == "__main__":
    policy = PolicyEngine()
    
    # 测试 1: P0 未标记人工审核
    print("测试 1: P0 未标记人工审核")
    result1 = {
        "severity": "P0",
        "category": "availability",
        "needs_human_review": False,  # 错误！
        "rationale": "支付接口完全不可用"
    }
    result1 = policy.check_and_enforce("支付接口 503", result1)
    assert result1['needs_human_review'] == True
    print("✓ 已修正\n")
    
    # 测试 2: 支付高错误率
    print("测试 2: 支付高错误率")
    result2 = {
        "severity": "P1",  # 错误！应该是 P0
        "category": "availability",
        "needs_human_review": True,
        "rationale": "支付接口错误"
    }
    result2 = policy.check_and_enforce("支付接口 5xx 从 0.1% 升到 35%", result2)
    assert result2['severity'] == 'P0'
    print("✓ 已修正\n")
    
    # 测试 3: 内部工具
    print("测试 3: 内部工具")
    result3 = {
        "severity": "P0",  # 错误！内部工具不应该是 P0
        "category": "latency",
        "needs_human_review": True,
        "rationale": "监控工具慢"
    }
    result3 = policy.check_and_enforce("内部监控工具响应慢", result3)
    assert result3['severity'] == 'P2'
    print("✓ 已修正\n")
    
    print("✅ 所有测试通过！")
```

**运行测试**：
```bash
python policy.py
```

### 步骤 2: 集成到分类器

```python
# classifier_with_policy.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from models import IncidentResult
from policy import PolicyEngine

load_dotenv()

class IncidentClassifier:
    """带 Policy 的故障分类器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.policy = PolicyEngine()
    
    def classify(self, description: str) -> IncidentResult:
        """
        分类故障（带 Policy 校验）
        
        流程:
        1. LLM 初步分类
        2. Policy 规则检查和修正
        3. 返回最终结果
        """
        # Step 1: LLM 初步分类
        llm_result = self._call_llm(description)
        print(f"\n📋 LLM 原始输出:")
        print(f"  severity: {llm_result['severity']}")
        print(f"  needs_human_review: {llm_result['needs_human_review']}")
        
        # Step 2: Policy 规则检查
        final_result = self.policy.check_and_enforce(description, llm_result)
        
        # Step 3: 转换为 Pydantic 模型
        result = IncidentResult(**final_result)
        
        # 显示最终结果
        if self.policy.get_violations():
            print(f"\n✅ 最终输出（经 Policy 修正）:")
            print(f"  severity: {result.severity}")
            print(f"  needs_human_review: {result.needs_human_review}")
        else:
            print(f"\n✅ 最终输出（无需修正）")
        
        return result
    
    def _call_llm(self, description: str) -> dict:
        """调用 LLM（与昨天相同）"""
        system_prompt = """你是故障分类专家。

严重程度：
- P0: 核心功能完全不可用
- P1: 核心功能严重受损
- P2: 非核心功能受损
- P3: 轻微影响

输出 JSON:
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "判断依据"
}"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"分析: {description}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

# 测试
if __name__ == "__main__":
    classifier = IncidentClassifier()
    
    # 案例 1: 支付高错误率（会被 Policy 修正）
    print("=" * 60)
    print("案例 1: 支付高错误率")
    print("=" * 60)
    result1 = classifier.classify("支付接口 5xx 从 0.1% 升到 35%")
    print(f"\n最终: {result1.severity} / {result1.category}")
    print(f"依据: {result1.rationale}")
    
    # 案例 2: 推荐延迟（不会被 Policy 修正）
    print("\n" + "=" * 60)
    print("案例 2: 推荐延迟")
    print("=" * 60)
    result2 = classifier.classify("推荐系统 P99 延迟从 500ms 升至 2 秒")
    print(f"\n最终: {result2.severity} / {result2.category}")
```

**运行测试**：
```bash
python classifier_with_policy.py
```

### 步骤 3: 单元测试（不调用 LLM）

```python
# test_policy.py
import pytest
from policy import PolicyEngine

class TestPolicyEngine:
    """Policy Engine 单元测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.policy = PolicyEngine()
    
    def test_p0_must_have_review(self):
        """测试: P0 必须人工审核"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": False,  # 错误
            "rationale": "测试"
        }
        
        result = self.policy.check_and_enforce("测试故障", result)
        
        assert result['needs_human_review'] == True
        assert len(self.policy.get_violations()) == 1
        assert self.policy.get_violations()[0].policy_name == "高优先级必须人工审核"
    
    def test_payment_high_error_rate(self):
        """测试: 支付高错误率必须 P0"""
        result = {
            "severity": "P1",  # 应该提升为 P0
            "category": "availability",
            "needs_human_review": True,
            "rationale": "测试"
        }
        
        result = self.policy.check_and_enforce(
            "支付接口 5xx 升到 30%",
            result
        )
        
        assert result['severity'] == 'P0'
        assert len(self.policy.get_violations()) == 1
    
    def test_internal_tool_downgrade(self):
        """测试: 内部工具降级"""
        result = {
            "severity": "P0",  # 应该降级为 P2
            "category": "latency",
            "needs_human_review": True,
            "rationale": "测试"
        }
        
        result = self.policy.check_and_enforce(
            "内部监控工具响应慢",
            result
        )
        
        assert result['severity'] == 'P2'
    
    def test_no_violation(self):
        """测试: 正确的输出不触发规则"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,  # 正确
            "rationale": "测试"
        }
        
        result = self.policy.check_and_enforce("主站宕机", result)
        
        assert len(self.policy.get_violations()) == 0
    
    def test_extract_error_rate(self):
        """测试: 错误率提取"""
        assert self.policy._extract_error_rate("5xx 升到 35%") == 35.0
        assert self.policy._extract_error_rate("错误率 20.5%") == 20.5
        assert self.policy._extract_error_rate("没有数字") == 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**运行测试**：
```bash
pip install pytest
pytest test_policy.py -v
```

## 💪 动手练习

### Level 1: 最低完成线（30 分钟）

**任务**：
- [ ] 完成上面的 `policy.py`
- [ ] 运行测试，看到 3 个规则生效
- [ ] 理解每条规则的作用

**验证**：能看到规则修正输出

### Level 2: 标准任务（1 小时）

**任务**：
1. 准备 8 条测试案例，覆盖：
   - 支付 5xx（高错误率）
   - 数据库死锁
   - 部署后异常
   - 内部工具问题
   - 数据泄露（安全）
   - 推荐延迟
   - 日志告警
   - 正常案例

2. 对每个案例：
   - 运行分类器
   - 记录 LLM 原始输出
   - 记录 Policy 修正后输出
   - 判断是否合理

3. 创建对比表格：
   ```markdown
   | 描述 | LLM输出 | Policy修正 | 最终结果 |
   |------|---------|-----------|----------|
   | 支付5xx 35% | P1 | P0 | P0 ✓ |
   | 内部监控慢 | P0 | P2 | P2 ✓ |
   ```

**验证**：8 个案例的对比表格

### Level 3: 进阶任务（1 小时）

**任务**：
1. 添加 2 条新规则：
   ```python
   # 规则 4: 数据安全必须人工审核
   # 关键词: 数据泄露、SQL注入、XSS、权限
   
   # 规则 5: category=unknown 时
   # rationale 必须包含"证据不足"
   ```

2. 写单元测试（`pytest`）覆盖所有 5 条规则

3. 记录失败案例到 `failures.md`：
   - LLM 犯的错误
   - Policy 如何修正
   - 为什么需要这条规则

**验证**：
- 5 条规则都有测试
- `failures.md` 记录 2+ 个案例

## 🐛 常见问题

### Q1: 规则太严格了

**问题**：正常案例也被修正

**解决**：
1. 检查关键词匹配是否过于宽泛
2. 添加错误率阈值
3. 考虑规则的适用条件

### Q2: 规则之间冲突

**问题**：规则 A 说提升，规则 B 说降级

**解决**：
1. 设置规则优先级
2. 按 CRITICAL > HIGH > MEDIUM 顺序执行
3. 后执行的规则可以覆盖前面的

### Q3: 如何测试规则？

**答案**：单元测试（不调用 LLM）
```python
def test_rule():
    policy = PolicyEngine()
    result = {"severity": "P1", ...}
    result = policy.check_and_enforce("描述", result)
    assert result['severity'] == 'P0'
```

### Q4: 规则太多了怎么办？

**答案**：
1. 只保留关键规则（3-5 条）
2. 定期review，删除不再触发的规则
3. 通过监控数据决定保留哪些

## ✅ 完成检查清单

概念理解：
- [ ] 知道模型会犯什么错
- [ ] 理解 Policy 的作用
- [ ] 知道什么该用规则，什么该用模型
- [ ] 理解规则优先级

实践检查：
- [ ] 实现了 PolicyEngine
- [ ] 至少 3 条规则
- [ ] 单元测试覆盖所有规则
- [ ] 集成到分类器
- [ ] 测试了 8 个案例

## 📚 延伸阅读（可选）

**Guard Rails for LLM**：
- https://www.guardrailsai.com/

**Prompt Injection 攻击**：
- https://simonwillison.net/2023/Apr/14/worst-that-can-happen/

## 🎯 明天预告

**Day 3: 第一个工具 - 日志搜索**

今天我们有了可靠的分类器，但它只能"猜测"：
- "可能是数据库问题"
- "建议查看日志"

明天你会学习：
- 如何实现一个只读工具 `search_logs`
- 什么是幂等性
- 工具的安全边界

有了工具，Agent 就能"查证据"而不是"瞎猜"！

休息一下，明天见！🚀
