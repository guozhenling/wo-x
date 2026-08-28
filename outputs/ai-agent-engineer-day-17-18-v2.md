# Day 17-18: 失败模式分析与优化

## 📋 学习目标

完成这两天的学习后，你将能够：
- 系统化分析 AI 系统的失败模式
- 识别失败的根本原因（提示词、规则、模型）
- 制定优化策略并验证效果
- 建立持续改进的反馈循环

**预计时间**：6-8 小时（两天）

---

## 🎯 为什么需要失败分析？

### 现实情况

运行评测后，你可能看到：
```
评测报告
==================
总案例数: 40
完全正确: 28 (70%)
可接受: 8 (20%)
失败: 4 (10%)

P0 准确率: 4/5 (80%)  ⚠️ 有 1 个 P0 案例分类错误！
P1 准确率: 7/10 (70%)
```

**问题**：
- 为什么这 4 个案例失败了？
- 是偶然还是系统性问题？
- 如何针对性优化？

**目标**：
从 70% 提升到 85%+（P0/P1 接近 100%）

---

## 📚 核心概念

### 1. 失败分类框架

AI 系统失败的三大根因：

#### 类型 1：提示词问题（Prompt Issue）
```
症状：模型理解错了任务
原因：指令不清晰、示例不够、格式说明模糊
解决：优化提示词
```

#### 类型 2：规则问题（Rule Issue）
```
症状：Policy 规则修正了正确的分类
原因：规则过于严格、逻辑冲突、边界条件错误
解决：调整 Policy 规则
```

#### 类型 3：模型能力问题（Model Capability Issue）
```
症状：模型无法理解复杂场景
原因：超出模型知识、推理能力不足
解决：换更强的模型、增加上下文
```

### 2. 失败分析流程

```
步骤 1: 收集失败案例
    ↓
步骤 2: 分类失败类型
    ↓
步骤 3: 识别模式（是否有共性？）
    ↓
步骤 4: 制定优化策略
    ↓
步骤 5: 实施优化
    ↓
步骤 6: 重新评测验证
    ↓
步骤 7: 对比前后效果
```

### 3. 优化策略矩阵

| 失败类型 | 常见表现 | 优化策略 | 难度 |
|---------|---------|---------|-----|
| 提示词模糊 | 理解偏差 | 增加示例、细化指令 | 低 |
| 规则过严 | 误修正 | 放宽阈值、增加条件 | 低 |
| 边界不清 | 临界值判断错 | 明确阈值、加示例 | 中 |
| 上下文缺失 | 信息不足 | 增加工具调用 | 中 |
| 模型能力 | 复杂推理失败 | 换更强模型 | 高 |

---

## 💻 完整示例

### 示例 1：失败案例分析器

