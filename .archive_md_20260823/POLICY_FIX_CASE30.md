# Policy 规则优化 - Case 30 修复报告

## 🐛 问题描述

**Case 30** 在测试中失败：

```python
TestCase(
    id=30,
    description="第三方支付渠道偶尔超时，切换备用渠道后成功，整体成功率 97%",
    expected_severity="P2",
    expected_human_review=False,
    tags=["payment_5xx"]
)
```

**实际结果**：被 Policy 规则强制提升为 P1

**期望结果**：保持 P2

## 🔍 根本原因分析

### 问题 1: 规则过于严格

**规则 3 (旧版本)**: 影响收入的故障必须高优先级
```python
if any(kw in description for kw in revenue_keywords):
    error_rate = self._extract_error_rate(description)
    
    if error_rate >= 20:
        # 提升为 P0
    elif severity in ['P2', 'P3']:
        # 强制提升为 P1  ← 问题在这里
```

**问题**：只要包含"支付"等关键词，所有 P2/P3 都会被强制提升为 P1，不考虑实际影响程度。

### 问题 2: 错误率提取不准确

**旧版本**:
```python
def _extract_error_rate(self, description: str) -> float:
    match = re.search(r'(\d+(?:\.\d+)?)%', description)
    return float(match.group(1)) if match else 0.0
```

**问题**：
- "整体成功率 97%" 被错误提取为错误率 97%
- 没有区分"成功率"和"错误率"
- 只匹配第一个百分比，可能不准确

## ✅ 修复方案

### 修复 1: 优化规则 3 - 增加错误率阈值

```python
def _enforce_revenue_impact(self, result, description):
    """
    规则 3：影响收入的故障必须高优先级
    
    根据错误率判断：
    - 错误率 >= 20%: 必须 P0
    - 错误率 >= 5%:  至少 P1
    - 错误率 < 5%:   可以是 P2（有降级处理的情况）
    """
    revenue_keywords = ["支付", "交易", "订单", "结算", "payment", "transaction"]
    severity = result.get('severity')

    if any(kw in description for kw in revenue_keywords):
        error_rate = self._extract_error_rate(description)

        # 高错误率：>= 20%，必须 P0
        if error_rate >= 20:
            if severity != 'P0':
                # 强制提升为 P0
                
        # 中等错误率：>= 5%，至少 P1
        elif error_rate >= 5:
            if severity in ['P2', 'P3']:
                # 强制提升为 P1
                
        # 低错误率：< 5%，可以是 P2
        # 不强制提升
```

**改进点**：
- ✅ 增加 5% 错误率阈值
- ✅ 低于 5% 不强制提升
- ✅ 考虑有降级处理的场景

### 修复 2: 改进错误率提取逻辑

```python
def _extract_error_rate(self, description: str) -> float:
    """
    提取错误率百分比
    
    注意：
    - "错误率 30%" -> 30
    - "成功率 97%" -> 3 (反向计算)
    - "5xx 升到 35%" -> 35
    """
    # 1. 先检查是否明确提到错误率
    error_match = re.search(r'错误率\s*[：:]\s*(\d+(?:\.\d+)?)%', description)
    if error_match:
        return float(error_match.group(1))

    # 2. 检查是否提到成功率（需要反向计算）
    success_match = re.search(r'成功率\s*[：:]\s*(\d+(?:\.\d+)?)%', description)
    if success_match:
        success_rate = float(success_match.group(1))
        return 100.0 - success_rate

    # 3. 检查整体成功率的表述
    success_match2 = re.search(r'整体成功率\s*(\d+(?:\.\d+)?)%', description)
    if success_match2:
        success_rate = float(success_match2.group(1))
        return 100.0 - success_rate

    # 4. 检查 5xx 升到 xx%、从 xx% 升到 yy% 等模式
    increase_match = re.search(r'(?:升到|升至|达到)\s*(\d+(?:\.\d+)?)%', description)
    if increase_match:
        return float(increase_match.group(1))

    # 5. 检查 "影响 xx% 用户"、"xx% 用户" 等模式
    impact_match = re.search(r'(?:影响|超时|失败).*?(\d+(?:\.\d+)?)%', description)
    if impact_match:
        return float(impact_match.group(1))

    # 6. 最后才用通用匹配（第一个百分比）
    general_match = re.search(r'(\d+(?:\.\d+)?)%', description)
    if general_match:
        return float(general_match.group(1))

    return 0.0
```

**改进点**：
- ✅ 优先匹配明确的错误率表述
- ✅ 识别成功率并反向计算
- ✅ 支持多种错误率表达方式
- ✅ 按优先级匹配，更准确

