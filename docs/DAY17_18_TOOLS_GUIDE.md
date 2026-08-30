# Day 17-18 工具使用指南

根据 `ai-agent-engineer-day-17-18-v2.md` 实现的失败分析和配置验证工具。

---

## 📦 新增工具

### 1. 配置验证工具 (tools/config_validator.py)

**功能**：
- ✅ 验证必需配置（OPENAI_API_KEY）
- ✅ 验证可选配置（OPENAI_BASE_URL、OPENAI_MODEL）
- ✅ 检查 .env 文件
- ✅ 验证目录结构
- ✅ 验证关键文件
- ✅ 可选：API 连接测试

**使用场景**：
- 首次启动前验证配置
- 部署前检查
- 排查 API 连接问题
- CI/CD 环境验证

### 2. 测试失败分析器 (tools/test_failure_analyzer.py)

**功能**：
- ✅ 分析 pytest 输出
- ✅ 识别失败类型（API、类型错误、属性错误等）
- ✅ 生成修复建议
- ✅ 提取关键错误信息
- ✅ 按优先级排序

**使用场景**：
- 测试失败后快速定位问题
- CI 失败分析
- 批量测试问题诊断

---

## 🚀 快速开始

### 方式 1: 使用集成脚本（推荐）

```bash
python scripts/run_dev_tools.py
```

交互式选择：
1. 配置验证工具
2. 测试失败分析器
3. 完整检查（推荐）

### 方式 2: 单独使用

#### 配置验证

```bash
# 快速验证
python tools/config_validator.py

# 或在代码中使用
python -c "
from dotenv import load_dotenv
load_dotenv()

from tools.config_validator import ConfigValidator
validator = ConfigValidator()
results = validator.validate()
validator.print_results(results)
"
```

#### 测试失败分析

```bash
# 1. 运行测试并保存输出
pytest tests/ -v > test_output.txt 2>&1

# 2. 分析输出
python tools/test_failure_analyzer.py test_output.txt

# 或在代码中使用
python -c "
from tools.test_failure_analyzer import TestFailureAnalyzer
analyzer = TestFailureAnalyzer()
analysis = analyzer.analyze_from_file('test_output.txt')
analyzer.print_analysis(analysis)
"
```

---

## 📊 工具 1: 配置验证工具

### 功能详解

#### 验证项目

| 验证项 | 类型 | 说明 |
|--------|------|------|
| OPENAI_API_KEY | 必需 | API 密钥 |
| OPENAI_BASE_URL | 可选 | API 基础 URL（需以 /v1 结尾）|
| OPENAI_MODEL | 可选 | 使用的模型 |
| .env 文件 | 检查 | 是否存在 |
| 目录结构 | 检查 | src/tests/outputs 等 |
| 关键文件 | 必需 | classifier/policy/trace |

#### 输出示例

```
配置验证
================================================================

✅ 配置验证通过

配置信息:
  ✓ OPENAI_API_KEY: 已设置
  ✓ OPENAI_BASE_URL: https://api.waibibabo.com/v1
  ✓ OPENAI_MODEL: glm-5.3-flash

警告 (1 个):
  ⚠️  目录不存在: outputs（可能不影响运行）

================================================================
```

#### 验证模式

**快速验证**（默认）：
- 检查配置文件
- 验证格式
- 不发送网络请求

**完整验证**（可选）：
- 包含快速验证的所有内容
- ✅ 测试 API 连接
- ✅ 验证凭据有效性

### 在代码中集成

```python
from tools.config_validator import ConfigValidator
from dotenv import load_dotenv

# 加载配置
load_dotenv()

# 验证
validator = ConfigValidator()
results = validator.validate()

# 根据结果决定是否继续
if not results["valid"]:
    validator.print_results(results)
    sys.exit(1)

# 继续执行主程序
...
```

---

## 📊 工具 2: 测试失败分析器

### 功能详解

#### 识别的失败类型

| 类型 | 说明 | 常见原因 |
|------|------|----------|
| api_required | 需要 API 配置 | 缺少 .env 或配置错误 |
| type_error | 类型错误 | 变量类型不匹配 |
| attribute_error | 属性错误 | 对象缺少属性或方法 |
| import_error | 导入错误 | 模块未安装或路径错误 |
| assertion_error | 断言失败 | 测试期望不匹配 |

#### 输出示例