```python
# tools/failure_analyzer.py
"""
失败案例分析工具
"""
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class FailurePattern:
    """失败模式"""
    pattern_type: str        # 失败类型
    count: int              # 出现次数
    cases: List[str]        # 案例 ID 列表
    description: str        # 模式描述
    suggested_fix: str      # 建议修复

class FailureAnalyzer:
    """
    失败案例分析器
    
    分析评测失败的案例，识别失败模式
    """
    
    def __init__(self):
        self.failure_types = {
            "severity_overestimate": "严重程度高估",
            "severity_underestimate": "严重程度低估",
            "category_wrong": "类别判断错误",
            "edge_case_failure": "边界案例失败",
            "system_error": "系统错误"
        }
    
    def analyze_failures(
        self,
        results: List[TestResult]
    ) -> Dict[str, Any]:
        """
        分析失败案例
        
        Args:
            results: 测试结果列表
            
        Returns:
            分析报告
        """
        # 1. 提取失败案例
        failures = [r for r in results if not r.is_acceptable]
        
        if not failures:
            return {
                "total_failures": 0,
                "patterns": [],
                "summary": "没有失败案例"
            }
        
        # 2. 分类失败类型
        type_groups = defaultdict(list)
        
        for f in failures:
            failure_type = self._classify_failure(f)
            type_groups[failure_type].append(f)
        
        # 3. 识别模式
        patterns = []
        
        for ftype, cases in type_groups.items():
            pattern = self._identify_pattern(ftype, cases)
            patterns.append(pattern)
        
        # 4. 生成建议
        suggestions = self._generate_suggestions(patterns)
        
        return {
            "total_failures": len(failures),
            "failure_types": {
                ftype: len(cases) 
                for ftype, cases in type_groups.items()
            },
            "patterns": patterns,
            "suggestions": suggestions,
            "details": [
                {
                    "test_id": f.test_id,
                    "description": f.description,
                    "expected": f"({f.expected_severity}, {f.expected_category})",
                    "actual": f"({f.actual_severity}, {f.actual_category})",
                    "failure_type": self._classify_failure(f)
                }
                for f in failures
            ]
        }
    
    def _classify_failure(self, result: TestResult) -> str:
        """
        分类单个失败案例
        
        Args:
            result: 测试结果
            
        Returns:
            失败类型
        """
        if result.error:
            return "system_error"
        
        # 严重程度判断
        severity_map = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        expected_level = severity_map.get(result.expected_severity, 3)
        actual_level = severity_map.get(result.actual_severity, 3)
        
        if actual_level < expected_level:
            return "severity_overestimate"  # 高估（实际给的更严重）
        elif actual_level > expected_level:
            return "severity_underestimate"  # 低估
        elif result.actual_category != result.expected_category:
            return "category_wrong"
        else:
            return "edge_case_failure"
    
    def _identify_pattern(
        self,
        failure_type: str,
        cases: List[TestResult]
    ) -> FailurePattern:
        """
        识别失败模式
        
        Args:
            failure_type: 失败类型
            cases: 案例列表
            
        Returns:
            失败模式
        """
        case_ids = [c.test_id for c in cases]
        
        # 分析共性
        descriptions = [c.description for c in cases]
        
        # 生成模式描述和修复建议
        pattern_desc, fix_suggestion = self._analyze_pattern(
            failure_type,
            cases
        )
        
        return FailurePattern(
            pattern_type=failure_type,
            count=len(cases),
            cases=case_ids,
            description=pattern_desc,
            suggested_fix=fix_suggestion
        )
    
    def _analyze_pattern(
        self,
        failure_type: str,
        cases: List[TestResult]
    ) -> tuple:
        """
        分析模式细节
        
        Args:
            failure_type: 失败类型
            cases: 案例列表
            
        Returns:
            (模式描述, 修复建议)
        """
        if failure_type == "severity_overestimate":
            # 分析是否都是某个优先级高估
            actual_levels = [c.actual_severity for c in cases]
            if actual_levels.count("P0") > len(cases) / 2:
                return (
                    f"{len(cases)} 个案例被高估为更高优先级",
                    "检查 Policy 规则是否过于严格，或提示词中的阈值定义"
                )
            else:
                return (
                    f"{len(cases)} 个案例严重程度判断偏高",
                    "在提示词中强调优先级判断标准，增加降级示例"
                )
        
        elif failure_type == "severity_underestimate":
            return (
                f"{len(cases)} 个案例被低估",
                "检查是否缺少关键信息（如影响范围），或提示词对严重性描述不足"
            )
        
        elif failure_type == "category_wrong":
            # 分析类别混淆
            actual_cats = [c.actual_category for c in cases]
            expected_cats = [c.expected_category for c in cases]
            
            confusion = defaultdict(int)
            for exp, act in zip(expected_cats, actual_cats):
                confusion[f"{exp}->{act}"] += 1
            
            most_common = max(confusion.items(), key=lambda x: x[1])
            
            return (
                f"{len(cases)} 个类别判断错误，最常见混淆: {most_common[0]}",
                "在提示词中明确区分容易混淆的类别，增加示例"
            )
        
        elif failure_type == "system_error":
            return (
                f"{len(cases)} 个系统错误",
                "检查代码逻辑、API 调用、异常处理"
            )
        
        else:
            return (
                f"{len(cases)} 个边界案例失败",
                "增加边界案例的处理逻辑或示例"
            )
    
    def _generate_suggestions(
        self,
        patterns: List[FailurePattern]
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议
        
        Args:
            patterns: 失败模式列表
            
        Returns:
            建议列表（按优先级排序）
        """
        suggestions = []
        
        # 按影响大小排序
        sorted_patterns = sorted(
            patterns,
            key=lambda p: p.count,
            reverse=True
        )
        
        for i, pattern in enumerate(sorted_patterns, 1):
            suggestions.append({
                "priority": i,
                "pattern": pattern.pattern_type,
                "impact": f"影响 {pattern.count} 个案例",
                "suggestion": pattern.suggested_fix,
                "affected_cases": pattern.cases
            })
        
        return suggestions
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """
        打印分析报告
        
        Args:
            analysis: 分析结果
        """
        print("\n" + "=" * 60)
        print("失败案例分析报告")
        print("=" * 60)
        
        if analysis["total_failures"] == 0:
            print("\n✅ 没有失败案例！")
            return
        
        print(f"\n失败案例总数: {analysis['total_failures']}")
        
        print(f"\n失败类型分布:")
        for ftype, count in analysis["failure_types"].items():
            print(f"  {self.failure_types.get(ftype, ftype)}: {count} 个")
        
        print(f"\n识别到的失败模式:")
        for pattern in analysis["patterns"]:
            print(f"\n  模式 {pattern.pattern_type}:")
            print(f"    影响: {pattern.count} 个案例")
            print(f"    描述: {pattern.description}")
            print(f"    建议: {pattern.suggested_fix}")
            print(f"    案例: {', '.join(pattern.cases)}")
        
        print(f"\n优化建议（按优先级）:")
        for i, suggestion in enumerate(analysis["suggestions"], 1):
            print(f"\n  {i}. {suggestion['pattern']}")
            print(f"     {suggestion['impact']}")
            print(f"     💡 {suggestion['suggestion']}")
        
        print("\n" + "=" * 60)
```

