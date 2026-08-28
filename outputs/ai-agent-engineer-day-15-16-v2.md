# Day 15-16: 测试框架设计

## 📋 学习目标

完成这两天的学习后，你将能够：
- 理解如何评测 AI 系统（与传统软件的区别）
- 设计全面的测试案例集
- 实现自动化测试框架
- 量化系统的准确率和可靠性

**预计时间**：6-8 小时（两天）

---

## 🎯 为什么需要专门的测试框架？

### 传统软件 vs AI 系统

**传统软件测试**：
```java
// Java 单元测试 - 确定性
@Test
public void testCalculate() {
    assertEquals(4, calculator.add(2, 2));  // 永远是 4
}
```

**AI 系统测试**：
```python
# AI 系统测试 - 非确定性
def test_classify():
    result = agent.classify("支付失败 5%")
    # 可能是 P0，也可能是 P1
    # 需要判断"是否合理"，而不是"是否精确相等"
```

### 核心区别

| 维度 | 传统软件 | AI 系统 |
|------|---------|---------|
| 确定性 | ✅ 相同输入永远相同输出 | ❌ 相同输入可能不同输出 |
| 测试标准 | 精确匹配 | 范围判断 |
| 失败原因 | 代码 bug | 提示词、规则、模型能力 |
| 修复方式 | 改代码 | 改提示词/规则/换模型 |

---

## 📚 核心概念

### 1. 测试案例的三个维度

#### 维度 1：优先级覆盖
```
P0: 核心收入、数据安全（必须准确）
P1: 核心服务故障（重要准确）
P2: 非核心影响（允许误差）
P3: 低影响观察（允许误差）
```

#### 维度 2：故障类型覆盖
```
- availability: 可用性（错误、宕机）
- latency: 延迟（慢查询、超时）
- database: 数据库（死锁、连接池）
- deployment: 部署相关
- unknown: 不明确
```

#### 维度 3：边界情况
```
- 明确案例: "支付失败 50%"
- 模糊案例: "有点慢"
- 冲突案例: "错误率 20%，但已回滚"
- 极端案例: "所有服务都挂了"
```

### 2. 评测指标

**准确率（Accuracy）**：
```python
accuracy = 正确分类数 / 总案例数
```

**严重程度准确率**：
```python
severity_accuracy = 严重程度正确数 / 总案例数
```

**可接受率**：
```python
# 允许 ±1 级误差
acceptable_rate = (完全正确 + 差1级) / 总数
```

### 3. 测试案例设计原则

**MECE 原则**（Mutually Exclusive, Collectively Exhaustive）：
- 互相排斥：案例之间不重复
- 完全穷尽：覆盖所有场景

**覆盖优先级**：
1. P0 案例（10-15 个）- 最重要
2. P1 案例（10-15 个）- 重要
3. P2/P3 案例（10-15 个）- 覆盖
4. 边界案例（5-10 个）- 鲁棒性

---

## 💻 完整示例

### 示例 1：测试案例定义

