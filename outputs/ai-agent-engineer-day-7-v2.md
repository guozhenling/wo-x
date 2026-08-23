# Day 7 - 第一周总结与集成

**预计学习时间**: 3 小时

## 🎯 本周回顾

### 你学会了什么

**Day 1**: Structured Output
- Agent vs 聊天机器人
- JSON 输出 + Pydantic 校验
- 故障分类器原型

**Day 2**: Policy 规则
- 为什么不能信任 LLM
- 确定性规则 vs 模型判断
- PolicyEngine 实现

**Day 3**: 第一个工具
- 什么是工具（Tool）
- 实现 search_logs
- 工具定义（Tool Definition）

**Day 4**: Tool-Calling Loop
- 完整的调用循环
- LLM 主动调用工具
- 多轮对话

**Day 5**: 第二个工具
- Runbook 检索
- 关键词匹配算法
- 推荐处理步骤

**Day 6**: 调用轨迹
- 审计和调试
- 调用次数限制
- 轨迹记录

### 你现在能做什么

✅ 能让 LLM 输出结构化 JSON  
✅ 能用规则兜底模型输出  
✅ 能实现只读工具  
✅ 能让 Agent 主动调用工具  
✅ 能检索相关处理手册  
✅ 能追踪和限制调用  

**简单说**：你已经能做一个**会查证据、会推荐方案、可审计**的 Agent 了！

## 📊 完整系统架构

```
用户输入："支付服务报错"
    ↓
┌─────────────────────────────────────┐
│ IncidentClassifier (Day 1-2)        │
│ - LLM 初步分类                       │
│ - Policy 规则修正                    │
│ - 输出结构化结果                     │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ IncidentAgent (Day 4)               │
│ - 决定是否需要工具                   │
│ - Tool-Calling Loop                 │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Tools (Day 3, 5)                    │
│ - search_logs: 查日志               │
│ - search_runbooks: 查处理手册       │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ TraceManager (Day 6)                │
│ - 记录调用轨迹                       │
│ - 限制调用次数                       │
│ - 生成审计报告                       │
└──────┬──────────────────────────────┘
       ↓
最终输出：
- 故障分析
- 严重程度
- 处理建议
- 调用轨迹
```

## 🔧 今天的任务：集成所有模块

### 完整的故障分析系统

