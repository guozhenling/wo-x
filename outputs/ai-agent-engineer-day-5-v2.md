# Day 5 - 第二个工具：Runbook 检索

**预计学习时间**: 2.5 小时

## 🎯 学习目标

学完今天，你将：
- 理解 Runbook 的作用
- 掌握基于关键词的简单检索（不用向量数据库）
- 能实现 Runbook 匹配算法
- 知道如何组织运维知识

## 📖 核心概念

### 1. 什么是 Runbook？

**定义**：标准化的故障处理手册

**类比你熟悉的场景**：

**线下餐厅**：
```
问题: 客人投诉菜凉了
Runbook:
  1. 道歉
  2. 重新加热或做新的
  3. 赠送小菜
  4. 记录反馈
```

**软件系统**：
```yaml
title: 支付 5xx 错误处理
keywords: [支付, 5xx, payment, timeout]
check_steps:
  - 检查数据库连接
  - 检查支付网关状态
  - 查看最近部署
fix_steps:
  - 如果数据库问题 → 重启连接池
  - 如果网关问题 → 切换备用通道
  - 如果部署问题 → 回滚
```

**为什么需要 Runbook？**
- ✅ **标准化**：不同人处理方式一致
- ✅ **快速响应**：不用每次都想怎么办
- ✅ **知识沉淀**：老员工经验固化
- ✅ **可培训**：新人快速上手

### 2. 简单检索 vs 向量检索

**今天学习：关键词匹配**（简单但够用）

```python
# Runbook
keywords = ["支付", "5xx", "timeout"]

# 故障描述
description = "支付接口返回 503 错误"

# 匹配逻辑
score = 0
if "支付" in description: score += 10  # 关键词匹配
if "503" in description: score += 5    # 5xx 类似

# score = 15，相关度较高
```

**未来学习：向量检索**（更智能，但复杂）
```python
# 需要：OpenAI Embeddings + 向量数据库
embedding = openai.embeddings(description)
results = vector_db.search(embedding, top_k=3)
```

**对比**：
| 方式 | 优点 | 缺点 | 今天学习 |
|------|------|------|----------|
| 关键词 | 简单、快速、可控 | 需要精确匹配 | ✓ |
| 向量 | 语义理解 | 复杂、成本高 | Day 15 |

**80/20 原则**：
- 80% 的故障用关键词匹配就够了
- 只有 20% 需要语义理解

### 3. Runbook 文件格式

**YAML 格式**（推荐）：

```yaml
# runbooks/payment_5xx.yaml
title: 支付 5xx 错误处理
description: 支付接口返回 5xx 错误的处理流程
keywords:
  - 支付
  - 5xx
  - payment
  - timeout
  - gateway
severity_match:
  - P0
  - P1
check_steps:
  - 检查支付网关状态（curl gateway.internal/health）
  - 检查数据库连接（show processlist）
  - 查看最近 1 小时部署记录
  - 检查错误率趋势
fix_steps:
  - 如果网关返回 503：切换备用通道（payment_backup）
  - 如果数据库超时：重启连接池（kubectl rollout restart payment）
  - 如果部署后出现：回滚到上一版本
  - 如果持续时间 > 10 分钟：升级为 P0，通知 on-call
related_docs:
  - https://wiki.internal/payment-architecture
  - https://grafana.internal/payment-dashboard
```

**为什么用 YAML？**
- ✅ 人类可读
- ✅ 易于编辑
- ✅ 支持列表和嵌套
- ✅ 不需要数据库

### 4. 匹配算法

**计分规则**：

```python
score = 0

# 1. 关键词完全匹配 +10
for keyword in runbook.keywords:
    if keyword in description:
        score += 10

# 2. 标题匹配 +5
if any(word in description for word in runbook.title.split()):
    score += 5

# 3. 严重程度匹配 +3
if incident.severity in runbook.severity_match:
    score += 3

# 4. 类别匹配 +2
if incident.category == runbook.category:
    score += 2

# 阈值：score >= 10 才推荐
```

**示例**：

```
故障: "支付接口 5xx 错误率 30%"
严重程度: P0

Runbook A: 支付 5xx 处理
  - keywords: [支付, 5xx] → +20
  - severity_match: [P0, P1] → +3
  - score = 23 ✓ 推荐

Runbook B: 数据库死锁处理
  - keywords: [数据库, 死锁] → 0
  - score = 0 ✗ 不推荐
```

### 5. 工作流程

```
用户描述故障
    ↓
Agent 分类（Day 1-2）
    ↓
    severity = P0
    category = availability
    ↓
Agent 决定查日志（Day 4）
    ↓
    search_logs("payment")
    ↓
Agent 决定查 Runbook（今天）
    ↓
    search_runbooks(
        description="支付 5xx",
        severity="P0",
        category="availability"
    )
    ↓
返回匹配的 Runbook
    ↓
Agent 推荐处理步骤
```

## 🔍 完整示例

### 步骤 1: 创建 Runbook 文件

