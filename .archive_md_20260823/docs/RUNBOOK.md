# 运行手册系统文档

## 概述

运行手册系统提供故障处理的标准化文档和自动推荐功能。当故障分类器识别出故障类型后，系统会自动推荐相关的运行手册，帮助工程师快速定位处理步骤。

**核心理念**：将常见故障的处理经验沉淀为结构化文档，通过关键词匹配快速检索，提高故障处理效率。

## 架构

```
故障描述
    ↓
故障分类器
    ↓
运行手册检索器 (关键词匹配)
    ↓
推荐运行手册列表 (按匹配度排序)
    ↓
人工执行处理步骤
```

## 运行手册格式

每个运行手册是一个 YAML 文件，包含以下字段：

```yaml
# 运行手册元数据
runbook_id: "RB-001"           # 运行手册唯一ID
title: "支付接口 5xx 错误处理"   # 标题
version: "1.0"                  # 版本号
last_updated: "2024-01-15"     # 最后更新日期

# 检索关键词（用于匹配）
keywords:
  - 支付
  - 5xx
  - 502
  - 503
  - 网关错误

# 适用条件
applicable_conditions:
  - 支付接口返回 5xx 错误
  - 错误率超过 5%
  - 用户支付失败

# 检查步骤
check_steps:
  - step: 1
    action: "查看支付服务监控大盘"
    details: "登录 Grafana，查看支付服务的错误率、QPS、响应时间"
    
  - step: 2
    action: "检查上游依赖"
    details: "查看银行网关、第三方支付接口的可用性"

# 人工升级条件
escalation_conditions:
  - 错误率持续超过 20% 且 5 分钟内未恢复
  - 影响 VIP 用户或大额交易
  - 需要协调外部团队（银行、支付平台）
```

## 核心类

### RunbookMatch

运行手册匹配结果：

```python
@dataclass
class RunbookMatch:
    runbook_id: str                  # 运行手册 ID
    title: str                       # 标题
    score: float                     # 匹配得分 (0-1)
    matched_keywords: List[str]      # 匹配到的关键词
    applicable_conditions: List[str] # 适用条件
    check_steps: List[Dict]          # 检查步骤
    escalation_conditions: List[str] # 人工升级条件
```

### RunbookSearcher

运行手册检索器：

```python
class RunbookSearcher:
    def __init__(self, runbooks_dir: str):
        """初始化检索器，加载所有运行手册"""
        
    def search(self, query: str, top_k: int = 3) -> List[RunbookMatch]:
        """搜索相关运行手册，返回 top_k 个最匹配的"""
        
    def _calculate_score(self, query: str, keywords: List[str]) -> Tuple[float, List[str]]:
        """计算匹配得分和匹配的关键词"""
```

## 使用方法

### 方式 1: 独立使用

```python
from runbook_search import RunbookSearcher

# 初始化检索器
searcher = RunbookSearcher("runbooks")

# 搜索运行手册
matches = searcher.search("支付接口返回 502 错误", top_k=3)

for match in matches:
    print(f"运行手册: {match.title}")
    print(f"匹配度: {match.score:.2f}")
    print(f"匹配关键词: {', '.join(match.matched_keywords)}")
    print()
    
    # 显示检查步骤
    for step in match.check_steps:
        print(f"  步骤 {step['step']}: {step['action']}")
        print(f"    {step['details']}")
```

### 方式 2: 集成到故障分类器

```python
from client import LLMClient
from incident_triage import IncidentClassifier

# 初始化分类器（自动加载运行手册）
client = LLMClient()
classifier = IncidentClassifier(client)

# 分类故障
description = "支付接口返回 502 错误，错误率 25%"
result = classifier.classify(description)

# 推荐运行手册
runbooks = classifier.recommend_runbooks(description, top_k=2)

if runbooks:
    print(f"找到 {len(runbooks)} 个相关运行手册：")
    for rb in runbooks:
        print(f"- {rb.title} (匹配度: {rb.score:.2f})")
```

## 匹配算法

### 关键词匹配

1. **分词**：将查询文本分词为关键词列表
2. **匹配计数**：统计查询中出现的运行手册关键词数量
3. **计算得分**：
   ```
   score = matched_count / total_keywords
   ```
4. **排序**：按得分降序排列，返回 top_k 个

### 示例

```
查询: "支付接口返回 502 错误"
运行手册关键词: ["支付", "5xx", "502", "503", "网关错误"]

匹配过程:
- "支付" ✓ 匹配
- "502"  ✓ 匹配
- "5xx"  ✓ 匹配（因为502属于5xx）
- "503"  ✗ 未匹配
- "网关错误" ✗ 未匹配

匹配得分: 3/5 = 0.60
```

## 现有运行手册

### 1. 支付接口 5xx 错误处理

**文件**: `runbooks/payment_5xx.yaml`

**关键词**: 支付、5xx、502、503、网关错误、超时

**适用场景**:
- 支付接口返回 5xx 错误
- 错误率超过 5%
- 用户支付失败

**检查步骤**:
1. 查看支付服务监控大盘
2. 检查上游依赖（银行网关、第三方支付）
3. 查看支付服务日志
4. 检查数据库连接池和慢查询

### 2. 数据库死锁处理

**文件**: `runbooks/db_deadlock.yaml`

**关键词**: 数据库、死锁、deadlock、锁等待、事务

**适用场景**:
- 数据库日志出现 "Deadlock found"
- 订单表、库存表被锁定
- 事务超时错误

