# Day 8-9 - 多工具协同

**预计学习时间**: 2 天，每天 2.5 小时

## 🎯 学习目标

学完这两天，你将：
- 理解工具组合的策略
- 掌握工具调用顺序优化
- 能实现更智能的决策逻辑
- 知道如何处理工具依赖

## 📖 核心概念

### 1. 什么是多工具协同？

**第一周的限制**：工具独立使用

```python
# Week 1: 工具独立调用
search_logs("payment")  # 查日志
search_runbooks("payment 5xx")  # 查 Runbook

# 问题：没有组合逻辑
```

**多工具协同**：工具之间配合

```python
# Week 2: 智能组合
1. search_logs("payment") → 发现 5xx 错误 35%
2. 基于日志结果 → search_runbooks("payment 5xx P0")
3. 基于 Runbook → 推荐具体步骤

# 每一步的结果影响下一步
```

### 2. 工具调用策略

**策略 1：顺序调用**（最常见）

```
先查证据 → 再查方案

search_logs("payment")
  ↓ 如果发现错误
search_runbooks("payment 5xx")
```

**策略 2：并行调用**（提升性能）

```
同时查询多个数据源

并行：
  - search_logs("payment")
  - get_metrics("payment")
  - check_deployment("payment")
```

**策略 3：条件调用**（按需调用）

```
根据严重程度决定

if severity == "P0":
    search_runbooks(...)  # 只有 P0 才查
    notify_oncall(...)    # 只有 P0 才通知
```

### 3. 工具依赖管理

**依赖类型**：

```python
# 1. 数据依赖：后面的工具需要前面的结果
logs = search_logs("payment")
error_rate = calculate_error_rate(logs)  # 依赖 logs

# 2. 条件依赖：满足条件才调用
if "5xx" in logs:
    runbook = search_runbooks("5xx")  # 条件依赖

# 3. 优先级依赖：按重要性排序
优先级 1: search_logs（必须）
优先级 2: search_runbooks（重要）
优先级 3: get_metrics（可选）
```

### 4. 智能决策树

```
故障描述
    ↓
初步判断严重程度
    ↓
┌─────────┴─────────┐
P0/P1            P2/P3
↓                ↓
必须查日志        可选查日志
↓                ↓
必须查 Runbook    条件查 Runbook
↓                ↓
必须通知          记录即可
```

## 🔍 完整示例

### 实现智能工具调度器

