# Day 1 - Agent 是什么？第一个 Structured Output

**预计学习时间**: 2.5-3 小时

## 🎯 学习目标

学完今天，你将：
- 理解 Agent 与普通聊天机器人的本质区别
- 掌握让 LLM 输出结构化 JSON 的方法
- 能用 Pydantic 校验模型输出
- 完成一个能稳定分类故障的最小原型

## 📖 核心概念

### 1. Agent 是什么？

**普通聊天机器人**：
```
用户: "支付接口报错了"
机器人: "可能是网络问题，建议检查日志..."  ← 只是文字回复
```

**Agent**：
```
用户: "支付接口报错了"
Agent:
  1. 分析 → 判断为 P0 级故障                    ← 结构化决策
  2. 调用工具 → search_logs("payment")          ← 主动行动
  3. 基于证据 → "发现 5xx 35%，数据库超时..."  ← 基于事实
```

**关键区别**：
| 特性 | 聊天机器人 | Agent |
|------|-----------|-------|
| 输出 | 自由文本 | 结构化数据 + 可执行动作 |
| 能力 | 对话 | 对话 + 决策 + 行动 |
| 可靠性 | 不确定 | 可校验、可测试 |
| 集成 | 难（需要解析文本） | 易（JSON + API） |

**类比**：
- **聊天机器人** = 顾问（给建议，但你得自己执行）
- **Agent** = 助理（分析、查资料、给出可执行方案）

### 2. 为什么需要 Structured Output？

**问题场景**：你是 SRE，需要 AI 帮你对故障分级

**方案 A：自由文本输出**
```
LLM 输出: "这个问题看起来比较严重，建议尽快处理，可能需要人工介入..."
```
❌ 无法自动化：
- 不知道是 P0 还是P1
- 不知道要不要人工审核
- 无法对接告警系统

**方案 B：结构化输出（JSON）**
```json
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "支付接口 5xx 错误率 35%"
}
```
✅ 可自动化：
- 直接读取 severity 字段
- 根据 needs_human_review 决定是否通知
- 可以写入数据库、触发告警

**你的 Java 经验对比**：
```java
// 方案 A：返回字符串（难以处理）
String result = service.analyze(incident);  // "问题严重，建议..."

// 方案 B：返回结构化对象（易于处理）
IncidentResult result = service.analyze(incident);
if (result.getSeverity() == Severity.P0) {
    alertService.sendUrgentAlert(result);
}
```

### 3. 为什么需要 Schema 校验？

**LLM 可能的错误输出**：

❌ 错误 1：字段拼写错误
```json
{
  "serverity": "P0",  // 拼写错误
  "category": "availability"
}
```

❌ 错误 2：值域错误
```json
{
  "severity": "critical",  // 应该是 P0/P1/P2/P3
  "category": "database_error"  // 不在预定义类别中
}
```

❌ 错误 3：缺少字段
```json
{
  "severity": "P0"
  // 缺少 category、needs_human_review
}
```

**Pydantic 校验**（类似 Java Bean Validation）：
```python
from pydantic import BaseModel, Field
from enum import Enum

class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class IncidentResult(BaseModel):
    severity: Severity  # 只能是 P0/P1/P2/P3
    category: str
    needs_human_review: bool
    rationale: str

# 自动校验
try:
    result = IncidentResult(**llm_output)  # 解析并校验
    print(f"分类成功: {result.severity}")
except ValidationError as e:
    print(f"LLM 输出不合法: {e}")
```

**对比你熟悉的 Java**：
```java
// Pydantic 相当于 Java 的
@Data
@Validated
public class IncidentResult {
    @NotNull
    @Pattern(regexp = "P[0-3]")
    private String severity;
    
    @NotNull
    private String category;
    
    @NotNull
    private Boolean needsHumanReview;
}
```

### 4. 完整的工作流程