```python
# incident_analyzer.py
"""
完整的故障分析系统（整合 Day 1-6）
"""
import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Day 1-2
from models import IncidentResult
from policy import PolicyEngine

# Day 3, 5
from tools.tool_definitions import get_all_tool_definitions
from tools.executor import execute_tool

# Day 6
from trace_manager import TraceManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IncidentAnalyzer:
    """
    完整的故障分析器
    
    整合：
    - Structured Output (Day 1)
    - Policy 规则 (Day 2)
    - 工具调用 (Day 3-5)
    - 轨迹管理 (Day 6)
    """
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.policy = PolicyEngine()
        self.trace = None  # 每次分析创建新的
    
    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """
        完整的故障分析流程
        
        Args:
            incident_description: 故障描述
            
        Returns:
            分析结果，包含：
            - classification: 分类结果（Day 1-2）
            - evidence: 工具调用证据（Day 3-5）
            - recommendation: 处理建议（Day 5）
            - trace: 调用轨迹（Day 6）
        """
        # 初始化轨迹
        self.trace = TraceManager(
            max_calls_per_tool=2,
            max_total_calls=5,
            max_duration_seconds=30
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"开始分析故障")
        logger.info(f"{'='*80}")
        logger.info(f"描述: {incident_description}")
        
        # Step 1: 初步分类（可能需要工具）
        messages = self._build_initial_messages(incident_description)
        
        # Step 2: Tool-Calling Loop
        classification, evidence = self._run_tool_calling_loop(
            messages,
            incident_description
        )
        
        # Step 3: Policy 规则修正
        if classification:
            logger.info("\n应用 Policy 规则...")
            classification = self.policy.check_and_enforce(
                incident_description,
                classification
            )
        
        # Step 4: 生成最终报告
        result = self._generate_report(
            incident_description,
            classification,
            evidence
        )
        
        # 打印轨迹
        self.trace.print_summary()
        
        # 保存轨迹
        trace_file = self.trace.save_to_file()
        result['trace_file'] = trace_file
        
        return result
    
    def _build_initial_messages(self, description: str) -> list:
        """构造初始消息"""
        system_prompt = """你是故障分析专家。

任务：分析故障并给出建议。

可用工具：
- search_logs: 搜索日志
- search_runbooks: 搜索处理手册

流程：
1. 理解故障描述
2. 如需更多证据，调用 search_logs
3. 调用 search_runbooks 查找处理流程
4. 给出分析结果

输出格式（JSON）：
{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment",
  "needs_human_review": true/false,
  "rationale": "判断依据",
  "recommendation": "处理建议"
}"""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析故障：{description}"}
        ]
    
    def _run_tool_calling_loop(
        self,
        messages: list,
        description: str
    ) -> tuple:
        """
        运行工具调用循环
        
        Returns:
            (classification, evidence)
        """
        evidence = {
            "logs": [],
            "runbooks": []
        }
        
        max_rounds = 5
        
        for round_num in range(max_rounds):
            logger.info(f"\n--- Round {round_num + 1} ---")
            
            # 调用 LLM
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=get_all_tool_definitions(),
                temperature=0.3
            )
            
            message = response.choices[0].message
            
            # 没有工具调用，返回最终结果
            if not message.tool_calls:
                logger.info("✓ 得到最终分析")
                
                try:
                    classification = json.loads(message.content)
                    return classification, evidence
                except:
                    # 如果不是 JSON，尝试提取
                    return {
                        "severity": "P3",
                        "category": "unknown",
                        "needs_human_review": True,
                        "rationale": message.content
                    }, evidence
            
            # 处理工具调用
            logger.info(f"→ LLM 请求 {len(message.tool_calls)} 个工具")
            messages.append(message.model_dump())
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args_str = tool_call.function.arguments
                
                # 执行工具
                result = self._execute_tool_with_trace(
                    tool_name,
                    args_str
                )
                
                # 记录证据
                if tool_name == "search_logs":
                    evidence["logs"].extend(result if isinstance(result, list) else [])
                elif tool_name == "search_runbooks":
                    evidence["runbooks"].extend(result if isinstance(result, list) else [])
                
                # 添加工具结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
        
        # 超时
        return None, evidence
    
    def _execute_tool_with_trace(
        self,
        tool_name: str,
        arguments_str: str
    ) -> Any:
        """执行工具并记录轨迹"""
        import time
        
        logger.info(f"  执行: {tool_name}")
        
        # 检查调用限制
        if not self.trace.can_call(tool_name):
            logger.warning(f"  ⚠️  {tool_name} 调用次数超限")
            self.trace.record_call(
                tool_name,
                {},
                None,
                0,
                success=False,
                error="调用次数超限"
            )
            return {"error": "调用次数超限"}
        
        # 执行工具
        try:
            start = time.time()
            arguments = json.loads(arguments_str)
            result = execute_tool(tool_name, arguments)
            duration = (time.time() - start) * 1000
            
            # 记录成功
            self.trace.record_call(
                tool_name,
                arguments,
                result,
                duration,
                success=True
            )
            
            logger.info(f"  ✓ 完成 ({duration:.0f}ms)")
            return result
            
        except Exception as e:
            duration = (time.time() - start) * 1000 if 'start' in locals() else 0
            logger.error(f"  ✗ 失败: {e}")
            
            self.trace.record_call(
                tool_name,
                json.loads(arguments_str) if arguments_str else {},
                None,
                duration,
                success=False,
                error=str(e)
            )
            
            return {"error": str(e)}
    
    def _generate_report(
        self,
        description: str,
        classification: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成最终报告"""
        return {
            "description": description,
            "classification": classification,
            "evidence": {
                "logs_count": len(evidence.get("logs", [])),
                "runbooks_count": len(evidence.get("runbooks", [])),
                "logs_sample": evidence.get("logs", [])[:3],
                "runbooks": evidence.get("runbooks", [])
            },
            "trace_summary": self.trace.get_summary()
        }

# 主函数
def main():
    """测试完整流程"""
    analyzer = IncidentAnalyzer()
    
    # 测试案例
    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "数据库报 1205 死锁错误，影响订单创建"
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试案例 {i}")
        print(f"{'='*80}")
        
        result = analyzer.analyze(case)
        
        print(f"\n【分析结果】")
        print(f"严重程度: {result['classification']['severity']}")
        print(f"类别: {result['classification']['category']}")
        print(f"需要审核: {result['classification']['needs_human_review']}")
        print(f"依据: {result['classification']['rationale']}")
        
        if result['classification'].get('recommendation'):
            print(f"建议: {result['classification']['recommendation']}")
        
        print(f"\n【证据】")
        print(f"查询日志: {result['evidence']['logs_count']} 条")
        print(f"匹配 Runbook: {result['evidence']['runbooks_count']} 个")
        
        print(f"\n【调用统计】")
        summary = result['trace_summary']
        print(f"总调用: {summary['total_calls']}")
        print(f"成功: {summary['successful_calls']}")
        print(f"耗时: {summary['total_duration_ms']} ms")
        print(f"轨迹文件: {result['trace_file']}")
        
        print("\n" + "="*80)
        input("按回车继续下一个案例...")

if __name__ == "__main__":
    main()
```

