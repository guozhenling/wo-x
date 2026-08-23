# Day 12-13 - 端到端集成与优化

**预计学习时间**: 2 天，每天 3 小时

## 🎯 学习目标

- 整合所有模块为完整系统
- 优化性能和代码质量
- 完成故障分类器 v1.0
- 准备生产部署

## 📖 核心概念

### 系统架构回顾

```
用户输入
    ↓
┌─────────────────────────────────────┐
│ IncidentAnalyzer (主入口)            │
│ - 初步分类                           │
│ - 工具调度                           │
│ - 结果整合                           │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ ToolCoordinator (Day 8-9)           │
│ - 规划工具调用                       │
│ - 管理依赖                           │
│ - 并行执行                           │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ RobustToolExecutor (Day 10-11)      │
│ - 超时保护                           │
│ - 自动重试                           │
│ - 降级方案                           │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ Tools (Day 3, 5)                    │
│ - search_logs                       │
│ - search_runbooks                   │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ PolicyEngine (Day 2)                │
│ - 规则修正                           │
│ - 安全兜底                           │
└──────┬──────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│ TraceManager (Day 6)                │
│ - 记录轨迹                           │
│ - 限制调用                           │
│ - 生成报告                           │
└──────┬──────────────────────────────┘
       ↓
最终输出：
- 故障分类
- 处理建议
- 证据链条
- 调用轨迹
```

## 🔍 完整系统实现

### 故障分类器 v1.0