```bash
# 创建目录
mkdir -p runbooks

# Runbook 1: 支付 5xx
cat > runbooks/payment_5xx.yaml << 'EOF'
title: 支付 5xx 错误处理
description: 支付接口返回 5xx 错误的诊断和修复步骤
keywords:
  - 支付
  - 5xx
  - payment
  - gateway
  - timeout
severity_match:
  - P0
  - P1
category: availability
check_steps:
  - 检查支付网关状态
  - 检查数据库连接池
  - 查看最近的部署记录
  - 检查第三方支付渠道状态
fix_steps:
  - 如果网关问题：切换备用支付渠道
  - 如果数据库问题：重启连接池
  - 如果部署问题：回滚到上一版本
  - 如果第三方问题：联系支付供应商
EOF

# Runbook 2: 数据库死锁
cat > runbooks/database_deadlock.yaml << 'EOF'
title: 数据库死锁处理
description: MySQL 死锁问题的排查和解决
keywords:
  - 数据库
  - 死锁
  - deadlock
  - mysql
  - 1205
severity_match:
  - P1
  - P2
category: database
check_steps:
  - 查看死锁日志（SHOW ENGINE INNODB STATUS）
  - 分析事务持有的锁
  - 检查慢查询日志
fix_steps:
  - 优化事务顺序（统一锁获取顺序）
  - 减少事务持有时间
  - 添加索引减少锁范围
  - 如果紧急：kill 长事务
EOF

# Runbook 3: 部署回滚
cat > runbooks/deployment_rollback.yaml << 'EOF'
title: 部署回滚流程
description: 发布后出现问题的回滚步骤
keywords:
  - 部署
  - 发布
  - 回滚
  - rollback
  - deployment
severity_match:
  - P0
  - P1
category: deployment
check_steps:
  - 确认问题出现在发布之后
  - 检查发布的版本号
  - 确认回滚目标版本
  - 评估回滚影响范围
fix_steps:
  - 停止灰度流量
  - 执行回滚命令（kubectl rollout undo）
  - 验证回滚后功能正常
  - 通知相关团队
  - 分析问题原因
EOF
```

### 步骤 2: 实现 Runbook 检索

```python
# tools/runbook_search.py
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml

class Runbook:
    """Runbook 数据结构"""
    
    def __init__(self, data: dict, file_path: str):
        self.title = data.get('title', '')
        self.description = data.get('description', '')
        self.keywords = data.get('keywords', [])
        self.severity_match = data.get('severity_match', [])
        self.category = data.get('category', '')
        self.check_steps = data.get('check_steps', [])
        self.fix_steps = data.get('fix_steps', [])
        self.related_docs = data.get('related_docs', [])
        self.file_path = file_path
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "description": self.description,
            "check_steps": self.check_steps,
            "fix_steps": self.fix_steps,
            "related_docs": self.related_docs
        }

class RunbookSearcher:
    """
    Runbook 检索器
    
    基于关键词匹配的简单检索
    """
    
    def __init__(self, runbooks_dir: str = "runbooks"):
        self.runbooks_dir = Path(runbooks_dir)
        self.runbooks: List[Runbook] = []
        self._load_runbooks()
    
    def _load_runbooks(self):
        """加载所有 Runbook"""
        if not self.runbooks_dir.exists():
            print(f"⚠️  Runbook 目录不存在: {self.runbooks_dir}")
            return
        
        for yaml_file in self.runbooks_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.runbooks.append(Runbook(data, str(yaml_file)))
            except Exception as e:
                print(f"⚠️  加载 {yaml_file} 失败: {e}")
        
        print(f"✓ 加载了 {len(self.runbooks)} 个 Runbook")
    
    def search(
        self,
        description: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        检索相关 Runbook
        
        Args:
            description: 故障描述
            severity: 严重程度（P0/P1/P2/P3）
            category: 类别
            top_k: 返回最相关的 N 个
            
        Returns:
            匹配的 Runbook 列表，按相关度排序
        """
        if not self.runbooks:
            return []
        
        # 计算每个 Runbook 的相关度
        scored_runbooks = []
        for runbook in self.runbooks:
            score = self._calculate_score(
                runbook,
                description,
                severity,
                category
            )
            
            if score >= 10:  # 阈值
                scored_runbooks.append({
                    "runbook": runbook.to_dict(),
                    "score": score,
                    "match_reason": self._explain_match(
                        runbook,
                        description,
                        severity,
                        category
                    )
                })
        
        # 按分数排序
        scored_runbooks.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_runbooks[:top_k]
    
    def _calculate_score(
        self,
        runbook: Runbook,
        description: str,
        severity: Optional[str],
        category: Optional[str]
    ) -> float:
        """计算相关度分数"""
        score = 0.0
        description_lower = description.lower()
        
        # 1. 关键词完全匹配 +10
        for keyword in runbook.keywords:
            if keyword.lower() in description_lower:
                score += 10
        
        # 2. 标题词匹配 +5
        title_words = runbook.title.lower().split()
        for word in title_words:
            if len(word) > 2 and word in description_lower:
                score += 5
                break
        
        # 3. 严重程度匹配 +3
        if severity and severity in runbook.severity_match:
            score += 3
        
        # 4. 类别匹配 +2
        if category and category == runbook.category:
            score += 2
        
        return score
    
    def _explain_match(
        self,
        runbook: Runbook,
        description: str,
        severity: Optional[str],
        category: Optional[str]
    ) -> str:
        """解释为什么匹配"""
        reasons = []
        
        description_lower = description.lower()
        
        # 关键词匹配
        matched_keywords = [
            kw for kw in runbook.keywords
            if kw.lower() in description_lower
        ]
        if matched_keywords:
            reasons.append(f"关键词匹配: {', '.join(matched_keywords)}")
        
        # 严重程度匹配
        if severity and severity in runbook.severity_match:
            reasons.append(f"严重程度匹配: {severity}")
        
        # 类别匹配
        if category and category == runbook.category:
            reasons.append(f"类别匹配: {category}")
        
        return "; ".join(reasons) if reasons else "通用匹配"

# 测试
if __name__ == "__main__":
    searcher = RunbookSearcher()
    
    print("\n测试 1: 支付 5xx")
    print("=" * 60)
    results = searcher.search(
        description="支付接口 5xx 错误率 30%",
        severity="P0",
        category="availability"
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['runbook']['title']} (分数: {result['score']})")
        print(f"   匹配原因: {result['match_reason']}")
        print(f"   检查步骤: {result['runbook']['check_steps'][0]}")
    
    print("\n测试 2: 数据库死锁")
    print("=" * 60)
    results = searcher.search(
        description="MySQL 报 1205 死锁错误",
        severity="P1",
        category="database"
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['runbook']['title']} (分数: {result['score']})")
        print(f"   匹配原因: {result['match_reason']}")
```

