"""
改动方案：使用 ToolCoordinator 替代 LLM Tool-Calling Loop

## 现有问题

agent.py 让 LLM 自己决定调用哪些工具：
- 问题1：LLM 可能不调用工具（依赖 prompt）
- 问题2：LLM 可能一直重复调用（无限循环）
- 问题3：每轮都调用 LLM API（成本高）
- 问题4：调用顺序不可控

## 解决方案

使用 ToolCoordinator 替代，改为：

1. 快速分类（不用工具）
2. ToolCoordinator 规划并执行工具
3. 基于证据做最终分类

## 新的工作流

```python
def analyze(self, incident_description: str) -> Dict[str, Any]:
    # Step 1: 快速初步分类（无工具）
    initial_classification = self._quick_classify(incident_description)
    
    # Step 2: ToolCoordinator 规划工具调用
    coordinator = ToolCoordinator(self)
    coordinator.plan_tool_calls(incident_description, initial_classification)
    
    # Step 3: 执行工具（确定性，无需 LLM 决策）
    evidence = coordinator.execute_plan()
    
    # Step 4: 基于证据做最终分类
    final_classification = self._final_classify_with_evidence(
        incident_description,
        initial_classification,
        evidence
    )
    
    return final_classification
```

## 优势

1. **确定性**：P0/P1 一定会查 Runbook
2. **高效**：只调用 2 次 LLM（初步 + 最终），不是 N 轮
3. **可控**：明确的工具调用顺序和依赖
4. **成本低**：减少 60-80% 的 LLM 调用

## 需要修改的文件

1. `src/agent.py`：
   - 删除 Tool-Calling Loop
   - 添加 `_quick_classify()` - 快速分类
   - 添加 `_final_classify_with_evidence()` - 基于证据的最终分类
   - 在 `analyze()` 中使用 ToolCoordinator

2. `tools/tool_coordinator.py`：
   - 已完成，无需修改

## 实现细节

### _quick_classify() - 快速初步分类

```python
def _quick_classify(self, description: str) -> Dict[str, Any]:
    """
    快速初步分类（不调用工具）
    
    目的：
    1. 判断严重程度（P0/P1/P2/P3）
    2. 判断类别（availability/latency/database）
    3. 为 ToolCoordinator 提供规划依据
    
    不需要很准确，只是给 ToolCoordinator 提供线索
    """
    response = self.client.messages.create(
        model=self.model,
        max_tokens=1024,
        system="你是故障分类专家。快速判断严重程度和类别，输出 JSON。",
        messages=[{
            "role": "user",
            "content": f"快速分类：{description}\n\n输出格式：{{\"severity\": \"P0/P1/P2/P3\", \"category\": \"availability/latency/database/deployment/unknown\"}}"
        }]
    )
    
    text = response.content[0].text
    return json.loads(text)
```

### _final_classify_with_evidence() - 基于证据的最终分类

```python
def _final_classify_with_evidence(
    self,
    description: str,
    initial: Dict,
    evidence: Dict
) -> Dict[str, Any]:
    """
    基于证据做最终分类
    
    参数：
    - description: 故障描述
    - initial: 初步分类结果
    - evidence: 工具调用的证据
    
    返回：
    - 最终分类结果（包含 rationale）
    """
    # 构造 evidence 摘要
    evidence_summary = []
    for tool_name, result in evidence.items():
        evidence_summary.append(f"【{tool_name}】\n{json.dumps(result, ensure_ascii=False, indent=2)}")
    
    evidence_text = "\n\n".join(evidence_summary)
    
    prompt = f"""分析故障并给出最终判断。

【故障描述】
{description}

【初步判断】
严重程度: {initial['severity']}
类别: {initial['category']}

【收集的证据】
{evidence_text}

请基于以上证据，输出最终分类结果（纯 JSON）：
{{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须引用具体证据）"
}}
"""
    
    response = self.client.messages.create(
        model=self.model,
        max_tokens=2048,
        system="你是故障分析专家。基于证据做出准确判断。",
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text
    return self._parse_final_answer(text)
```

## 对比

### 旧方案（Tool-Calling Loop）
- LLM 调用次数：5 轮 = 5 次
- 工具调用：不确定（可能 0-N 次）
- Token 消耗：~8000 tokens
- 时间：~30 秒

### 新方案（ToolCoordinator）
- LLM 调用次数：2 次（初步 + 最终）
- 工具调用：确定（P0/P1 一定 2 次）
- Token 消耗：~3000 tokens
- 时间：~12 秒

**节省 60% 成本和时间！**

## 下一步

1. 创建 `src/agent_v2.py`（新版本）
2. 实现上述逻辑
3. 测试对比
4. 如果效果好，替换 `agent.py`
"""