```python
# tool_coordinator.py
"""
工具协调器 - 智能管理多工具调用
"""
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ToolPriority(Enum):
    """工具优先级"""
    REQUIRED = "required"    # 必须调用
    IMPORTANT = "important"  # 重要，优先调用
    OPTIONAL = "optional"    # 可选，按需调用

class ToolCoordinator:
    """
    工具协调器
    
    功能：
    - 管理工具调用顺序
    - 处理工具依赖
    - 优化调用策略
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.execution_plan = []
    
    def plan_tool_calls(
        self,
        incident_description: str,
        initial_classification: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        规划工具调用
        
        根据故障描述和初步分类，决定：
        - 调用哪些工具
        - 按什么顺序
        - 是否并行
        """
        plan = []
        severity = initial_classification.get('severity', 'P3')
        category = initial_classification.get('category', 'unknown')
        
        # 规则 1: 所有故障都查日志（优先级高）
        plan.append({
            "tool": "search_logs",
            "priority": ToolPriority.REQUIRED,
            "arguments": self._get_log_search_args(incident_description),
            "reason": "获取错误证据"
        })
        
        # 规则 2: P0/P1 必须查 Runbook
        if severity in ['P0', 'P1']:
            plan.append({
                "tool": "search_runbooks",
                "priority": ToolPriority.REQUIRED,
                "arguments": {
                    "description": incident_description,
                    "severity": severity,
                    "category": category
                },
                "reason": "高优先级故障需要标准处理流程",
                "depends_on": ["search_logs"]  # 依赖日志结果
            })
        
        # 规则 3: 数据库问题查慢查询
        if category == "database":
            plan.append({
                "tool": "search_slow_queries",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {"time_range": 60},
                "reason": "数据库问题需要查慢查询"
            })
        
        # 规则 4: 部署问题查发布历史
        if category == "deployment" or "部署" in incident_description:
            plan.append({
                "tool": "get_deployment_history",
                "priority": ToolPriority.IMPORTANT,
                "arguments": {"hours": 24},
                "reason": "可能与最近部署相关"
            })
        
        self.execution_plan = plan
        return plan
    
    def execute_plan(self) -> Dict[str, Any]:
        """
        执行工具调用计划
        
        按优先级和依赖关系执行
        """
        results = {}
        
        # 按优先级排序
        sorted_plan = sorted(
            self.execution_plan,
            key=lambda x: (
                0 if x['priority'] == ToolPriority.REQUIRED else
                1 if x['priority'] == ToolPriority.IMPORTANT else 2
            )
        )
        
        for step in sorted_plan:
            tool_name = step['tool']
            
            # 检查依赖
            if 'depends_on' in step:
                missing_deps = [
                    dep for dep in step['depends_on']
                    if dep not in results
                ]
                if missing_deps:
                    logger.warning(f"跳过 {tool_name}，缺少依赖: {missing_deps}")
                    continue
            
            # 检查是否可以调用
            if not self.agent.trace.can_call(tool_name):
                logger.warning(f"跳过 {tool_name}，调用次数超限")
                continue
            
            # 执行工具
            logger.info(f"执行: {tool_name} ({step['reason']})")
            result = self.agent._execute_tool_with_trace(
                tool_name,
                json.dumps(step['arguments'])
            )
            
            results[tool_name] = result
            
            # 根据结果调整后续计划
            self._adjust_plan_based_on_result(tool_name, result)
        
        return results
    
    def _get_log_search_args(self, description: str) -> Dict[str, Any]:
        """根据描述推断日志搜索参数"""
        args = {"level": "ERROR", "limit": 20}
        
        # 提取服务名
        services = ["payment", "order", "user", "recommendation"]
        for service in services:
            if service in description.lower() or service in description:
                args["service"] = service
                break
        
        if "service" not in args:
            # 默认支付（最关键）
            args["service"] = "payment"
        
        return args
    
    def _adjust_plan_based_on_result(
        self,
        tool_name: str,
        result: Any
    ):
        """根据工具结果调整后续计划"""
        # 例如：如果日志显示 5xx 很多，提高 Runbook 查询优先级
        if tool_name == "search_logs":
            if isinstance(result, list) and len(result) > 10:
                logger.info("日志错误较多，提高 Runbook 查询优先级")
                for step in self.execution_plan:
                    if step['tool'] == 'search_runbooks':
                        step['priority'] = ToolPriority.REQUIRED

# 测试
if __name__ == "__main__":
    # 模拟测试
    class MockAgent:
        def __init__(self):
            from trace_manager import TraceManager
            self.trace = TraceManager()
        
        def _execute_tool_with_trace(self, tool_name, args):
            print(f"  执行 {tool_name}({args})")
            return {"success": True}
    
    agent = MockAgent()
    coordinator = ToolCoordinator(agent)
    
    # 测试 P0 故障
    print("测试 1: P0 支付故障")
    print("=" * 60)
    plan = coordinator.plan_tool_calls(
        "支付接口 5xx 错误率 35%",
        {"severity": "P0", "category": "availability"}
    )
    
    print("执行计划:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step['tool']} - {step['reason']}")
        print(f"   优先级: {step['priority'].value}")
    
    print("\n执行:")
    coordinator.execute_plan()
```

## 💪 动手练习

### Day 8: 设计工具组合策略（2.5 小时）

**任务**：
1. 实现 ToolCoordinator
2. 定义 5 条工具调用规则
3. 测试不同严重程度的故障

**验证**：
- [ ] P0 故障调用 2-3 个工具
- [ ] P3 故障只调用必要工具
- [ ] 工具按优先级执行

### Day 9: 优化性能（2.5 小时）

**任务**：
1. 实现并行工具调用
   ```python
   import concurrent.futures
   
   with concurrent.futures.ThreadPoolExecutor() as executor:
       futures = {
           executor.submit(search_logs, "payment"): "logs",
           executor.submit(get_metrics, "payment"): "metrics"
       }
       for future in concurrent.futures.as_completed(futures):
           results[futures[future]] = future.result()
   ```

2. 添加工具调用缓存
3. 测试性能提升

**验证**：
- [ ] 并行调用比顺序快 30%+
- [ ] 相同查询命中缓存
- [ ] 性能测试报告

## ✅ 完成检查清单

- [ ] 理解工具组合策略
- [ ] 实现了 ToolCoordinator
- [ ] 测试了多种场景
- [ ] 优化了性能

## 🎯 Day 10-11 预告

**错误处理与降级**

多工具调用会遇到更多错误：
- 工具超时怎么办？
- 某个工具失败了怎么继续？
- 如何优雅降级？

下两天学习完整的错误处理策略！🚀
