# 安全设计文档

## 核心原则

**绝不直接信任 LLM 输出**

本项目采用多层防护机制，确保 AI 模型输出的可靠性和安全性。

## 多层校验架构

```
用户输入
   ↓
LLM 分类
   ↓
┌─────────────────────────────────┐
│ 第一层：JSON 格式校验            │
│ - 确保返回的是有效 JSON          │
│ - 处理 markdown 代码块包裹       │
└─────────────────────────────────┘
   ↓
┌─────────────────────────────────┐
│ 第二层：Pydantic Schema 校验     │
│ - 枚举值严格匹配                 │
│ - 类型强制检查                   │
│ - 必填字段验证                   │
│ - 字段长度限制                   │
└─────────────────────────────────┘
   ↓
┌─────────────────────────────────┐
│ 第三层：业务逻辑一致性校验        │
│ - P0/P1 必须人工审核             │
│ - P3 不应该人工审核              │
│ - 自动修正逻辑冲突               │
└─────────────────────────────────┘
   ↓
安全的分类结果
```

## 具体防护措施

### 1. Pydantic 强类型校验

使用 `Literal` 类型确保枚举值严格匹配：

```python
class IncidentTriage(BaseModel):
    severity: Literal["P0", "P1", "P2", "P3"]  # 只能是这4个值
    category: Literal["availability", "latency", "database", "deployment", "unknown"]
    needs_human_review: bool  # 严格布尔类型
    rationale: str = Field(min_length=10, max_length=500)  # 长度限制
```

**防护效果**：
- ❌ `severity="P5"` → 拦截
- ❌ `category="network"` → 拦截
- ❌ `needs_human_review="yes"` → 拦截
- ❌ `rationale="太短"` → 拦截

### 2. 字段验证器

自定义验证逻辑确保数据质量：

```python
@field_validator('rationale')
@classmethod
def validate_rationale(cls, v: str) -> str:
    if not v or v.strip() == "":
        raise ValueError("rationale 不能为空")
    if len(v.strip()) < 10:
        raise ValueError("rationale 必须提供充分的分类理由")
    return v.strip()
```

**防护效果**：
- ❌ 空字符串 → 拦截
- ❌ 过短的理由 → 拦截
- ✅ 自动去除首尾空格

### 3. 业务逻辑校验

确保分类结果符合业务规则：

```python
def _validate_business_logic(self, result: IncidentTriage) -> None:
    # P0/P1 必须需要人工审核
    if result.severity in ["P0", "P1"] and not result.needs_human_review:
        result.needs_human_review = True  # 自动修正
    
    # P3 不应该需要人工审核
    if result.severity == "P3" and result.needs_human_review:
        result.needs_human_review = False  # 自动修正
```

**防护效果**：
- 自动修正不合理的配置
- 记录警告日志便于审计

### 4. 异常处理

完善的错误处理机制：

```python
try:
    # JSON 解析
    result_dict = json.loads(response_text)
except json.JSONDecodeError as e:
    logger.error(f"模型输出无法解析为 JSON: {response_text}")
    raise ValueError(f"模型返回了无效的 JSON 格式: {str(e)}")

try:
    # Pydantic 校验
    validated_result = IncidentTriage(**result_dict)
except ValidationError as e:
    logger.error(f"模型输出未通过 Pydantic 校验")
    raise ValueError(f"模型输出不符合分类规范: {str(e)}")
```

**防护效果**：
- 详细的错误日志
- 清晰的异常信息
- 失败时不返回无效数据

### 5. 批量处理容错

单个故障失败不影响整体：

```python
def classify_batch(self, incidents: list[str]) -> list[IncidentTriage]:
    results = []
    for i, incident in enumerate(incidents):
        try:
            result = self.classify(incident)
            results.append(result)
        except Exception as e:
            logger.error(f"批量分类第 {i+1} 项失败: {str(e)}")
            continue  # 跳过失败项
    return results
```

## 测试验证

运行以下命令验证校验功能：

```bash
python test_validation.py
```

测试覆盖：
- ✅ 合法输入通过
- ✅ 无效枚举值被拦截
- ✅ 类型错误被拦截
- ✅ 缺失字段被拦截
- ✅ 长度不符被拦截
- ✅ 空值被拦截

## 日志与审计

所有校验失败都会记录日志：

```python
import logging
logger = logging.getLogger(__name__)

# 记录 JSON 解析失败
logger.error(f"模型输出无法解析为 JSON: {response_text}")

# 记录 Pydantic 校验失败
logger.error(f"模型输出未通过 Pydantic 校验: {result_dict}")
logger.error(f"校验错误详情: {e}")

# 记录业务逻辑警告
logger.warning(f"业务逻辑警告: {result.severity} 级别故障应该需要人工审核")
```

## 最佳实践

1. **永远使用 Pydantic 模型**
   - 不要直接使用字典
   - 不要跳过类型检查

2. **处理所有异常**
   - 捕获 `ValidationError`
   - 捕获 `json.JSONDecodeError`
   - 记录详细错误信息

3. **记录关键操作**
   - 校验失败
   - 业务逻辑修正
   - 批量处理错误

4. **测试边界情况**
   - 无效枚举值
   - 空值和极端值
   - 类型错误

## 安全承诺

- ✅ **类型安全**：Pydantic 强制类型检查
- ✅ **枚举安全**：只接受预定义的值
- ✅ **数据完整性**：必填字段验证
- ✅ **业务一致性**：逻辑规则校验
- ✅ **容错能力**：异常不会导致系统崩溃
- ✅ **可审计性**：完整的日志记录

## 参考资料

- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [OpenAI Best Practices - Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [OWASP AI Security](https://owasp.org/www-project-ai-security-and-privacy-guide/)