```
测试失败分析
================================================================

发现 5 个失败测试
分布: 3 个 api_required, 2 个 type_error

失败类型分布:
  api_required: 3 个
  type_error: 2 个

关键错误:
  ❌ TypeError: string indices must be integers, not 'str'
  ❌ AttributeError: 'NoneType' object has no attribute 'get'

修复建议:

  1. [API 配置] (优先级: high)
     影响 3 个测试

这些测试需要 API 配置。建议：
1. 检查 .env 文件是否存在
2. 确保 OPENAI_API_KEY 已设置
3. 确保 OPENAI_BASE_URL 正确（需要以 /v1 结尾）
4. 或在 CI 中排除这些测试：
   pytest --ignore-glob='tests/test_e2e*.py' \
          --ignore-glob='tests/test_agent*.py' \
          --ignore-glob='tests/test_api*.py'

     失败的测试:
       - tests/test_e2e_integration.py::test_basic_classification
       - tests/test_e2e_integration.py::test_with_tools
       - tests/test_agent_integration.py::test_agent_flow

  2. [类型错误] (优先级: high)
     影响 2 个测试

检查以下内容：
1. 变量类型是否符合预期
2. 函数返回值类型（查看类型注解）
3. 字典 vs 字符串混淆
4. 使用 isinstance() 验证类型

     失败的测试:
       - tests/test_classifier.py::test_build_report
       - tests/test_trace.py::test_summary

================================================================
```

### 在 CI/CD 中使用

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest tests/ -v > test_output.txt 2>&1 || true

- name: Analyze failures
  if: failure()
  run: |
    python tools/test_failure_analyzer.py test_output.txt
```

---

## 💡 典型使用场景

### 场景 1: 首次启动项目

```bash
# 1. 验证配置
python scripts/run_dev_tools.py
# 选择模式 1（配置验证）

# 2. 如果验证失败，按提示修复
# 3. 重新验证直到通过
```

### 场景 2: 测试失败后诊断

```bash
# 1. 运行测试并保存输出
pytest tests/ -v > test_output.txt 2>&1

# 2. 分析失败
python scripts/run_dev_tools.py
# 选择模式 2（测试失败分析）

# 3. 根据建议修复问题

# 4. 重新运行测试
pytest tests/ -v
```

### 场景 3: 部署前完整检查

```bash
# 运行完整检查
python scripts/run_dev_tools.py
# 选择模式 3（完整检查）

# 输出:
# - 配置验证结果
# - 测试失败分析（如果有 test_output.txt）
```

### 场景 4: CI 环境诊断

```bash
# 在 CI 中运行
pytest tests/ \
  --ignore-glob='tests/test_e2e*.py' \
  --ignore-glob='tests/test_agent*.py' \
  -v > test_output.txt 2>&1 || true

# 分析失败
python tools/test_failure_analyzer.py test_output.txt

# 根据分析结果决定是否继续部署
```

---

## 🔧 故障排查

### 问题 1: 配置验证失败

**错误**: `缺少必需配置: OPENAI_API_KEY`

**解决**:
```bash
# 1. 创建 .env 文件
cp .env.example .env

# 2. 编辑 .env
vim .env

# 3. 添加配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.waibibabo.com/v1
OPENAI_MODEL=glm-5.3-flash

# 4. 重新验证
python tools/config_validator.py
```

### 问题 2: BASE_URL 格式错误

**错误**: `OPENAI_BASE_URL 应该以 /v1 结尾`

**解决**:
```bash
# .env 中修改
# 错误
OPENAI_BASE_URL=https://api.waibibabo.com

# 正确
OPENAI_BASE_URL=https://api.waibibabo.com/v1
```

### 问题 3: 测试分析器找不到文件

**错误**: `文件不存在: test_output.txt`

**解决**:
```bash
# 先运行测试生成输出文件
pytest tests/ -v > test_output.txt 2>&1

# 然后再分析
python tools/test_failure_analyzer.py test_output.txt
```

---

## 📚 与其他工具的关系

| 工具 | 用途 | 时机 |
|------|------|------|
| **配置验证工具** | 验证系统配置 | 启动前、部署前 |
| **测试失败分析器** | 诊断测试失败 | 测试失败后 |
| 失败分析器 (Level 2) | 分析评测失败 | 评测失败后 |
| A/B 对比工具 (Level 2) | 对比优化效果 | 优化后 |
| 性能分析器 (Level 3) | 分析性能瓶颈 | 评测后 |

### 工作流集成

```
启动前 → 配置验证 ✅
  ↓
单元测试 → 测试失败分析器（如果失败）
  ↓
评测 → 失败分析器 + 性能分析器
  ↓
优化 → A/B 对比 + 趋势追踪
```

---

## 🎯 最佳实践

1. **每次启动前验证配置**
   ```bash
   python tools/config_validator.py
   ```

2. **CI 中使用测试失败分析**
   - 自动分析失败原因
   - 生成可读的报告

3. **保存测试输出**
   - 便于后续分析
   - 可追溯历史问题

4. **定期完整检查**
   ```bash
   python scripts/run_dev_tools.py
   # 选择模式 3
   ```

---

## 📝 总结

根据 Day 17-18 文档实现的两个实用工具：

✅ **配置验证工具** - 确保环境正确配置
✅ **测试失败分析器** - 快速定位测试问题

这些工具帮助你：
- 减少启动失败
- 快速诊断问题
- 提高开发效率
- 改善 CI/CD 体验
