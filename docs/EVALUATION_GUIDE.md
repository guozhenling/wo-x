# 评测与优化工具使用指南

本目录包含完整的评测、分析和优化工具链。

## 📁 工具清单

### 核心工具

| 文件 | 功能 | 说明 |
|------|------|------|
| `tests/test_cases.py` | 测试案例集 | 35 个结构化测试案例 |
| `tests/evaluation_framework.py` | 评测框架 | 标准化评测流程和报告生成 |
| `tests/failure_analyzer.py` | 失败分析器 | 识别失败模式，生成优化建议 |
| `tests/ab_comparator.py` | A/B 对比工具 | 对比优化前后效果 |

### 运行脚本

| 文件 | 功能 | 适用场景 |
|------|------|----------|
| `scripts/run_evaluation.py` | 运行评测 | 单次评测 |
| `scripts/run_optimization_flow.py` | 完整优化流程 | 系统化优化 |

---

## 🚀 快速开始

### 场景 1: 第一次评测

```bash
# 运行评测
python scripts/run_evaluation.py

# 选择模式 2（快速评测，P0 + P1）
# 等待评测完成，查看结果
```

**输出**:
- `outputs/evaluations/evaluation_YYYYMMDD_HHMMSS.json` - JSON 报告
- `outputs/evaluations/evaluation_YYYYMMDD_HHMMSS.md` - Markdown 报告

### 场景 2: 系统化优化流程

```bash
# 运行完整优化流程
python scripts/run_optimization_flow.py

# 选择模式 1（完整流程）
# 将执行：基线评测 → 失败分析 → 优化建议 → 优化后评测 → A/B 对比
```

**流程**:
1. 运行基线评测
2. 自动分析失败案例
3. 显示优化建议
4. 暂停，等待你修改代码
5. 运行优化后评测
6. A/B 对比，显示改进效果

### 场景 3: 只分析失败案例

```bash
# 运行优化流程
python scripts/run_optimization_flow.py

# 选择模式 2（仅基线+分析）
# 查看失败分析和优化建议
```

### 场景 4: 对比两次评测

```bash
# 运行优化流程
python scripts/run_optimization_flow.py

# 选择模式 3（仅对比）
# 输入两个评测报告路径
```

---

## 📊 测试案例说明

### 案例统计

```
总案例数: 35 个

按优先级:
- P0: 7 个（核心收入/数据安全，必须准确）
- P1: 8 个（核心服务故障，重要准确）
- P2: 7 个（非核心或部分影响，允许误差）
- P3: 6 个（低影响观察，允许误差）
- 边界: 7 个（测试鲁棒性）

按类别:
- availability: 可用性故障
- latency: 延迟问题
- database: 数据库问题
- deployment: 部署相关
- unknown: 未分类
```

### 案例示例

```python
from tests.test_cases import get_all_cases, get_test_cases_by_priority

# 获取所有案例
all_cases = get_all_cases()

# 获取 P0 案例
p0_cases = get_test_cases_by_priority("P0")

# 获取 P0 + P1（快速评测）
quick_cases = (
    get_test_cases_by_priority("P0") +
    get_test_cases_by_priority("P1")
)
```

---

## 📈 评测报告格式

### JSON 报告结构

```json
{
  "metadata": {
    "report_id": "20260828_143000",
    "agent_version": "1.0.0",
    "start_time": "...",
    "end_time": "...",
    "total_duration": 900.5
  },
  "summary": {
    "total_cases": 35,
    "passed": 28,
    "failed": 7,
    "accuracy": 0.80,
    "acceptable_rate": 0.94,
    "p0_accuracy": 1.0,
    "p1_accuracy": 0.875
  },
  "performance": {
    "avg_duration": 25.7,
    "p95_duration": 35.2
  },
  "failures": [...],
  "results": [...]
}
```

### 关键指标说明

| 指标 | 说明 | 目标 |
|------|------|------|
| `accuracy` | 完全正确率（严重程度+类别都对） | > 80% |
| `acceptable_rate` | 可接受率（严重程度在 ±1 级范围内） | > 90% |
| `p0_accuracy` | P0 准确率（最关键） | > 95% |
| `p1_accuracy` | P1 准确率 | > 90% |
| `avg_duration` | 平均延迟 | < 30s |
| `p95_duration` | P95 延迟 | < 40s |

---

## 🔍 失败分析说明

### 失败类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **严重程度高估** | 判断过于严格 | P2 判断为 P0 |
| **严重程度低估** | 判断过于宽松 | P0 判断为 P2 |
| **类别判断错误** | 故障类型错误 | latency 判断为 availability |
| **边界案例失败** | 模糊输入处理不佳 | 空输入、极短描述 |
| **系统错误** | 代码或 API 错误 | 超时、异常 |

### 分析输出

```python
from tests.failure_analyzer import FailureAnalyzer

analyzer = FailureAnalyzer()
analysis = analyzer.analyze_failures(report)

# 打印分析
analyzer.print_analysis(analysis)

# 保存分析
analyzer.save_analysis_json(analysis, 'outputs/analysis.json')
```

**输出**:
- 失败类型分布
- 失败模式识别
- 优化建议（按优先级）

---

## 🔄 A/B 对比说明

### 对比指标

| 维度 | 指标 |
|------|------|
| **准确率** | 整体、P0、P1、严重程度、类别 |
| **案例变化** | 修复的案例、新增失败、仍然失败 |
| **性能** | 平均延迟、P95 延迟 |