### 示例 2：A/B 对比工具

```python
# tools/ab_comparator.py
"""
A/B 对比工具 - 对比优化前后效果
"""
from typing import Dict, Any
import json

class ABComparator:
    """
    A/B 对比工具
    
    对比两次评测结果，量化优化效果
    """
    
    def compare_reports(
        self,
        baseline_file: str,
        optimized_file: str
    ) -> Dict[str, Any]:
        """
        对比两个评测报告
        
        Args:
            baseline_file: 基线报告文件
            optimized_file: 优化后报告文件
            
        Returns:
            对比结果
        """
        # 加载报告
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        with open(optimized_file, 'r') as f:
            optimized = json.load(f)
        
        base_summary = baseline["summary"]
        opt_summary = optimized["summary"]
        
        # 计算改进
        improvements = {}
        
        metrics = [
            "accuracy",
            "acceptable_rate",
            "severity_accuracy",
            "category_accuracy",
            "p0_accuracy",
            "p1_accuracy"
        ]
        
        for metric in metrics:
            base_val = base_summary.get(metric, 0)
            opt_val = opt_summary.get(metric, 0)
            
            if base_val > 0:
                delta = opt_val - base_val
                pct_change = (delta / base_val) * 100
            else:
                delta = opt_val
                pct_change = 0
            
            improvements[metric] = {
                "baseline": base_val,
                "optimized": opt_val,
                "delta": delta,
                "percent_change": pct_change
            }
        
        # 对比失败案例
        base_results = {r["test_id"]: r for r in baseline["results"]}
        opt_results = {r["test_id"]: r for r in optimized["results"]}
        
        fixed_cases = []
        new_failures = []
        
        for test_id in base_results:
            base_r = base_results[test_id]
            opt_r = opt_results.get(test_id)
            
            if not opt_r:
                continue
            
            # 基线失败，优化后成功
            if not base_r["is_acceptable"] and opt_r["is_acceptable"]:
                fixed_cases.append(test_id)
            
            # 基线成功，优化后失败
            if base_r["is_acceptable"] and not opt_r["is_acceptable"]:
                new_failures.append(test_id)
        
        return {
            "improvements": improvements,
            "fixed_cases": fixed_cases,
            "new_failures": new_failures,
            "summary": self._generate_summary(improvements, fixed_cases, new_failures)
        }
    
    def _generate_summary(
        self,
        improvements: Dict,
        fixed: List[str],
        new_failures: List[str]
    ) -> str:
        """生成对比摘要"""
        lines = []
        
        # 整体改进
        accuracy_imp = improvements["accuracy"]["percent_change"]
        if accuracy_imp > 0:
            lines.append(f"✅ 准确率提升 {accuracy_imp:.1f}%")
        elif accuracy_imp < 0:
            lines.append(f"⚠️ 准确率下降 {abs(accuracy_imp):.1f}%")
        else:
            lines.append("→ 准确率无变化")
        
        # P0/P1 改进
        p0_imp = improvements["p0_accuracy"]["percent_change"]
        p1_imp = improvements["p1_accuracy"]["percent_change"]
        
        if p0_imp > 0:
            lines.append(f"✅ P0 准确率提升 {p0_imp:.1f}%")
        if p1_imp > 0:
            lines.append(f"✅ P1 准确率提升 {p1_imp:.1f}%")
        
        # 修复的案例
        if fixed:
            lines.append(f"🔧 修复 {len(fixed)} 个失败案例")
        
        # 新增失败
        if new_failures:
            lines.append(f"⚠️ 引入 {len(new_failures)} 个新失败")
        
        return "\n".join(lines)
    
    def print_comparison(self, comparison: Dict[str, Any]):
        """
        打印对比报告
        
        Args:
            comparison: 对比结果
        """
        print("\n" + "=" * 60)
        print("A/B 对比报告")
        print("=" * 60)
        
        print(f"\n摘要:")
        print(comparison["summary"])
        
        print(f"\n详细指标变化:")
        for metric, values in comparison["improvements"].items():
            metric_name = {
                "accuracy": "整体准确率",
                "acceptable_rate": "可接受率",
                "severity_accuracy": "严重程度准确率",
                "category_accuracy": "类别准确率",
                "p0_accuracy": "P0 准确率",
                "p1_accuracy": "P1 准确率"
            }.get(metric, metric)
            
            base = values["baseline"] * 100
            opt = values["optimized"] * 100
            delta = values["delta"] * 100
            
            symbol = "✅" if delta > 0 else ("⚠️" if delta < 0 else "→")
            
            print(f"  {symbol} {metric_name}:")
            print(f"     基线: {base:.1f}%")
            print(f"     优化: {opt:.1f}%")
            print(f"     变化: {delta:+.1f}%")
        
        if comparison["fixed_cases"]:
            print(f"\n修复的案例 ({len(comparison['fixed_cases'])} 个):")
            for case_id in comparison["fixed_cases"]:
                print(f"  ✅ {case_id}")
        
        if comparison["new_failures"]:
            print(f"\n新增失败 ({len(comparison['new_failures'])} 个):")
            for case_id in comparison["new_failures"]:
                print(f"  ⚠️ {case_id}")
        
        print("\n" + "=" * 60)
```