```python
# tests/test_cases.py
"""
测试案例集定义
"""
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TestCase:
    """单个测试案例"""
    id: str                          # 案例 ID
    description: str                 # 故障描述
    expected_severity: str           # 期望严重程度
    expected_category: str           # 期望类别
    acceptable_severities: List[str] # 可接受的严重程度范围
    notes: str = ""                  # 说明

# P0 案例 - 核心收入/数据安全
P0_CASES = [
    TestCase(
        id="P0-001",
        description="支付接口完全不可用，所有请求返回 500",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="核心收入，必须 P0"
    ),
    TestCase(
        id="P0-002",
        description="订单创建成功率从 99.9% 降到 60%",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="影响核心收入"
    ),
    TestCase(
        id="P0-003",
        description="用户登录接口 5xx 错误率 30%",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="用户无法登录"
    ),
    TestCase(
        id="P0-004",
        description="数据库发现未授权访问，疑似数据泄露",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="数据安全"
    ),
    TestCase(
        id="P0-005",
        description="Redis 集群完全宕机，所有缓存失效",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="影响核心服务"
    ),
]

# P1 案例 - 核心服务明显故障
P1_CASES = [
    TestCase(
        id="P1-001",
        description="推荐服务 p99 延迟从 100ms 升到 3s",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P0", "P1"],
        notes="核心服务延迟严重"
    ),
    TestCase(
        id="P1-002",
        description="数据库出现大量死锁，影响订单处理",
        expected_severity="P1",
        expected_category="database",
        acceptable_severities=["P0", "P1"],
        notes="影响核心功能"
    ),
    TestCase(
        id="P1-003",
        description="搜索服务超时率从 1% 升到 15%",
        expected_severity="P1",
        expected_category="latency",
        acceptable_severities=["P1"],
        notes="超时率高"
    ),
    TestCase(
        id="P1-004",
        description="API Gateway OOM，每 10 分钟重启一次",
        expected_severity="P1",
        expected_category="availability",
        acceptable_severities=["P0", "P1"],
        notes="频繁重启"
    ),
    TestCase(
        id="P1-005",
        description="新版本部署后，错误日志暴增 10 倍",
        expected_severity="P1",
        expected_category="deployment",
        acceptable_severities=["P1"],
        notes="部署引入问题"
    ),
]

# P2 案例 - 非核心或部分影响
P2_CASES = [
    TestCase(
        id="P2-001",
        description="用户头像上传失败率 5%",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P1", "P2"],
        notes="非核心功能"
    ),
    TestCase(
        id="P2-002",
        description="消息推送延迟 30 秒",
        expected_severity="P2",
        expected_category="latency",
        acceptable_severities=["P2"],
        notes="延迟但不影响核心"
    ),
    TestCase(
        id="P2-003",
        description="后台管理系统加载慢",
        expected_severity="P2",
        expected_category="latency",
        acceptable_severities=["P2", "P3"],
        notes="内部系统"
    ),
    TestCase(
        id="P2-004",
        description="部分地区 CDN 节点故障，已切换备用",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P2"],
        notes="已有降级"
    ),
    TestCase(
        id="P2-005",
        description="埋点数据采集失败率 10%",
        expected_severity="P2",
        expected_category="availability",
        acceptable_severities=["P2", "P3"],
        notes="数据分析，非实时"
    ),
]

# P3 案例 - 低影响观察
P3_CASES = [
    TestCase(
        id="P3-001",
        description="某个 API 偶发 500 错误，错误率 0.5%",
        expected_severity="P3",
        expected_category="availability",
        acceptable_severities=["P2", "P3"],
        notes="低错误率"
    ),
    TestCase(
        id="P3-002",
        description="日志中发现少量慢查询（<1%）",
        expected_severity="P3",
        expected_category="database",
        acceptable_severities=["P3"],
        notes="偶发，无影响"
    ),
    TestCase(
        id="P3-003",
        description="测试环境数据库连接池满",
        expected_severity="P3",
        expected_category="database",
        acceptable_severities=["P3"],
        notes="非生产环境"
    ),
    TestCase(
        id="P3-004",
        description="某个低频 API 响应时间略有上升",
        expected_severity="P3",
        expected_category="latency",
        acceptable_severities=["P3"],
        notes="低流量"
    ),
    TestCase(
        id="P3-005",
        description="监控告警发现一个节点 CPU 使用率偏高",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P3"],
        notes="单节点，无影响"
    ),
]

# 边界案例 - 测试鲁棒性
EDGE_CASES = [
    TestCase(
        id="EDGE-001",
        description="有点慢",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P2", "P3"],
        notes="描述模糊"
    ),
    TestCase(
        id="EDGE-002",
        description="错误率 20%，但已通过回滚恢复",
        expected_severity="P2",
        expected_category="deployment",
        acceptable_severities=["P1", "P2"],
        notes="已恢复，降级"
    ),
    TestCase(
        id="EDGE-003",
        description="",
        expected_severity="P3",
        expected_category="unknown",
        acceptable_severities=["P3"],
        notes="空输入"
    ),
    TestCase(
        id="EDGE-004",
        description="所有服务都挂了，网站完全不可用",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="灾难性故障"
    ),
    TestCase(
        id="EDGE-005",
        description="支付接口错误率 8%",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0", "P1"],
        notes="接近阈值，可能P0或P1"
    ),
]

# 完整案例集
ALL_TEST_CASES = (
    P0_CASES + P1_CASES + P2_CASES + P3_CASES + EDGE_CASES
)

def get_test_cases_by_priority(priority: str) -> List[TestCase]:
    """按优先级获取测试案例"""
    case_map = {
        "P0": P0_CASES,
        "P1": P1_CASES,
        "P2": P2_CASES,
        "P3": P3_CASES,
        "EDGE": EDGE_CASES,
    }
    return case_map.get(priority, [])

def get_all_cases() -> List[TestCase]:
    """获取所有测试案例"""
    return ALL_TEST_CASES
```