**运行测试**：
```bash
python tools/runbook_search.py
```

### 步骤 3: 添加到工具定义

```python
# tools/tool_definitions.py 中添加
def get_search_runbooks_definition() -> Dict[str, Any]:
    """Runbook 检索工具定义"""
    return {
        "type": "function",
        "function": {
            "name": "search_runbooks",
            "description": """检索相关的故障处理手册（Runbook）。

使用场景：
- 当需要查找标准处理流程时
- 当需要检查步骤和修复建议时

返回：
- 相关 Runbook 列表
- 包含检查步骤和修复步骤""",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "故障描述"
                    },
                    "severity": {
                        "type": "string",
                        "description": "严重程度",
                        "enum": ["P0", "P1", "P2", "P3"]
                    },
                    "category": {
                        "type": "string",
                        "description": "故障类别",
                        "enum": ["availability", "latency", "database", "deployment"]
                    }
                },
                "required": ["description"]
            }
        }
    }

def get_all_tool_definitions() -> list:
    """返回所有工具定义"""
    return [
        get_search_logs_definition(),
        get_search_runbooks_definition()  # 新增
    ]
```

### 步骤 4: 添加到工具执行器

```python
# tools/executor.py 中添加
from tools.runbook_search import RunbookSearcher

# 全局实例（避免重复加载）
_runbook_searcher = None

def get_runbook_searcher():
    global _runbook_searcher
    if _runbook_searcher is None:
        _runbook_searcher = RunbookSearcher()
    return _runbook_searcher

def search_runbooks(
    description: str,
    severity: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """检索 Runbook（包装函数）"""
    searcher = get_runbook_searcher()
    return searcher.search(description, severity, category, top_k=3)

# 更新注册表
TOOL_REGISTRY = {
    "search_logs": search_logs,
    "search_runbooks": search_runbooks,  # 新增
}
```

## 💪 动手练习

### Level 1: 最低完成线（30 分钟）

**任务**：
- [ ] 创建 3 个 Runbook 文件
- [ ] 实现 RunbookSearcher
- [ ] 测试关键词匹配

**验证**：能检索到相关 Runbook

### Level 2: 标准任务（1 小时）

**任务**：
1. 扩展到 8 个 Runbook，覆盖：
   - 支付 5xx
   - 数据库死锁
   - 部署回滚
   - 缓存雪崩
   - API 限流
   - 磁盘满
   - 内存泄漏
   - 日志暴增

2. 测试各种匹配场景

3. 调整计分规则

**验证**：8 个 Runbook，匹配准确

### Level 3: 进阶任务（1 小时）

**任务**：
1. 添加模糊匹配：
   ```python
   from difflib import SequenceMatcher
   
   similarity = SequenceMatcher(None, keyword, word).ratio()
   if similarity > 0.8:
       score += 5
   ```

2. 添加同义词：
   ```python
   synonyms = {
       "5xx": ["500", "502", "503", "504"],
       "慢": ["延迟", "超时", "卡顿"]
   }
   ```

3. 记录检索日志

**验证**：模糊匹配、同义词工作

## ✅ 完成检查清单

- [ ] 理解 Runbook 的作用
- [ ] 掌握关键词匹配算法
- [ ] 实现了 RunbookSearcher
- [ ] 创建了多个 Runbook
- [ ] 集成到工具系统

## 🎯 明天预告

**Day 6: 调用轨迹管理**

现在 Agent 有 2 个工具了，但调用过程不透明：
- 调用了几次？
- 为什么调用？
- 结果是什么？

明天学习完整的轨迹管理系统！

休息一下，明天见！🚀