## 📊 验证测试

创建了 `tests/test_policy_fix.py` 进行验证：

### 测试用例

| 描述 | 错误率 | 期望 | 结果 |
|------|--------|------|------|
| 支付接口 5xx 升到 35% | 35% | P0 | ✓ 通过 |
| 5% 用户支付超时 | 5% | P1 | ✓ 通过 |
| 整体成功率 97% | 3% | P2 | ✓ 通过 |
| 支付系统响应缓慢 | 0% | P2 | ✓ 通过 |
| 推荐系统错误率 30% | 30% | P2 | ✓ 通过 |

### 测试结果

```bash
python3 tests/test_policy_fix.py

================================================================================
测试结果汇总
================================================================================
✓ 支付高错误率 35%
✓ 支付中等错误率 8%
✓ 支付低错误率 3%
✓ 支付问题但无错误率
✓ 非收入相关高错误率

通过率: 5/5 (100%)

================================================================================
专门测试 Case 30
================================================================================

描述: 第三方支付渠道偶尔超时，切换备用渠道后成功，整体成功率 97%
初始结果: severity=P2, needs_human_review=False

规则检查后: severity=P2, needs_human_review=False

✓ 没有规则违反

✓ Case 30 测试通过！
```

## 🎯 修复效果

### Case 30 分析

**描述**：第三方支付渠道偶尔超时，切换备用渠道后成功，整体成功率 97%

**关键信息**：
- 包含"支付"关键词 ✓
- 成功率 97% = 错误率 3%
- 有降级处理（切换备用渠道）
- 整体影响可控

**修复前**：
- Policy 检测到"支付"关键词
- 强制提升为 P1 ❌
- 不符合实际情况

**修复后**：
- Policy 检测到"支付"关键词
- 提取错误率：97% -> 3%（成功率反向计算）
- 错误率 3% < 5%，不强制提升
- 保持 P2 ✓

## 📋 影响范围

### 受益的案例

所有包含收入关键词的低错误率故障：

1. **Case 30**: 第三方支付渠道偶尔超时，成功率 97%
   - 修复前: 强制 P1
   - 修复后: 保持 P2 ✓

2. **未来案例**: 任何错误率 < 5% 的支付相关故障
   - 例如：支付系统响应慢但可用
   - 例如：第三方接口偶尔超时但有重试

### 不受影响的案例

高错误率和中等错误率的案例仍然会被正确提升：

1. **Case 1**: 支付接口 5xx 升到 35%
   - 错误率 35% >= 20%
   - 仍然强制 P0 ✓

2. **Case 24**: 5% 用户支付超时
   - 错误率 5% >= 5%
   - 仍然强制 P1 ✓

## 🎓 规则优化原则

这次优化体现了以下原则：

### 1. 考虑实际影响
- ✅ 不仅看关键词，还要看错误率
- ✅ 低错误率 + 降级处理 = 影响可控

### 2. 梯度判断
- ✅ 高错误率 (>= 20%): P0 - 紧急
- ✅ 中等错误率 (>= 5%): P1 - 高优先级
- ✅ 低错误率 (< 5%): 不强制提升 - 视情况而定

### 3. 准确提取信息
- ✅ 区分"成功率"和"错误率"
- ✅ 多种匹配模式，提高准确性
- ✅ 按优先级匹配，避免误判

## 📝 建议

### 对测试案例的建议

如果有类似的低错误率支付场景，可以：
1. 明确标注错误率或成功率
2. 说明是否有降级处理
3. 描述整体影响程度

### 对规则的未来优化

1. **考虑持续时间**
   - 短时间高错误率 vs 长时间低错误率
   - 可能需要不同的判断策略

2. **考虑趋势**
   - 错误率上升 vs 错误率下降
   - 上升趋势可能需要更高优先级

3. **考虑服务类型**
   - 核心支付 vs 第三方支付
   - 可能需要不同的阈值

## 🎉 总结

### 问题
- ✗ Case 30 被错误地强制提升为 P1
- ✗ 规则过于严格，不考虑错误率
- ✗ 错误率提取不准确

### 修复
- ✅ 增加 5% 错误率阈值
- ✅ 低错误率不强制提升
- ✅ 改进错误率提取逻辑

### 效果
- ✅ Case 30 测试通过
- ✅ 所有验证测试通过 (5/5)
- ✅ 规则更智能、更合理

---

**修复日期**: 2026-08-20  
**影响文件**: `src/policy.py`, `tests/test_policy_fix.py`  
**测试通过率**: 100% (5/5)  
**状态**: ✅ 已完成并验证