### 示例 3：优化实验脚本

```python
# scripts/run_optimization.py
"""
优化实验流程
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.incident_classifier_v1 import IncidentClassifierV1
from tests.test_cases import get_all_cases
from tests.evaluation_framework import EvaluationFramework
from tools.failure_analyzer import FailureAnalyzer
from tools.ab_comparator import ABComparator

def main():
    """主流程"""
    print("\n" + "=" * 60)
    print("优化实验流程")
    print("=" * 60)
    
    # 步骤 1: 运行基线评测
    print("\n步骤 1: 运行基线评测...")
    print("-" * 60)
    
    agent_baseline = IncidentClassifierV1()
    test_cases = get_all_cases()
    
    framework = EvaluationFramework(agent_baseline)
    baseline_report = framework.run_all_tests(test_cases)
    framework.print_report(baseline_report)
    
    # 保存基线报告
    baseline_file = "outputs/evaluations/baseline.json"
    framework.save_report(baseline_report, baseline_file)
    
    # 步骤 2: 分析失败案例
    print("\n步骤 2: 分析失败案例...")
    print("-" * 60)
    
    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze_failures(baseline_report.results)
    analyzer.print_analysis(analysis)
    
    # 步骤 3: 实施优化
    print("\n步骤 3: 实施优化...")
    print("-" * 60)
    print("根据分析结果，修改:")
    print("  - 提示词（src/incident_classifier_v1.py）")
    print("  - Policy 规则（src/policy.py）")
    print("  - 或切换模型")
    print("\n按 Enter 继续运行优化后的评测...")
    input()
    
    # 步骤 4: 运行优化后评测
    print("\n步骤 4: 运行优化后评测...")
    print("-" * 60)
    
    agent_optimized = IncidentClassifierV1()  # 重新加载（应用了修改）
    optimized_report = framework.run_all_tests(test_cases)
    framework.print_report(optimized_report)
    
    # 保存优化报告
    optimized_file = "outputs/evaluations/optimized.json"
    framework.save_report(optimized_report, optimized_file)
    
    # 步骤 5: A/B 对比
    print("\n步骤 5: A/B 对比...")
    print("-" * 60)
    
    comparator = ABComparator()
    comparison = comparator.compare_reports(baseline_file, optimized_file)
    comparator.print_comparison(comparison)
    
    # 步骤 6: 结论
    print("\n步骤 6: 结论...")
    print("-" * 60)
    
    accuracy_delta = comparison["improvements"]["accuracy"]["percent_change"]
    
    if accuracy_delta > 5:
        print("✅ 优化显著有效！建议采纳。")
    elif accuracy_delta > 0:
        print("→ 优化略有改善，可继续迭代。")
    else:
        print("⚠️ 优化未生效或有副作用，建议回滚重新分析。")
    
    # 是否有新失败？
    if comparison["new_failures"]:
        print(f"\n⚠️ 注意：优化引入了 {len(comparison['new_failures'])} 个新失败")
        print("建议分析这些案例，避免过拟合")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
```

