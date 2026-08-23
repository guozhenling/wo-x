# 项目重构说明

## 📁 新的项目结构

项目已重新组织，将代码、测试、文档、示例分类清晰：

```
wo-x/
│
├── src/                    # 📦 核心代码
│   ├── __init__.py
│   ├── client.py          # LLM 客户端（OpenAI/Anthropic）
│   └── incident_triage.py # 故障分类器（多层校验）
│
├── tests/                  # 🧪 测试文件
│   ├── __init__.py
│   ├── test_cases.py      # 20 个生产测试用例
│   ├── run_tests.py       # 自动化测试框架
│   ├── test_validation.py # Pydantic 校验测试
│   └── test_claude_client.py # 客户端连接测试
│
├── examples/               # 💡 示例代码
│   ├── __init__.py
│   ├── demo.py            # 基础演示
│   ├── demo_incident.py   # 故障分类演示
│   └── quick_start.py     # 交互式工具
│
├── docs/                   # 📚 完整文档（9 个）
│   ├── README.md          # 项目总览
│   ├── TUTORIAL.md        # 新手教程
│   ├── ARCHITECTURE.md    # 系统架构
│   ├── SECURITY.md        # 安全设计
│   ├── FAILURES.md        # 故障模式与修正
│   ├── PRODUCTION_DECISIONS.md # 生产环境决策
│   ├── PROJECT_SUMMARY.md # 项目总结
│   ├── DOCS_INDEX.md      # 文档导航
│   └── CHECKLIST.md       # 项目清单
│
├── config.yaml            # API 配置
├── config.yaml.example    # 配置示例
├── requirements.txt       # Python 依赖
├── README.md              # 根目录总览（新）
├── .env.example          # 环境变量示例
└── .gitignore            # Git 忽略规则
```

## 🔄 与旧结构的对比

### 旧结构（混乱）
```
.
├── client.py              # 代码
├── incident_triage.py     # 代码
├── demo.py                # 示例
├── test_cases.py          # 测试
├── run_tests.py           # 测试
├── README.md              # 文档
├── TUTORIAL.md            # 文档
└── ...                    # 所有文件混在一起
```

### 新结构（清晰）
```
.
├── src/          # 所有核心代码
├── tests/        # 所有测试文件
├── examples/     # 所有示例代码
├── docs/         # 所有文档
└── README.md     # 项目入口
```

## ✅ 改进点

1. **分类清晰** - 代码、测试、文档、示例各归其位
2. **易于导航** - 一眼就能找到需要的文件
3. **Python 标准** - 符合 Python 项目最佳实践
4. **模块化** - src/ 是 Python 包，可以被导入
5. **可维护** - 新增文件时知道放在哪里

## 🚀 使用方法

### 运行示例

```bash
# 交互式工具
python examples/quick_start.py

# 基础演示
python examples/demo.py

# 故障分类演示
python examples/demo_incident.py
```

### 运行测试

```bash
# 测试客户端连接
python tests/test_claude_client.py

# 完整测试（20 个用例）
python tests/run_tests.py

# Pydantic 校验测试
python tests/test_validation.py
```

### 在代码中使用

```python
from src.client import LLMClient
from src.incident_triage import IncidentClassifier

# 初始化
client = LLMClient()
classifier = IncidentClassifier(client)

# 使用
result = classifier.classify("故障描述")
```

## 📝 路径处理

所有测试和示例文件都添加了路径设置：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from incident_triage import IncidentClassifier
```

这样无论从哪里运行，都能正确导入 src/ 中的模块。

## 🎯 快速导航

### 我想...

- **快速开始** → 看根目录 `README.md`
- **学习使用** → 看 `docs/README.md` 和 `docs/TUTORIAL.md`
- **了解架构** → 看 `docs/ARCHITECTURE.md`
- **生产部署** → 看 `docs/PRODUCTION_DECISIONS.md`
- **运行示例** → `python examples/quick_start.py`
- **运行测试** → `python tests/run_tests.py`
- **查看代码** → `src/` 目录
- **阅读文档** → `docs/` 目录

## 🔧 开发建议

### 添加新功能

1. **核心代码** → 放在 `src/`
2. **测试代码** → 放在 `tests/`
3. **示例代码** → 放在 `examples/`
4. **文档** → 放在 `docs/`

### 文件命名

- **核心模块** → `src/module_name.py`
- **测试文件** → `tests/test_module_name.py`
- **示例文件** → `examples/demo_feature.py`
- **文档文件** → `docs/FEATURE.md`

## ✅ 测试状态

所有功能已验证：

- ✅ 客户端连接正常
- ✅ Pydantic 校验正常
- ✅ 故障分类功能正常
- ✅ 所有 import 路径正确

## 📊 统计

- **核心代码**: 2 个文件
- **测试文件**: 4 个文件
- **示例代码**: 3 个文件
- **文档文件**: 9 个文件
- **总代码行数**: ~2000 行
- **总文档字数**: ~40,000 字

---

**重构完成！项目结构现在更加清晰、易于维护。**