### 使用方法

```python
from tests.ab_comparator import ABComparator

comparator = ABComparator()
comparison = comparator.compare_reports(
    'outputs/evaluations/baseline.json',
    'outputs/evaluations/optimized.json'
)

# 打印对比
comparator.print_comparison(comparison)

# 保存对比
comparator.save_comparison_json(comparison, 'outputs/comparisons/ab.json')
```

### 推荐逻辑

| 情况 | 推荐 |
|------|------|
| 准确率提升 > 5% 且无新失败 | ✅ 推荐采纳 |
| 准确率提升且修复 > 新失败 | ✅ 推荐采纳 |
| 准确率提升但有新失败 | ⚠️ 谨慎采纳 |
| 准确率无变化 | → 根据案例变化判断 |
| 准确率下降 | ❌ 不推荐采纳 |

---

## 💡 使用示例

### 示例 1: 完整优化循环

```bash
# 第 1 轮
python scripts/run_optimization_flow.py
# 选择模式 1，完成基线评测 → 分析 → 优化 → 对比

# 根据建议修改代码
# 例如：优化提示词、调整 Policy 规则

# 第 2 轮（可选）
python scripts/run_optimization_flow.py
# 如果第 1 轮改进不够，继续优化
```

### 示例 2: 在代码中使用

```python
from src.incident_classifier_v1 import IncidentClassifierV1
from tests.test_cases import get_test_cases_by_priority
from tests.evaluation_framework import EvaluationFramework
from tests.failure_analyzer import FailureAnalyzer

# 1. 初始化
agent = IncidentClassifierV1()
framework = EvaluationFramework(agent, agent_version="1.0.0")

# 2. 选择测试集
test_cases = (
    get_test_cases_by_priority("P0") +
    get_test_cases_by_priority("P1")
)

# 3. 运行评测
report = framework.run_evaluation(test_cases)

# 4. 分析失败
analyzer = FailureAnalyzer()
analysis = analyzer.analyze_failures(report)

# 5. 查看建议
for suggestion in analysis["suggestions"]:
    print(f"{suggestion['pattern']}: {suggestion['suggestion']}")
```

### 示例 3: 查看历史报告

```bash
# 列出所有报告
ls -lh outputs/evaluations/

# 查看特定报告
cat outputs/evaluations/evaluation_20260828_143000.md

# 对比任意两个报告
python scripts/run_optimization_flow.py
# 选择模式 3，输入两个报告路径
```

---

## 📝 优化建议示例

### 常见优化方向

#### 1. 提示词优化

**问题**: 严重程度高估

**建议**:
```python
# src/incident_classifier_v1.py

# 修改前
"""
P0: 核心功能完全不可用
"""

# 修改后（更严格）
"""
P0: 核心收入或数据安全功能完全不可用，影响超过 10% 用户
P1: 核心功能部分不可用或严重延迟，影响 1-10% 用户
"""
```

#### 2. Policy 规则调整

**问题**: 错误率判断不准

**建议**:
```python
# src/policy.py

# 修改前
if error_rate >= 5:
    severity = "P0"

# 修改后（放宽阈值）
if error_rate >= 10:
    severity = "P0"
elif error_rate >= 5:
    severity = "P1"
```

#### 3. 增加示例

**问题**: 类别混淆（latency vs availability）

**建议**:
```python
# 在提示词中增加对比示例
"""
示例:
- availability: "接口返回 500 错误"（可用性问题）
- latency: "接口响应时间从 100ms 升到 3s"（延迟问题）
"""
```

---

## 🎯 优化目标

### 基础目标（合格）

- ✅ 整体准确率 > 80%
- ✅ 可接受率 > 90%
- ✅ P0 准确率 > 95%
- ✅ P1 准确率 > 85%

### 优秀目标

- 🌟 整体准确率 > 90%
- 🌟 可接受率 > 95%
- 🌟 P0 准确率 = 100%
- 🌟 P1 准确率 > 95%
- 🌟 平均延迟 < 20s

---

## 🔧 故障排查

### 问题 1: 评测脚本失败

**错误**: `ModuleNotFoundError: No module named 'tests'`

**解决**:
```bash
# 从项目根目录运行
cd /path/to/wo-x
python scripts/run_evaluation.py
```

### 问题 2: API 调用失败

**错误**: `API 超时`或`连接失败`

**解决**:
```bash
# 检查 .env 配置
cat .env | grep OPENAI

# 确保配置正确
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.waibibabo.com/v1
OPENAI_MODEL=glm-5.3-flash
```

### 问题 3: 报告文件不存在

**错误**: `❌ 基线报告不存在`

**解决**:
```bash
# 先运行评测生成报告
python scripts/run_evaluation.py

# 然后再进行对比
```

---

## 📚 延伸阅读

- [Day 15-16: 测试与评测回顾](../outputs/ai-agent-engineer-day-15-16-v2.md)
- [Day 17-18: 失败分析与优化实践](../outputs/ai-agent-engineer-day-17-18-v2.md)
- [Day 19-20: 性能分析与优化](../outputs/ai-agent-engineer-day-19-20-v2.md)

---

## 🤝 贡献

如果你发现 bug 或有优化建议，欢迎提 Issue 或 PR！

**关键扩展点**:
- 添加更多测试案例到 `tests/test_cases.py`
- 优化失败模式识别逻辑
- 增加新的评测指标
- 支持更多报告格式（HTML、PDF）