### 示例 2：自动化测试框架

```python
# tests/evaluation_framework.py
"""
自动化评测框架
"""
import time
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class TestResult:
    """单个测试结果"""
    test_id: str
    description: str
    expected_severity: str
    actual_severity: str
    expected_category: str
    actual_category: str
    is_correct: bool
    is_acceptable: bool
    duration: float
    error: str = ""

@dataclass
class EvaluationReport:
    """评测报告"""
    total_cases: int = 0
    passed: int = 0
    acceptable: int = 0
    failed: int = 0
    
    severity_correct: int = 0
    category_correct: int = 0
    
    p0_correct: int = 0
    p0_total: int = 0
    p1_correct: int = 0
    p1_total: int = 0
    
    total_duration: float = 0.0
    avg_duration: float = 0.0
    
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)

class EvaluationFramework:
    """
    评测框架
    
    用于自动化运行测试案例并生成报告
    """
    
    def __init__(self, agent):
        """
        初始化
        
        Args:
            agent: 要评测的 Agent 实例
        """
        self.agent = agent
    
    def run_single_test(self, test_case: TestCase) -> TestResult:
        """
        运行单个测试案例
        
        Args:
            test_case: 测试案例
            
        Returns:
            TestResult: 测试结果
        """
        start = time.time()
        
        try:
            # 调用 Agent
            result = self.agent.classify(test_case.description)
            duration = time.time() - start
            
            if not result.get('success'):
                return TestResult(
                    test_id=test_case.id,
                    description=test_case.description,
                    expected_severity=test_case.expected_severity,
                    actual_severity="ERROR",
                    expected_category=test_case.expected_category,
                    actual_category="ERROR",
                    is_correct=False,
                    is_acceptable=False,
                    duration=duration,
                    error=str(result.get('error', 'Unknown error'))
                )
            
            actual_severity = result['classification']['severity']
            actual_category = result['classification']['category']
            
            # 判断是否正确
            is_correct = (
                actual_severity == test_case.expected_severity and
                actual_category == test_case.expected_category
            )
            
            # 判断是否可接受（严重程度在允许范围内）
            is_acceptable = (
                actual_severity in test_case.acceptable_severities
            )
            
            return TestResult(
                test_id=test_case.id,
                description=test_case.description,
                expected_severity=test_case.expected_severity,
                actual_severity=actual_severity,
                expected_category=test_case.expected_category,
                actual_category=actual_category,
                is_correct=is_correct,
                is_acceptable=is_acceptable,
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start
            return TestResult(
                test_id=test_case.id,
                description=test_case.description,
                expected_severity=test_case.expected_severity,
                actual_severity="ERROR",
                expected_category=test_case.expected_category,
                actual_category="ERROR",
                is_correct=False,
                is_acceptable=False,
                duration=duration,
                error=str(e)
            )
    
    def run_all_tests(
        self,
        test_cases: List[TestCase]
    ) -> EvaluationReport:
        """
        运行所有测试案例
        
        Args:
            test_cases: 测试案例列表
            
        Returns:
            EvaluationReport: 评测报告
        """
        report = EvaluationReport()
        report.start_time = datetime.now()
        report.total_cases = len(test_cases)
        
        print(f"\n开始评测 {len(test_cases)} 个案例...")
        print("=" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test_case.id}: {test_case.description[:50]}...")
            
            result = self.run_single_test(test_case)
            report.results.append(result)
            report.total_duration += result.duration
            
            # 统计结果
            if result.is_correct:
                report.passed += 1
                print(f"  ✅ 正确: {result.actual_severity} / {result.actual_category}")
            elif result.is_acceptable:
                report.acceptable += 1
                print(f"  ⚠️  可接受: {result.actual_severity} (期望 {result.expected_severity})")
            else:
                report.failed += 1
                if result.error:
                    print(f"  ❌ 失败: {result.error}")
                else:
                    print(f"  ❌ 错误: {result.actual_severity} (期望 {result.expected_severity})")
            
            # 统计严重程度和类别
            if result.actual_severity == test_case.expected_severity:
                report.severity_correct += 1
            if result.actual_category == test_case.expected_category:
                report.category_correct += 1
            
            # 统计 P0/P1 准确率
            if test_case.expected_severity == "P0":
                report.p0_total += 1
                if result.actual_severity == "P0":
                    report.p0_correct += 1
            elif test_case.expected_severity == "P1":
                report.p1_total += 1
                if result.actual_severity == "P1":
                    report.p1_correct += 1
        
        report.end_time = datetime.now()
        report.avg_duration = report.total_duration / len(test_cases)
        
        return report
    
    def print_report(self, report: EvaluationReport):
        """
        打印评测报告
        
        Args:
            report: 评测报告
        """
        print("\n" + "=" * 60)
        print("评测报告")
        print("=" * 60)
        
        # 整体准确率
        accuracy = report.passed / report.total_cases * 100
        acceptable_rate = (report.passed + report.acceptable) / report.total_cases * 100
        severity_acc = report.severity_correct / report.total_cases * 100
        category_acc = report.category_correct / report.total_cases * 100
        
        print(f"\n总体统计:")
        print(f"  总案例数: {report.total_cases}")
        print(f"  完全正确: {report.passed} ({accuracy:.1f}%)")
        print(f"  可接受: {report.acceptable} ({acceptable_rate:.1f}%)")
        print(f"  失败: {report.failed}")
        
        print(f"\n维度准确率:")
        print(f"  严重程度: {report.severity_correct}/{report.total_cases} ({severity_acc:.1f}%)")
        print(f"  故障类别: {report.category_correct}/{report.total_cases} ({category_acc:.1f}%)")
        
        # P0/P1 准确率（最重要）
        if report.p0_total > 0:
            p0_acc = report.p0_correct / report.p0_total * 100
            print(f"\n关键指标:")
            print(f"  P0 准确率: {report.p0_correct}/{report.p0_total} ({p0_acc:.1f}%)")
        
        if report.p1_total > 0:
            p1_acc = report.p1_correct / report.p1_total * 100
            print(f"  P1 准确率: {report.p1_correct}/{report.p1_total} ({p1_acc:.1f}%)")
        
        # 性能
        print(f"\n性能:")
        print(f"  总耗时: {report.total_duration:.1f}s")
        print(f"  平均耗时: {report.avg_duration:.2f}s/案例")
        
        # 失败案例
        failed_results = [r for r in report.results if not r.is_acceptable]
        if failed_results:
            print(f"\n失败案例 ({len(failed_results)} 个):")
            for r in failed_results:
                print(f"  [{r.test_id}] {r.description[:40]}...")
                print(f"    期望: {r.expected_severity} / {r.expected_category}")
                print(f"    实际: {r.actual_severity} / {r.actual_category}")
                if r.error:
                    print(f"    错误: {r.error}")
        
        print("\n" + "=" * 60)
    
    def save_report(self, report: EvaluationReport, filepath: str):
        """
        保存评测报告到 JSON 文件
        
        Args:
            report: 评测报告
            filepath: 文件路径
        """
        import json
        
        data = {
            "summary": {
                "total_cases": report.total_cases,
                "passed": report.passed,
                "acceptable": report.acceptable,
                "failed": report.failed,
                "accuracy": report.passed / report.total_cases,
                "acceptable_rate": (report.passed + report.acceptable) / report.total_cases,
                "severity_accuracy": report.severity_correct / report.total_cases,
                "category_accuracy": report.category_correct / report.total_cases,
                "p0_accuracy": report.p0_correct / report.p0_total if report.p0_total > 0 else 0,
                "p1_accuracy": report.p1_correct / report.p1_total if report.p1_total > 0 else 0,
                "avg_duration": report.avg_duration,
                "total_duration": report.total_duration,
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "description": r.description,
                    "expected": {
                        "severity": r.expected_severity,
                        "category": r.expected_category
                    },
                    "actual": {
                        "severity": r.actual_severity,
                        "category": r.actual_category
                    },
                    "is_correct": r.is_correct,
                    "is_acceptable": r.is_acceptable,
                    "duration": r.duration,
                    "error": r.error
                }
                for r in report.results
            ],
            "metadata": {
                "start_time": report.start_time.isoformat(),
                "end_time": report.end_time.isoformat(),
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存到: {filepath}")
```