```
┌─────────────┐
│ 故障描述     │ "支付接口 5xx 从 0.1% 升到 35%"
└──────┬──────┘
       ↓
┌─────────────────────────────────────┐
│ Step 1: 构造 Prompt                  │
│                                     │
│ system: "你是故障分类专家..."       │
│ user: "分析这个故障: {description}" │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 2: LLM 生成 JSON                │
│                                     │
│ {                                   │
│   "severity": "P0",                 │
│   "category": "availability",       │
│   "needs_human_review": true,       │
│   "rationale": "支付 5xx 35%..."    │
│ }                                   │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 3: JSON 解析                    │
│                                     │
│ import json                         │
│ data = json.loads(llm_response)     │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 4: Pydantic 校验                │
│                                     │
│ result = IncidentResult(**data)     │
│ # 自动校验类型、值域、必需字段       │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Step 5: 使用结果                     │
│                                     │
│ if result.severity == "P0":         │
│     send_urgent_alert()             │
└─────────────────────────────────────┘
```

## 🔍 完整示例

让我们从零实现一个故障分类器：

### 步骤 1: 环境准备

```bash
# 创建项目目录
mkdir incident-classifier
cd incident-classifier

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install openai pydantic python-dotenv

# 创建配置文件
cat > .env << EOF
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1  # 或你的代理地址
EOF
```

### 步骤 2: 定义数据模型

```python
# models.py
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class Severity(str, Enum):
    """故障严重程度"""
    P0 = "P0"  # 紧急：核心功能完全不可用
    P1 = "P1"  # 高：核心功能严重受损
    P2 = "P2"  # 中：非核心功能受损
    P3 = "P3"  # 低：轻微影响

class Category(str, Enum):
    """故障类别"""
    AVAILABILITY = "availability"  # 可用性问题
    LATENCY = "latency"           # 延迟问题
    DATABASE = "database"         # 数据库问题
    DEPLOYMENT = "deployment"     # 部署问题
    UNKNOWN = "unknown"           # 未知

class IncidentResult(BaseModel):
    """故障分类结果"""
    severity: Severity
    category: Category
    needs_human_review: bool = Field(
        description="是否需要人工审核"
    )
    rationale: str = Field(
        description="判断依据，100字以内",
        max_length=200
    )
    
    class Config:
        use_enum_values = True  # 序列化时使用枚举值

# 测试
if __name__ == "__main__":
    # 合法输入
    result = IncidentResult(
        severity="P0",
        category="availability",
        needs_human_review=True,
        rationale="支付接口完全不可用"
    )
    print("✓ 校验通过:", result.json(indent=2))
    
    # 非法输入
    try:
        bad_result = IncidentResult(
            severity="critical",  # 错误：不是 P0/P1/P2/P3
            category="availability",
            needs_human_review=True,
            rationale="测试"
        )
    except Exception as e:
        print("✗ 校验失败:", e)
```

**运行测试**：
```bash
python models.py
```

**预期输出**：
```
✓ 校验通过: {
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "支付接口完全不可用"
}
✗ 校验失败: 1 validation error for IncidentResult
severity
  value is not a valid enumeration member...
```

### 步骤 3: 实现分类器