---

## 🎯 动手练习

### Level 1：基础 - 手动分析失败案例

**任务**：分析你的评测结果中的失败案例

**步骤**：
1. 运行评测，找出 3-5 个失败案例
2. 逐个分析：
   - 为什么失败？
   - 是提示词、规则还是模型问题？
   - 如何修复？

**模板**：
```
案例 ID: P1-001
描述: 推荐服务 p99 延迟从 100ms 升到 3s
期望: P1, latency
实际: P2, latency

分析:
- 失败类型: 严重程度低估
- 根本原因: 提示词中对"延迟严重"的定义不够明确
- 修复方案: 在提示词中明确 p99 > 1s 为严重延迟
```

### Level 2：进阶 - 实现失败分析器

**任务**：实现一个简化版的失败分析器

**要求**：
- 自动分类失败类型
- 统计失败分布
- 生成优化建议

**提示**：
```python
class SimpleAnalyzer:
    def analyze(self, results):
        failures = [r for r in results if not r.is_acceptable]
        
        # 分类
        overestimate = []
        underestimate = []
        category_wrong = []
        
        for f in failures:
            # 判断失败类型
            # ...
        
        return {
            "overestimate": len(overestimate),
            "underestimate": len(underestimate),
            "category_wrong": len(category_wrong)
        }
```

### Level 3：高级 - 完整优化流程

**任务**：实现完整的优化实验流程

**要求**：
1. 自动化运行基线评测
2. 分析失败模式
3. 记录每次优化尝试
4. A/B 对比多个版本
5. 生成优化历史报告