### 示例 3：运行评测

```python
# scripts/run_evaluation.py
"""
运行完整评测
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.incident_classifier_v1 import IncidentClassifierV1
from tests.test_cases import get_all_cases
from tests.evaluation_framework import EvaluationFramework

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("AI Agent 评测系统")
    print("=" * 60)
    
    # 1. 初始化 Agent
    print("\n初始化 Agent...")
    agent = IncidentClassifierV1()
    
    # 2. 加载测试案例
    test_cases = get_all_cases()
    print(f"加载 {len(test_cases)} 个测试案例")
    
    # 3. 创建评测框架
    framework = EvaluationFramework(agent)
    
    # 4. 运行评测
    report = framework.run_all_tests(test_cases)
    
    # 5. 打印报告
    framework.print_report(report)
    
    # 6. 保存报告
    output_dir = Path("outputs/evaluations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = report.start_time.strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"evaluation_{timestamp}.json"
    framework.save_report(report, str(report_file))
    
    # 7. 返回退出码（CI/CD 用）
    if report.failed > 0:
        print(f"\n⚠️  有 {report.failed} 个案例失败")
        return 1
    else:
        print(f"\n✅ 所有案例通过！")
        return 0

if __name__ == "__main__":
    exit(main())
```

---

## 🎯 动手练习

