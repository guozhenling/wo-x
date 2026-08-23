# 故障分类器使用教程（Python 小白版）

## 📚 准备工作

### 1. 安装 Python 依赖包

打开终端（命令行），在项目目录下运行：

```bash
pip install -r requirements.txt
```

这会安装所有需要的包。

### 2. 配置 API

编辑 `config.yaml` 文件，填入你的 API 信息：

```yaml
api:
  base_url: "https://api.waibibabo.com/v1"  # 改成你的API地址
  api_key: "sk-xxxxx"                        # 改成你的API密钥
  model: "gpt-5.6-terra"                     # 改成你要使用的模型
  temperature: 0.7
  max_tokens: 1000
```

## 🚀 快速开始

### 最简单的使用方式

运行提供的快速入门脚本：

```bash
python quick_start.py
```

这个脚本会自动完成所有步骤，展示如何分类一个故障。

## 💡 详细说明

### 方法一：使用现成的代码（推荐新手）

1. 打开 `quick_start.py` 文件
2. 修改第 29 行的故障描述，改成你要分类的内容：
   ```python
   incident_description = "这里写你的故障描述"
   ```
3. 保存文件
4. 运行：`python quick_start.py`

### 方法二：在自己的代码中使用

创建一个新的 Python 文件（比如 `my_test.py`），写入以下代码：

```python
from client import LLMClient
from incident_triage import IncidentClassifier

# 1. 创建客户端
client = LLMClient()

# 2. 创建分类器
classifier = IncidentClassifier(client)

# 3. 准备故障描述
my_incident = "数据库连接失败，部分用户无法登录"

# 4. 进行分类
result = classifier.classify(my_incident)

# 5. 打印结果
print(f"严重程度：{result.severity}")
print(f"故障类别：{result.category}")
print(f"需要人工审核：{result.needs_human_review}")
print(f"理由：{result.rationale}")
```

然后运行：
```bash
python my_test.py
```

## 📖 代码解释

### 核心步骤

```python
# 导入类（就像从工具箱里拿出工具）
from client import LLMClient
from incident_triage import IncidentClassifier

# 创建客户端（连接到AI模型）
client = LLMClient()

# 创建分类器（准备好分类工具）
classifier = IncidentClassifier(client)

# 调用分类方法（开始分类）
result = classifier.classify("你的故障描述")

# 使用结果（查看分类结果）
print(result.severity)   # 严重程度：P0/P1/P2/P3
print(result.category)   # 类别：availability/latency/database等
print(result.needs_human_review)  # 是否需要人工审核：True/False
print(result.rationale)  # 分类理由
```

### 分类结果说明

| 字段 | 含义 | 可能的值 |
|------|------|----------|
| `severity` | 严重程度 | P0（紧急）、P1（高）、P2（中）、P3（低）|
| `category` | 故障类别 | availability（可用性）、latency（延迟）、database（数据库）、deployment（部署）、unknown（未知）|
| `needs_human_review` | 需要人工审核吗 | True（需要）、False（不需要）|
| `rationale` | 为什么这样分类 | 一段文字说明 |

## 🔧 进阶用法

### 批量分类多个故障

```python
from client import LLMClient
from incident_triage import IncidentClassifier

client = LLMClient()
classifier = IncidentClassifier(client)

# 准备多个故障描述
incidents = [
    "服务器宕机",
    "网站响应慢",
    "数据库查询超时"
]

# 批量分类
results = classifier.classify_batch(incidents)

# 查看每个结果
for i, result in enumerate(results):
    print(f"故障 {i+1}：{result.severity} - {result.category}")
```

## ⚠️ 常见问题

### 1. 运行报错：ModuleNotFoundError

**原因**：没有安装依赖包

**解决**：运行 `pip install -r requirements.txt`

### 2. 运行报错：FileNotFoundError: config.yaml

**原因**：配置文件不存在或路径不对

**解决**：确保在项目根目录下运行，且 config.yaml 文件存在

### 3. 运行报错：API 相关错误

**原因**：API配置不正确

**解决**：检查 config.yaml 中的 base_url 和 api_key 是否正确

### 4. 分类结果不准确

**原因**：故障描述不够详细

**解决**：提供更详细的故障信息，包括：
- 具体症状
- 影响范围
- 发生时间
- 错误信息

## 📝 示例

### 好的故障描述（推荐）

```python
incident = """
生产环境API服务在今天14:30开始出现问题：
- 所有/api/users接口返回502错误
- 影响100%的用户
- 错误日志显示数据库连接超时
- 持续时间已超过10分钟
"""
```

### 不好的故障描述（不推荐）

```python
incident = "出问题了"  # 太简单，无法准确分类
```

## 🎯 完整示例

完整的、可以直接运行的示例在 `quick_start.py` 文件中，建议先运行它熟悉流程。

运行后你会看到：
```
欢迎使用故障分类器！

正在初始化客户端...
✓ 客户端初始化成功

正在创建分类器...
✓ 分类器创建成功

故障描述：网站打不开了，所有用户都无法访问，报502错误

正在分类，请稍候...

============================================================
分类结果：
============================================================
严重程度：P0
故障类别：availability
需要人工审核：否
分类理由：服务完全不可用，影响所有用户，属于紧急故障
============================================================
```

## 💬 需要帮助？

如果遇到问题，可以：
1. 查看上面的"常见问题"部分
2. 检查 config.yaml 配置是否正确
3. 确认网络连接正常
4. 查看终端的错误信息