**检查步骤**:
1. 查看死锁日志
2. 分析涉及的表和事务
3. 检查慢查询
4. Kill 长时间运行的事务

### 3. 发布回滚处理

**文件**: `runbooks/rollback.yaml`

**关键词**: 发布、回滚、rollback、错误率上升、部署

**适用场景**:
- 发布后错误率从 <1% 上升到 >10%
- 新版本导致的功能异常
- 配置错误导致的服务不可用

**检查步骤**:
1. 确认发布版本和时间
2. 对比发布前后的错误率
3. 检查新版本的错误日志
4. 执行回滚操作

## 添加新运行手册

### 步骤

1. **创建 YAML 文件**：在 `runbooks/` 目录下创建新文件

```yaml
runbook_id: "RB-004"
title: "Redis 连接池耗尽处理"
version: "1.0"
last_updated: "2024-01-15"

keywords:
  - Redis
  - 连接池
  - 连接耗尽
  - too many connections

applicable_conditions:
  - Redis 连接数接近最大值
  - 应用日志显示 "Could not get a resource from the pool"
  - 缓存读写超时

check_steps:
  - step: 1
    action: "查看 Redis 连接数"
    details: "执行 redis-cli INFO clients，查看 connected_clients"
    
  - step: 2
    action: "检查应用连接池配置"
    details: "查看 maxTotal、maxIdle、minIdle 配置是否合理"
    
  - step: 3
    action: "检查连接泄漏"
    details: "查找应用中未关闭的 Redis 连接"

escalation_conditions:
  - 连接数持续增长且重启应用后复现
  - 需要调整 Redis 最大连接数配置
```

2. **测试检索**：

```python
searcher = RunbookSearcher("runbooks")
matches = searcher.search("Redis 连接池耗尽", top_k=1)
assert len(matches) > 0
assert "Redis" in matches[0].title
```

3. **更新文档**：在本文档中补充新运行手册的说明

## 最佳实践

1. **关键词选择**
   - 包含故障的核心术语（如"支付"、"数据库"、"5xx"）
   - 包含常见的错误信息（如"deadlock"、"timeout"）
   - 包含业务术语（如"订单"、"库存"）
   - 避免过于宽泛的词（如"错误"、"问题"）

2. **适用条件**
   - 具体描述故障现象（错误信息、监控指标、用户反馈）
   - 包含触发阈值（如"错误率超过 5%"）
   - 区分不同严重程度的场景

3. **检查步骤**
   - 步骤顺序：从简单到复杂，从快速检查到深入分析
   - 包含具体操作命令和工具
   - 每个步骤都有明确的预期结果
   - 标注需要的权限和注意事项

4. **人工升级条件**
   - 明确何时需要升级到高级工程师或专家
   - 包含时间阈值（如"5 分钟内未恢复"）
   - 包含影响范围阈值（如"影响 VIP 用户"）
   - 包含需要跨团队协作的情况

## 扩展方向

### 1. 向量检索

当前使用关键词匹配，未来可以升级为向量检索：

```python
# 使用 embedding 模型
embeddings = model.encode([query] + all_runbook_texts)
similarities = cosine_similarity(embeddings[0:1], embeddings[1:])[0]
top_indices = similarities.argsort()[::-1][:top_k]
```

**优势**：
- 语义理解更准确
- 支持同义词和近义词
- 支持长文本匹配

**劣势**：
- 需要引入 embedding 模型（如 sentence-transformers）
- 计算开销更大
- 需要预先计算和缓存向量

### 2. 运行手册版本管理

```yaml
runbook_id: "RB-001"
version: "2.0"
changelog:
  - version: "2.0"
    date: "2024-02-01"
    changes:
      - "新增步骤：检查 Nginx 日志"
      - "修改升级条件：从 10% 改为 20%"
  - version: "1.0"
    date: "2024-01-15"
    changes:
      - "初始版本"
```

### 3. 运行手册执行反馈

记录运行手册的执行结果，用于优化：

```python
@dataclass
class RunbookFeedback:
    runbook_id: str
    incident_id: str
    executed_at: datetime
    success: bool                # 是否解决问题
    time_to_resolve: int         # 解决时间（分钟）
    steps_executed: List[int]    # 实际执行的步骤
    comments: str                # 反馈意见
```

### 4. 自动化执行

将运行手册的部分步骤自动化：

```yaml
check_steps:
  - step: 1
    action: "查看 Redis 连接数"
    details: "执行 redis-cli INFO clients"
    automated: true              # 可自动执行
    command: "redis-cli INFO clients | grep connected_clients"
    
  - step: 2
    action: "重启 Redis"
    details: "执行重启命令"
    automated: false             # 需要人工确认
    requires_approval: true
```

## 监控指标

建议监控以下指标：

```python
# 运行手册使用统计
runbook.search_count                    # 搜索次数
runbook.match_rate                      # 匹配成功率
runbook.avg_match_score                 # 平均匹配分数

# 运行手册效果
runbook.execution_count{id="RB-001"}   # 每个运行手册的执行次数
runbook.success_rate{id="RB-001"}      # 每个运行手册的成功率
runbook.avg_resolution_time{id="RB-001"} # 平均解决时间
```

## 总结

运行手册系统通过 **关键词匹配检索**，实现：

1. ✅ 将故障处理经验结构化沉淀
2. ✅ 自动推荐相关处理步骤
3. ✅ 降低故障处理门槛
4. ✅ 提高故障处理效率
5. ✅ 支持新工程师快速上手

**核心价值**: 标准化故障处理流程，让每个工程师都能按照最佳实践处理故障。