### Level 1：基础 - 设计测试案例

**任务**：为你的故障分类器设计 10 个测试案例

**要求**：
- 覆盖 P0、P1、P2、P3 各 2-3 个
- 每个案例包含：描述、期望输出、可接受范围
- 使用 `TestCase` 数据类

**提示**：
```python
# 你的测试案例
MY_TEST_CASES = [
    TestCase(
        id="MY-001",
        description="...",
        expected_severity="P0",
        expected_category="availability",
        acceptable_severities=["P0"],
        notes="..."
    ),
    # ... 更多案例
]
```

### Level 2：进阶 - 实现评测框架

**任务**：实现一个简化版的评测框架

**要求**：
- 能运行测试案例
- 能统计准确率
- 能打印失败案例

**提示**：
```python
class SimpleEvaluator:
    def __init__(self, agent):
        self.agent = agent
    
    def run_tests(self, cases):
        results = []
        for case in cases:
            # 运行测试
            result = self.agent.classify(case.description)
            # 判断正确性
            # 记录结果
        return results
    
    def print_summary(self, results):
        # 打印统计信息
        pass
```

### Level 3：高级 - 完整评测系统

**任务**：实现完整的评测系统，包括：

1. **测试案例管理**：
   - 支持从文件加载案例
   - 支持按优先级/类别过滤

2. **评测执行**：
   - 支持并发执行（加速）
   - 支持失败重试
   - 支持中断恢复

3. **报告生成**：
   - 生成 JSON 报告
   - 生成 HTML 可视化报告
   - 支持趋势对比（多次评测）

