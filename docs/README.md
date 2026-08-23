# 故障分类器 (Incident Classifier)

基于大语言模型的智能故障分类系统，使用 OpenAI 协议自动分析生产环境故障并进行分级分类。

## 功能特点

- 🎯 **自动分类**：智能识别故障严重程度（P0-P3）和类别
- 🤖 **AI驱动**：基于大语言模型的自然语言理解
- 📊 **高准确率**：经过 20 个生产案例测试，综合准确率达 90%
- 🔧 **灵活配置**：支持自定义 API base_url 和 api_key
- 💬 **交互式工具**：提供命令行交互界面，实时分类
- ⚡ **批量处理**：支持批量故障分类
- 🛡️ **安全可靠**：多层校验机制，绝不直接信任模型输出

## 安装依赖

推荐使用虚拟环境：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

## 配置

### API 协议支持

支持两种协议：
- **Anthropic** - Claude 模型（推荐：Sonnet 5）
- **OpenAI** - GPT 模型或兼容 OpenAI 协议的其他服务

### 方式一：使用配置文件（推荐）

编辑 `config.yaml` 文件：

#### Anthropic Claude (当前配置)

```yaml
api:
  protocol: "anthropic"
  api_key: "your-anthropic-api-key-here"
  model: "claude-sonnet-4-20250514"  # Sonnet 5
  temperature: 0.3
  max_tokens: 4096
```

#### OpenAI (备选配置)

```yaml
api:
  protocol: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: "your-openai-api-key-here"
  model: "gpt-4"
  temperature: 0.3
  max_tokens: 4096
```

参考 `config.yaml.example` 查看完整配置说明。

### 方式二：使用环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件填入你的配置。

## 使用方法

### 1. 交互式故障分类（推荐新手）

```bash
python quick_start.py
```

进入交互式界面，输入故障描述即可获得 JSON 格式的分类结果：

```
请输入故障描述：
> 支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟

正在分类...

分类结果：
{
  "severity": "P0",
  "category": "availability",
  "needs_human_review": true,
  "rationale": "支付接口属于直接影响收入的核心功能，5xx错误率升至35%..."
}
```

### 2. 运行演示脚本

```bash
# 基础对话演示
python demo.py

# 故障分类演示
python demo_incident.py
```

### 3. 在代码中使用

#### 基础 LLM 客户端

```python
from client import LLMClient

# 初始化客户端
client = LLMClient("config.yaml")

# 基础对话
response = client.chat(
    message="你好",
    system_prompt="你是一个助手"
)
print(response)

# 流式对话
for chunk in client.stream_chat(message="讲个笑话"):
    print(chunk, end="", flush=True)
```

#### 故障分类器

```python
from client import LLMClient
from incident_triage import IncidentClassifier

# 初始化
client = LLMClient()
classifier = IncidentClassifier(client)

# 单个故障分类
result = classifier.classify("支付接口 5xx 从 0.1% 升到 35%")
print(f"严重程度: {result.severity}")
print(f"故障类别: {result.category}")
print(f"需要人工审核: {result.needs_human_review}")
print(f"分类理由: {result.rationale}")

# 批量分类
descriptions = [
    "数据库主库 CPU 100% 持续 5 分钟",
    "首页加载时间从 200ms 升到 3s"
]
results = classifier.classify_batch(descriptions)
for result in results:
    print(result)
```

## 项目结构

```
.
├── client.py              # LLM客户端核心类
├── incident_triage.py     # 故障分类器（多层校验）
├── demo.py               # 基础演示脚本
├── demo_incident.py      # 故障分类演示
├── quick_start.py        # 交互式故障分类工具
├── test_cases.py         # 测试用例（20个生产场景）
├── run_tests.py          # 自动化测试脚本
├── test_validation.py    # Pydantic 校验测试
├── test_results.json     # 测试结果报告
├── config.yaml           # 配置文件
├── requirements.txt      # Python依赖
├── TUTORIAL.md           # 新手教程
├── SECURITY.md           # 安全设计文档
├── FAILURES.md           # 故障模式与修正策略
├── .env.example          # 环境变量示例
├── .gitignore           # Git忽略文件
└── README.md            # 项目说明
```

## 测试与验证

项目包含 20 个真实生产环境场景的测试用例，覆盖 P0-P3 各级别故障。

### 运行测试

```bash
python run_tests.py
```

### 测试结果

经过 20 个生产案例验证，分类器性能：

| 指标 | 准确率 |
|------|--------|
| **severity** (严重程度) | 100.0% |
| **category** (故障类别) | 90.0% |
| **needs_human_review** (人工审核) | 100.0% |
| **综合准确率** | 90.0% |