```python
# classifier.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from models import IncidentResult
from pydantic import ValidationError

load_dotenv()

class IncidentClassifier:
    """故障分类器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
    
    def classify(self, description: str) -> IncidentResult:
        """
        分类故障
        
        Args:
            description: 故障描述
            
        Returns:
            结构化的分类结果
            
        Raises:
            ValidationError: LLM 输出不符合 schema
        """
        # 构造 Prompt
        system_prompt = """你是一个故障分类专家。

你的任务是分析故障描述，输出结构化的 JSON。

严重程度判断标准：
- P0（紧急）：核心功能完全不可用，如支付、登录全部失败
- P1（高）：核心功能严重受损，如 50% 用户无法支付
- P2（中）：非核心功能受损，如推荐系统延迟
- P3（低）：轻微影响，如日志告警

类别：
- availability: 服务不可用、5xx 错误
- latency: 延迟过高、超时
- database: 数据库连接、死锁
- deployment: 发布后异常
- unknown: 无法确定

输出格式（JSON）：
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "判断依据"
}

只输出 JSON，不要其他文字。"""

        user_prompt = f"分析以下故障并分类：\n\n{description}"
        
        # 调用 LLM
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # 降低随机性
            response_format={"type": "json_object"}  # 强制 JSON 输出
        )
        
        # 解析响应
        response_text = response.choices[0].message.content
        
        try:
            # JSON 解析
            data = json.loads(response_text)
            
            # Pydantic 校验
            result = IncidentResult(**data)
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"原始输出: {response_text}")
            raise
            
        except ValidationError as e:
            print(f"Schema 校验失败: {e}")
            print(f"LLM 输出: {data}")
            raise

# 测试
if __name__ == "__main__":
    classifier = IncidentClassifier()
    
    # 测试案例 1: 支付故障
    description1 = "支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟"
    result1 = classifier.classify(description1)
    print("\n案例 1:")
    print(f"描述: {description1}")
    print(f"严重程度: {result1.severity}")
    print(f"类别: {result1.category}")
    print(f"需要审核: {result1.needs_human_review}")
    print(f"依据: {result1.rationale}")
    
    # 测试案例 2: 推荐延迟
    description2 = "推荐系统 P99 延迟从 500ms 升至 2 秒"
    result2 = classifier.classify(description2)
    print("\n案例 2:")
    print(f"描述: {description2}")
    print(f"严重程度: {result2.severity}")
    print(f"类别: {result2.category}")
    print(f"需要审核: {result2.needs_human_review}")
    print(f"依据: {result2.rationale}")
```

**运行测试**：
```bash
python classifier.py
```

### 步骤 4: 添加测试

```python
# test_classifier.py
from classifier import IncidentClassifier
from models import IncidentResult

def test_payment_5xx():
    """测试支付 5xx 故障分类"""
    classifier = IncidentClassifier()
    
    description = "支付接口 5xx 从 0.1% 升到 35%"
    result = classifier.classify(description)
    
    # 断言
    assert result.severity in ["P0", "P1"], f"支付高错误率应该是 P0 或 P1，实际: {result.severity}"
    assert result.needs_human_review == True, "支付故障必须人工审核"
    assert "5xx" in result.rationale or "35%" in result.rationale, "依据应包含关键信息"
    
    print("✓ 测试通过: 支付 5xx 故障")

def test_recommendation_latency():
    """测试推荐延迟分类"""
    classifier = IncidentClassifier()
    
    description = "推荐系统 P99 延迟从 500ms 升至 2 秒"
    result = classifier.classify(description)
    
    # 推荐系统不是核心功能，应该是 P2 或 P3
    assert result.severity in ["P2", "P3"], f"推荐延迟应该是 P2 或 P3，实际: {result.severity}"
    assert result.category in ["latency", "availability"], "应该识别为延迟或可用性问题"
    
    print("✓ 测试通过: 推荐延迟")

def test_schema_validation():
    """测试 Schema 校验"""
    from pydantic import ValidationError
    
    # 测试非法输入
    try:
        IncidentResult(
            severity="critical",  # 非法值
            category="availability",
            needs_human_review=True,
            rationale="测试"
        )
        assert False, "应该抛出 ValidationError"
    except ValidationError:
        print("✓ 测试通过: Schema 校验")

if __name__ == "__main__":
    test_schema_validation()
    test_payment_5xx()
    test_recommendation_latency()
    print("\n✅ 所有测试通过！")
```

**运行测试**：
```bash
python test_classifier.py
```

## 💪 动手练习

### Level 1: 最低完成线（30 分钟）

**任务**：
- [ ] 完成上面的完整示例
- [ ] 成功运行 `python classifier.py`
- [ ] 看到 LLM 输出的结构化 JSON

**验证**：能稳定输出 JSON，不报错

### Level 2: 标准任务（1 小时）

**任务**：
1. 准备 3 个测试案例：
   - 数据库死锁
   - 部署后异常
   - 日志告警（P3）