**提示**：
```python
class AdvancedEvaluator:
    def load_cases_from_file(self, filepath):
        """从 YAML/JSON 加载案例"""
        pass
    
    def run_parallel(self, cases, workers=4):
        """并发执行测试"""
        from concurrent.futures import ThreadPoolExecutor
        # ...
    
    def generate_html_report(self, report):
        """生成 HTML 可视化报告"""
        pass
    
    def compare_reports(self, report1, report2):
        """对比两次评测结果"""
        pass
```

---

## ✅ 自我检查清单

完成这两天的学习后，你应该能回答：

### 概念理解
- [ ] AI 系统测试与传统软件测试有什么区别？
- [ ] 为什么不能用"精确相等"来判断 AI 输出？
- [ ] 什么是"可接受范围"？为什么需要它？
- [ ] 测试案例设计的 MECE 原则是什么？

### 实践能力
- [ ] 能否设计 40 个覆盖全面的测试案例？
- [ ] 能否实现自动化评测框架？
- [ ] 能否计算准确率、可接受率等指标？
- [ ] 能否生成评测报告？

### 工程实践
- [ ] 如何判断一个测试案例是好的案例？
- [ ] P0/P1 案例为什么最重要？
- [ ] 如何设计边界案例？
- [ ] 评测报告应该包含哪些信息？

---

## 🤔 常见问题

### Q1：需要多少个测试案例？
**A**：根据系统复杂度：
- 最少：20-30 个（覆盖主要场景）
- 推荐：40-50 个（全面覆盖）
- 更多：100+ 个（生产级系统）

重点是覆盖率，不是数量。

### Q2：可接受范围怎么设置？
**A**：根据业务影响：
- P0 案例：只接受 P0（最严格）
- P1 案例：接受 P0-P1（允许高估）
- P2/P3 案例：接受 ±1 级（允许误差）

### Q3：测试失败了怎么办？
**A**：三步走：
1. **分析原因**：提示词？规则？模型能力？
2. **调整策略**：改提示词、加规则、换模型
3. **重新评测**：验证改进效果

### Q4：如何提高准确率？
**A**：优先级顺序：
1. **先保证 P0/P1 准确**（最重要）
2. **再优化 P2/P3**（次要）
3. **最后处理边界案例**（锦上添花）

### Q5：评测要花多长时间？
**A**：取决于：
- 案例数量：40 个案例
- 每个案例：10-30 秒（调用 API）
- 总计：10-20 分钟

可以并发执行加速。

---

## 📚 延伸阅读

### 相关概念
- **混淆矩阵**（Confusion Matrix）- 多分类评测
- **F1 Score** - 准确率和召回率的平衡
- **A/B 测试** - 对比不同版本

### 工具推荐
- **pytest** - Python 测试框架
- **pytest-html** - 生成 HTML 报告
- **pandas** - 数据分析
- **matplotlib/plotly** - 可视化

### 下一步
- Day 17-18：失败模式分析
- Day 19-20：性能优化
- Day 21：第三周总结

---

## 🎯 本节重点

1. **AI 系统测试需要"范围判断"而不是"精确匹配"**
2. **测试案例要全面覆盖：优先级 × 类型 × 边界**
3. **P0/P1 准确率是最重要的指标**
4. **自动化评测框架让优化有据可依**

---

## 💡 小贴士

**类比 Java 后端**：
```java
// 传统后端测试
@Test
public void testUserService() {
    User user = userService.getById(1);
    assertEquals("张三", user.getName());  // 精确匹配
}

// AI 系统测试
@Test
public void testClassifier() {
    Result result = classifier.classify("支付失败 5%");
    assertTrue(result.getSeverity() in ["P0", "P1"]);  // 范围判断
}
```

**记住**：
- 传统测试：验证"做对了"
- AI 测试：验证"合理"

---

**完成 Day 15-16 后，你将拥有一个完整的评测系统，能够量化你的 Agent 的表现！**

**下一步**：Day 17-18 - 失败模式分析