测试用例包括：
- **P0 级别**：支付故障、主站宕机、数据库崩溃、认证失败、缓存全挂
- **P1 级别**：搜索变慢、API 错误、上传异常、数据同步延迟、消息积压
- **P2 级别**：导出偶尔失败、邮件延迟、推荐不准、样式错乱、任务重试
- **P3 级别**：404 增多、报表变慢、内部工具慢、日志预警、开发环境问题

### 查看详细测试报告

```bash
cat test_results.json
```

## 故障分类说明

### 严重程度（Severity）

| 级别 | 错误率/影响 | 典型场景 |
|------|------------|----------|
| **P0** | >20% 或完全不可用 | 支付失败、交易中断、收入受损、数据丢失、主站宕机 |
| **P1** | 5%-20% | 核心功能部分不可用，有替代方案或影响部分用户 |
| **P2** | 1%-5% | 非核心功能异常，影响有限 |
| **P3** | <1% | 轻微影响，不影响核心业务 |

### 故障类别（Category）

- **availability**：可用性问题（服务不可用、接口超时、系统宕机）
- **latency**：性能问题（响应慢、查询慢、加载慢）
- **database**：数据库相关（数据库崩溃、慢查询、Redis/缓存问题）
- **deployment**：部署相关（发布失败、配置错误、静态资源加载失败）
- **unknown**：原因不明（日志异常、偶发错误、无明确故障点）

### 人工审核（needs_human_review）

- **P0/P1**：必须人工介入处理
- **P2/P3**：通常自动处理，特殊情况除外（涉及安全、数据、收入）

## 安全设计

本项目采用**多层校验机制**，绝不直接信任 LLM 输出：

### 三层防护

1. **JSON 格式校验** - 确保返回有效 JSON
2. **Pydantic Schema 校验** - 强制类型检查、枚举值验证、必填字段检查
3. **业务逻辑校验** - 确保分类结果符合业务规则（如 P0/P1 必须人工审核）

### 校验功能

- ✅ 枚举值严格匹配（severity 只能是 P0/P1/P2/P3）
- ✅ 类型强制检查（needs_human_review 必须是布尔值）
- ✅ 字段长度限制（rationale 10-500 字符）
- ✅ 业务规则自动修正
- ✅ 详细错误日志

**测试校验功能**：

```bash
python test_validation.py
```

详细安全设计参见 [SECURITY.md](SECURITY.md)

## 故障模式与修正

LLM 输出可能出现的问题及修正策略：

### 常见失败模式

1. **输出空理由或过短** - 通过 Pydantic min_length 拦截
2. **误判严重程度** - 通过业务上下文和关键词规则修正
3. **分类类别错误** - 通过优先级规则修正（database > deployment > latency）
4. **needs_human_review 不合理** - 通过业务规则自动修正

### 修正策略

- **Prompt 优化** - 添加业务上下文、分类优先级、思维链
- **Schema 约束** - Pydantic 强制校验、字段验证器
- **业务规则** - 关键词规则、一致性修正、优先级修正
- **多模型投票** - 降低单模型不稳定性

详细失败模式分析和修正策略参见 [FAILURES.md](FAILURES.md)

## 📚 文档导航

- **[DOCS_INDEX.md](DOCS_INDEX.md)** - 📖 完整文档导航（推荐从这里开始）
- **[TUTORIAL.md](TUTORIAL.md)** - 新手教程、详细使用说明
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 系统架构、数据流图
- **[SECURITY.md](SECURITY.md)** - 安全设计、多层校验机制
- **[FAILURES.md](FAILURES.md)** - 故障模式、修正策略、最佳实践
- **[PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md)** - ⭐ 生产环境决策指南（部署必读）
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - 项目完成总结

### 推荐阅读路径

- **新用户**：README → TUTORIAL → 实际操作
- **开发者**：README → ARCHITECTURE → SECURITY → FAILURES
- **生产部署**：SECURITY → FAILURES → **PRODUCTION_DECISIONS** ⭐⭐⭐

详见 [DOCS_INDEX.md](DOCS_INDEX.md)

## 兼容的服务

支持任何兼容 OpenAI API 协议的服务：

- OpenAI
- Azure OpenAI
- Claude (通过兼容层)
- 国内大模型服务（如智谱、百川等）
- 本地部署的开源模型（如 vLLM、Ollama 等）

只需修改 `base_url` 和 `api_key` 即可。

## 注意事项

- 请勿将包含真实 API key 的配置文件提交到版本控制
- `config.yaml` 和 `.env` 已添加到 `.gitignore`
- 建议使用环境变量或加密存储敏感信息