2. 运行分类器并手动检查结果：
   ```python
   cases = [
       "MySQL 报 deadlock，1205 错误",
       "灰度发布后 10% 用户报 404",
       "告警：磁盘使用率 85%"
   ]
   
   for desc in cases:
       result = classifier.classify(desc)
       print(f"\n描述: {desc}")
       print(f"分类: {result.severity} / {result.category}")
       print(f"依据: {result.rationale}")
   ```

3. 判断结果是否合理：
   - 数据库死锁应该是 P0 或 P1
   - 部署异常应该是 P1 或 P2
   - 磁盘告警应该是 P3

**验证**：3 个案例分类合理

### Level 3: 进阶任务（1 小时）

**任务**：
1. 扩展测试到 10 个案例，覆盖所有严重程度和类别

2. 写自动化断言测试（参考 `test_classifier.py`）

3. 记录至少 2 个失败案例：
   - LLM 分类错误（如把 P0 判断为 P2）
   - 输出格式不对（JSON 解析失败）
   
   创建 `failures.md` 记录：
   ```markdown
   # 失败案例
   
   ## 案例 1: 低估严重程度
   - 描述: "支付接口全部 503"
   - 期望: P0
   - 实际: P1
   - 原因: Prompt 中 P0 定义不够明确
   - 修复: 强调"完全不可用"关键词
   ```

**验证**：
- 10 个案例的自动化测试
- `failures.md` 文件

## 🐛 常见问题

### Q1: JSON 解析失败

**问题**：
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**原因**：LLM 输出了额外文字
```
让我分析一下...

{
  "severity": "P0",
  ...
}
```

**解决**：
1. 在 Prompt 中强调"只输出 JSON"
2. 使用 `response_format={"type": "json_object"}`（OpenAI）
3. 或手动提取 JSON：
```python
import re
json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
if json_match:
    data = json.loads(json_match.group())
```

### Q2: Schema 校验失败

**问题**：
```
ValidationError: 1 validation error for IncidentResult
severity
  value is not a valid enumeration member
```

**原因**：LLM 输出了 `"critical"` 而不是 `"P0"`

**解决**：
1. 在 Prompt 中明确列出合法值
2. 在 System Prompt 中给出示例输出
3. 降低 temperature（减少创造性）

### Q3: 分类不准确

**问题**：把 P0 故障判断为 P2

**解决**：
1. 优化 Prompt，提供更详细的判断标准
2. 给出 few-shot 示例
3. 明天会学习用 Policy 规则兜底

### Q4: API 调用失败

**问题**：
```
openai.APIConnectionError: Connection error
```

**解决**：
1. 检查 `.env` 配置
2. 检查网络连接
3. 检查 API key 是否有效
4. 尝试降低模型（gpt-3.5-turbo 更便宜）

## ✅ 完成检查清单

今天学完，你应该能回答：

- [ ] Agent 和聊天机器人的区别是什么？
- [ ] 为什么需要 Structured Output？
- [ ] Pydantic 的作用是什么？
- [ ] 如何构造 Prompt 让 LLM 输出 JSON？
- [ ] 如何处理 JSON 解析失败？
- [ ] 如何校验 LLM 输出的合法性？

实践检查：

- [ ] 能成功调用 LLM API
- [ ] 能稳定得到 JSON 输出
- [ ] 能用 Pydantic 校验结果
- [ ] 测试了至少 3 个案例
- [ ] 记录了失败案例

## 📚 延伸阅读（可选）

**Pydantic 文档**：
- https://docs.pydantic.dev/

**OpenAI Function Calling**（明天会用）：
- https://platform.openai.com/docs/guides/function-calling

**Prompt Engineering**：
- https://www.promptingguide.ai/

## 🎯 明天预告

**Day 2: 为什么需要 Policy 规则？**

今天我们相信 LLM 的输出，但实际上：
- LLM 会犯错（把 P0 判断为 P2）
- LLM 会忘记规则（支付故障不标记人工审核）
- LLM 不了解业务规则（内部工具不应该是 P0）

明天你会学习：
- 如何用确定性规则兜底
- 什么该信任模型，什么该强制执行
- 实现一个 Policy Engine

今天先休息，明天见！🚀