**运行测试**：
```bash
python incident_analyzer.py
```

## 💪 第一周作业

### 必做作业（3 小时）

**任务**：完善故障分析系统

1. **添加更多测试案例**（至少 10 个）
   - 支付相关 3 个
   - 数据库相关 2 个
   - 部署相关 2 个
   - 其他 3 个

2. **完善 Runbook**（至少 5 个）
   - 覆盖常见故障类型
   - 包含详细的检查和修复步骤

3. **运行完整测试**
   - 对每个案例生成分析报告
   - 检查分类是否准确
   - 验证 Policy 规则是否生效
   - 查看调用轨迹

4. **创建测试报告**
   ```markdown
   # 第一周测试报告
   
   ## 测试案例
   - 案例 1: 支付 5xx
     - 分类: P0 / availability
     - 工具调用: search_logs, search_runbooks
     - 结果: ✓ 正确
   
   ## Policy 规则触发统计
   - 高优先级审核: 3 次
   - 支付高错误率: 2 次
   ...
   
   ## 问题与改进
   - 问题 1: Runbook 匹配不准
   - 改进: 添加更多关键词
   ```

**验证**：
- ✓ 10 个测试案例
- ✓ 5 个 Runbook
- ✓ 测试报告
- ✓ 所有代码能运行

### 选做作业（2 小时）

**任务**：优化和扩展

1. **添加缓存**
   - 相同的日志查询不重复执行
   - 相同的 Runbook 检索不重复

2. **添加并发**
   - search_logs 和 search_runbooks 并发执行
   - 减少总耗时

3. **添加可视化**
   - 生成 HTML 报告
   - 展示调用轨迹

4. **添加 CLI**
   ```bash
   python cli.py analyze "支付接口报错"
   python cli.py report --trace-id trace_12345
   ```

## 📊 自我评估

### 检查清单

**概念理解**：
- [ ] 理解 Structured Output 的作用
- [ ] 知道为什么需要 Policy 规则
- [ ] 理解工具的设计原则
- [ ] 掌握 Tool-Calling Loop 流程
- [ ] 知道如何检索 Runbook
- [ ] 理解调用轨迹的作用

**实践能力**：
- [ ] 能独立实现故障分类器
- [ ] 能添加 Policy 规则
- [ ] 能实现只读工具
- [ ] 能集成工具到 Agent
- [ ] 能实现 Runbook 检索
- [ ] 能记录和分析轨迹

**代码质量**：
- [ ] 代码能正常运行
- [ ] 有基本的错误处理
- [ ] 有必要的日志输出
- [ ] 代码结构清晰

### 你的水平

**如果完成 80% 以上**：✅ 优秀，可以进入第二周

**如果完成 60-80%**：⚠️ 良好，建议复习薄弱环节

**如果完成 < 60%**：❌ 需要重新学习，不要着急进入下一周

## 🎯 下周预告

**第二周：完整系统实现（Day 8-14）**

这周学了基础，下周要做完整系统：

**Day 8-9**: 多工具协同
- 工具组合使用
- 调用顺序优化
- 更智能的决策

**Day 10-11**: 错误处理与降级
- 超时处理
- 重试机制
- 降级策略

**Day 12-13**: 端到端集成
- 完整的故障分类器 v1.0
- 生产级代码
- 性能优化

**Day 14**: 第二周总结
- 系统 Demo
- 文档整理
- 准备评测

## 📝 第一周总结

**你已经走了多远**：
- ✅ 从零开始学习 Agent 开发
- ✅ 实现了 6 个核心模块
- ✅ 有了一个可工作的原型
- ✅ 理解了 Agent 的基本原理

**与普通开发者的区别**：
- 普通开发者：只会调用 API
- 你：理解原理、能设计系统、能处理边界情况

**下周目标**：
- 从原型到产品
- 从能用到好用
- 从玩具到工具

**好好休息，准备下周的挑战！** 🚀

---

**完成第一周的标志**：
- [ ] 所有 Day 1-6 的代码都能运行
- [ ] 完成了必做作业
- [ ] 写了测试报告
- [ ] 理解了所有核心概念

**准备好了就开始 Day 8！**