**提示**：
```python
class OptimizationTracker:
    def __init__(self):
        self.experiments = []
    
    def run_experiment(self, name, agent_factory):
        """运行一次优化实验"""
        # 评测
        # 分析
        # 记录
        pass
    
    def compare_all(self):
        """对比所有实验"""
        # 生成多版本对比
        pass
    
    def get_best(self):
        """返回最佳版本"""
        pass
```

---

## ✅ 自我检查清单

完成这两天的学习后，你应该能回答：

### 概念理解
- [ ] AI 系统失败的三大根因是什么？
- [ ] 如何区分提示词问题和规则问题？
- [ ] 什么是 A/B 对比？为什么重要？
- [ ] 如何避免过拟合（修复 A 破坏 B）？

### 实践能力
- [ ] 能否分析失败案例的根本原因？
- [ ] 能否制定针对性的优化策略？
- [ ] 能否量化优化效果？
- [ ] 能否进行 A/B 对比？

### 工程实践
- [ ] 如何系统化地优化 AI 系统？
- [ ] 优化的优先级应该如何排序？
- [ ] 何时停止优化（足够好 vs 过拟合）？
- [ ] 如何记录和管理优化历史？

---

## 🤔 常见问题

### Q1：优化了某些案例，但破坏了其他案例怎么办？
**A**：这是过拟合。解决方法：
1. **不要针对单个案例优化**（增加通用性）
2. **每次优化后重新跑全量评测**（验证副作用）
3. **如果新失败 > 修复数**，回滚重新分析

### Q2：P0 准确率到 100% 了，但 P3 很差，要优化吗？
**A**：要看业务优先级：
- 如果 P3 误判不影响业务 → 不优化
- 如果 P3 误判引起用户投诉 → 优化
- **原则**：先保证关键指标，再优化次要指标

### Q3：尝试了很多优化，准确率还是上不去？
**A**：可能原因：
1. **测试案例定义有问题**（期望输出不合理）
2. **模型能力不足**（换更强的模型）
3. **任务本身太难**（需要更多上下文/工具）

### Q4：什么时候应该停止优化？
**A**：达到以下任一条件：
- P0 准确率 > 95%
- P1 准确率 > 90%
- 整体准确率 > 85%
- 继续优化收益递减（改进 < 1%）

### Q5：如何决定优化优先级？
**A**：优先级排序：
1. **P0 失败案例**（最高优先级）
2. **P1 失败案例**
3. **影响面最大的模式**（修复一个模式 = 修复多个案例）
4. **P2/P3 失败案例**

---

## 📚 延伸阅读

### 相关概念
- **Prompt Engineering** - 提示词工程
- **Few-Shot Learning** - 少样本学习
- **Ensemble Methods** - 集成方法（多个模型投票）
- **Active Learning** - 主动学习（标注难例）

### 优化技巧
1. **提示词优化**：
   - 增加示例（Few-Shot）
   - 使用 Chain-of-Thought
   - 明确输出格式

2. **规则优化**：
   - 放宽阈值
   - 增加条件分支
   - 移除冲突规则

3. **模型选择**：
   - GPT-4 vs GPT-3.5
   - Claude vs GPT
   - 开源模型微调

### 下一步
- Day 19-20：性能优化
- Day 21：第三周总结

---

## 🎯 本节重点

1. **失败分析是优化的第一步**（先分析再优化）
2. **三大失败根因：提示词、规则、模型能力**
3. **A/B 对比验证优化效果**（避免主观判断）
4. **优先修复 P0/P1 失败案例**（业务优先级）

---

## 💡 小贴士

**类比调试代码**：
```
传统 Bug 调试:
1. 发现 Bug
2. 定位代码位置
3. 修复代码
4. 回归测试

AI 系统优化:
1. 发现失败案例
2. 定位失败根因（提示词/规则/模型）
3. 实施优化
4. 重新评测
```

**记住**：
- 优化是迭代过程，不是一次性
- 每次优化后都要验证副作用
- 数据驱动，避免凭感觉

---

**完成 Day 17-18 后，你将建立起系统化的优化方法，从 70% 提升到 85%+！**

**下一步**：Day 19-20 - 性能优化