```python
# incident_classifier_v1.py
"""
故障分类器 v1.0 - 生产就绪版本

整合：
- Day 1-2: Structured Output + Policy
- Day 3-5: 工具系统
- Day 6: 调用轨迹
- Day 8-9: 多工具协同
- Day 10-11: 错误处理
"""
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from models import IncidentResult
from policy import PolicyEngine
from tool_coordinator import ToolCoordinator
from robust_executor import RobustToolExecutor
from trace_manager import TraceManager

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IncidentClassifierV1:
    """
    故障分类器 v1.0
    
    特性：
    - ✓ 结构化输出
    - ✓ Policy 规则兜底
    - ✓ 多工具协同
    - ✓ 智能调度
    - ✓ 错误处理
    - ✓ 完整轨迹
    """
    
    VERSION = "1.0.0"
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.policy = PolicyEngine()
        self.executor = RobustToolExecutor()
        self.trace = None
        
        logger.info(f"初始化故障分类器 v{self.VERSION}")
    
    def classify(self, incident_description: str) -> Dict[str, Any]:
        """
        分类故障（完整流程）
        
        Args:
            incident_description: 故障描述
            
        Returns:
            完整的分析结果
        """
        start_time = datetime.now()
        
        # 初始化轨迹
        self.trace = TraceManager(
            max_calls_per_tool=2,
            max_total_calls=5,
            max_duration_seconds=30
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"开始分析故障")
        logger.info(f"描述: {incident_description}")
        logger.info(f"{'='*80}\n")
        
        try:
            # Step 1: 初步分类
            initial_classification = self._initial_classify(
                incident_description
            )
            logger.info(f"初步分类: {initial_classification['severity']}")
            
            # Step 2: 规划工具调用
            coordinator = ToolCoordinator(self)
            tool_plan = coordinator.plan_tool_calls(
                incident_description,
                initial_classification
            )
            logger.info(f"规划调用 {len(tool_plan)} 个工具")
            
            # Step 3: 执行工具调用
            evidence = coordinator.execute_plan()
            logger.info(f"收集证据: {len(evidence)} 个工具返回")
            
            # Step 4: 综合分析
            final_classification = self._final_classify(
                incident_description,
                initial_classification,
                evidence
            )
            
            # Step 5: Policy 规则修正
            final_classification = self.policy.check_and_enforce(
                incident_description,
                final_classification
            )
            
            # Step 6: 生成报告
            result = self._build_report(
                incident_description,
                final_classification,
                evidence,
                start_time
            )
            
            logger.info(f"\n✅ 分析完成")
            logger.info(f"最终判断: {result['classification']['severity']}")
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)
            return self._build_error_report(incident_description, e, start_time)
    
    def _initial_classify(self, description: str) -> Dict[str, Any]:
        """初步分类（快速）"""
        prompt = f"""分析故障并给出初步判断。

故障描述: {description}

输出 JSON:
{{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "简短依据"
}}"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _final_classify(
        self,
        description: str,
        initial: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """最终分类（基于证据）"""
        
        # 构造完整 prompt
        evidence_summary = self._summarize_evidence(evidence)
        
        prompt = f"""基于证据重新分析故障。

故障描述: {description}

初步判断: {initial['severity']} / {initial['category']}

证据:
{evidence_summary}

基于证据给出最终判断，输出 JSON:
{{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "基于证据的详细分析",
  "recommendation": "具体处理建议"
}}"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _summarize_evidence(self, evidence: Dict[str, Any]) -> str:
        """总结证据"""
        lines = []
        
        for tool_name, result in evidence.items():
            if isinstance(result, list):
                lines.append(f"- {tool_name}: {len(result)} 条记录")
            elif isinstance(result, dict) and not result.get("error"):
                lines.append(f"- {tool_name}: 成功")
            else:
                lines.append(f"- {tool_name}: 失败或降级")
        
        return "\n".join(lines)
    
    def _build_report(
        self,
        description: str,
        classification: Dict[str, Any],
        evidence: Dict[str, Any],
        start_time: datetime
    ) -> Dict[str, Any]:
        """构建完整报告"""
        duration = (datetime.now() - start_time).total_seconds()
        
        # 保存轨迹
        trace_file = self.trace.save_to_file("traces")
        
        return {
            "version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "description": description,
            "classification": classification,
            "evidence_summary": {
                tool: len(result) if isinstance(result, list) else "N/A"
                for tool, result in evidence.items()
            },
            "policy_violations": [
                {
                    "policy": v.policy_name,
                    "level": v.level.value,
                    "message": v.message
                }
                for v in self.policy.get_violations()
            ],
            "trace": {
                "trace_id": self.trace.trace_id,
                "total_calls": len(self.trace.tool_calls),
                "file": trace_file
            },
            "success": True
        }
    
    def _build_error_report(
        self,
        description: str,
        error: Exception,
        start_time: datetime
    ) -> Dict[str, Any]:
        """构建错误报告"""
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "description": description,
            "classification": {
                "severity": "P3",
                "category": "unknown",
                "needs_human_review": True,
                "rationale": "分析失败，需要人工介入"
            },
            "error": str(error),
            "success": False
        }

# 命令行工具
def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python incident_classifier_v1.py <故障描述>")
        print("\n示例:")
        print('  python incident_classifier_v1.py "支付接口 5xx 错误率 35%"')
        sys.exit(1)
    
    description = " ".join(sys.argv[1:])
    
    classifier = IncidentClassifierV1()
    result = classifier.classify(description)
    
    # 输出结果
    print(f"\n{'='*80}")
    print("分析结果")
    print(f"{'='*80}")
    print(f"严重程度: {result['classification']['severity']}")
    print(f"类别: {result['classification']['category']}")
    print(f"需要审核: {result['classification']['needs_human_review']}")
    print(f"\n分析依据:")
    print(result['classification']['rationale'])
    
    if result['classification'].get('recommendation'):
        print(f"\n处理建议:")
        print(result['classification']['recommendation'])
    
    print(f"\n调用统计:")
    print(f"  总调用: {result['trace']['total_calls']}")
    print(f"  耗时: {result['duration_seconds']}s")
    print(f"  轨迹: {result['trace']['file']}")
    
    if result.get('policy_violations'):
        print(f"\nPolicy 修正:")
        for v in result['policy_violations']:
            print(f"  - {v['policy']}: {v['message']}")

if __name__ == "__main__":
    main()
```

## 💪 动手练习

### Day 12: 系统集成（3 小时）

**任务**：
1. 整合所有模块
2. 运行完整测试
3. 修复集成问题

**验证**：
- [ ] 所有模块正常工作
- [ ] 端到端流程通畅
- [ ] 10 个测试案例通过

### Day 13: 性能优化（3 小时）

**任务**：
1. 性能分析
   - 找出瓶颈
   - 测量各步骤耗时

2. 优化
   - 并行化工具调用
   - 添加缓存
   - 优化 Prompt

3. 对比测试
   - 优化前后性能对比
   - 准确率是否下降

**验证**：
- [ ] 性能提升 30%+
- [ ] 准确率保持
- [ ] 性能测试报告

## ✅ 完成检查清单

- [ ] 完成系统集成
- [ ] 所有测试通过
- [ ] 性能优化完成
- [ ] 代码质量良好

## 🎯 Day 14 预告

**第二周总结**

最后一天：
- 系统 Demo
- 文档整理
- 第二周回顾
- 第三周准备

即将进入评测阶段！🚀
