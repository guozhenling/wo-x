# 文档导航

## 📚 完整文档体系

本项目提供了完整的文档体系，涵盖从快速开始到生产部署的所有内容。

---

## 🚀 快速开始

### 1. [README.md](README.md) - 项目总览
**适合人群**：所有人  
**阅读时间**：5 分钟

**内容**：
- 项目简介和功能特点
- 快速开始指南
- 基础使用示例
- 测试结果概览
- 项目结构

**何时阅读**：第一次接触项目时

---

### 2. [TUTORIAL.md](TUTORIAL.md) - 新手教程
**适合人群**：新用户  
**阅读时间**：15 分钟

**内容**：
- 详细的安装步骤
- 配置文件说明
- 三种使用方式（交互式、脚本、代码集成）
- 常见问题解答
- 故障排查

**何时阅读**：第一次使用项目时

---

## 🏗️ 架构与设计

### 3. [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构
**适合人群**：开发者、架构师  
**阅读时间**：10 分钟

**内容**：
- 系统架构图
- 数据流图
- 多层校验架构
- 测试流程
- 配置文件结构

**何时阅读**：需要理解系统设计时

---

### 4. [SECURITY.md](SECURITY.md) - 安全设计
**适合人群**：开发者、安全工程师  
**阅读时间**：15 分钟

**内容**：
- 核心原则：绝不信任模型输出
- 三层防护机制详解
- Pydantic 强类型验证
- 业务规则修正
- 日志与审计
- 最佳实践

**何时阅读**：
- 需要理解安全机制时
- 准备生产部署前
- 代码审查时

---

## 🔧 深度指南

### 5. [FAILURES.md](FAILURES.md) - 故障模式与修正策略
**适合人群**：开发者、SRE  
**阅读时间**：30 分钟

**内容**：
- 5 种常见失败模式
  - 输出空理由
  - 误判严重程度
  - 分类类别错误
  - needs_human_review 不合理
  - JSON 格式不合规
- 4 种修正策略
  - Prompt 优化
  - Schema 约束
  - 业务规则修正
  - 多模型投票
- 3 个实战案例详解
- 最佳实践和监控指标

**何时阅读**：
- 遇到分类不准确时
- 需要优化系统时
- 准备生产部署前

**重要性**：⭐⭐⭐⭐⭐

---

### 6. [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 生产环境决策指南
**适合人群**：技术负责人、SRE、架构师  
**阅读时间**：45 分钟

**内容**：
- **问题 1**：哪些判断交给模型，哪些必须由规则兜底？
  - 决策矩阵
  - 详细分析（5 个判断维度）
  - 最佳实践
  
- **问题 2**：如果触发 PagerDuty，需要什么审批或阈值？
  - 人工确认机制
  - 双模型确认
  - 5 种阈值设计
  - 分阶段部署策略
  - 误报补救机制
  
- **问题 3**：模型未按 Schema 返回时，重试、降级还是拒绝？
  - 策略矩阵
  - 重试→降级→拒绝流程
  - 完整实现代码
  - 监控指标

**何时阅读**：
- 准备生产部署前（必读）
- 需要理解关键决策时
- 遇到生产问题时

**重要性**：⭐⭐⭐⭐⭐（生产必读）

---

### 7. [POLICY.md](POLICY.md) - Policy 规则引擎文档
**适合人群**：开发者、SRE  
**阅读时间**：20 分钟

**内容**：
- Policy 规则引擎架构
- 7 条确定性规则详解
  - 高优先级必须人工复核
  - 未知原因谦逊原则
  - 收入影响高优先级
  - 内部工具优先级限制
  - 核心服务宕机必须 P0
  - 数据安全必须审核
  - 错误率阈值强制规则
- 使用方法和最佳实践
- 规则执行顺序和优先级
- PolicyViolation 记录和监控

**何时阅读**：
- 需要理解 Policy 规则时
- 需要添加新规则时
- 规则触发时排查问题

**重要性**：⭐⭐⭐⭐

---

### 8. [RUNBOOK.md](RUNBOOK.md) - 运行手册系统文档 ⭐ 新增
**适合人群**：开发者、SRE  
**阅读时间**：15 分钟

**内容**：
- 运行手册系统架构和设计理念
- 运行手册 YAML 格式规范
- 关键词匹配检索算法
- 核心类（RunbookMatch、RunbookSearcher）
- 现有运行手册（支付 5xx、数据库死锁、发布回滚）
- 使用方法和集成示例
- 添加新运行手册的步骤
- 最佳实践和扩展方向

**何时阅读**：
- 需要查询运行手册时
- 需要添加新运行手册时
- 需要理解检索系统实现时

**重要性**：⭐⭐⭐

---

### 9. [LOG_SEARCH.md](LOG_SEARCH.md) - 日志搜索工具文档 ⭐
**适合人群**：开发者、SRE  
**阅读时间**：15 分钟

**内容**：
- 日志搜索工具功能和特性
- API 使用方法和参数说明
- 数据模型（LogEntry、SearchResult）
- 参数校验和超时保护机制
- 性能指标和最佳实践
- 8 个使用场景演示
- 错误处理和边界情况

**何时阅读**：
- 需要查询日志时
- 需要集成日志搜索功能时
- 需要理解日志工具实现时

**重要性**：⭐⭐⭐

---

### 10. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目完成总结
**适合人群**：所有人  
**阅读时间**：10 分钟

**内容**：
- 项目概览
- 已完成功能清单
- 测试结果
- 技术栈
- 生产部署建议
- 学习资源

**何时阅读**：
- 需要快速了解项目全貌时
- 向他人介绍项目时

---

## 📖 推荐阅读路径

### 路径 1：新用户（第一次使用）

```
README.md (5分钟)
    ↓
TUTORIAL.md (15分钟)
    ↓
实际操作: python quick_start.py
    ↓
查看测试: python run_tests.py
```

**总时间**：30 分钟  
**目标**：能够使用项目

---

### 路径 2：开发者（理解设计）

```
README.md (5分钟)
    ↓
ARCHITECTURE.md (10分钟)
    ↓
SECURITY.md (15分钟)
    ↓
POLICY.md (20分钟) ⭐
    ↓
阅读核心代码: incident_triage.py, policy.py
    ↓
FAILURES.md (30分钟)
```

**总时间**：1.5 小时  
**目标**：理解系统设计和安全机制

---

### 路径 3：生产部署（准备上线）

```
README.md (5分钟)
    ↓
SECURITY.md (15分钟) ⭐
    ↓
FAILURES.md (30分钟) ⭐
    ↓
PRODUCTION_DECISIONS.md (45分钟) ⭐⭐⭐
    ↓
运行完整测试验证
    ↓
制定部署计划
```

**总时间**：2 小时  
**目标**：安全地部署到生产环境

**关键文档**：
- ⭐⭐⭐ PRODUCTION_DECISIONS.md（必读）
- ⭐⭐ FAILURES.md（强烈推荐）
- ⭐ SECURITY.md（推荐）

---

### 路径 4：问题排查（遇到问题）

#### 4.1 分类不准确

```
FAILURES.md
    ↓ 查找对应的失败模式
    ↓
应用修正策略
    ↓
运行测试验证
```

#### 4.2 安全问题

```
SECURITY.md
    ↓ 查看多层防护机制
    ↓
运行: python test_validation.py
```

#### 4.3 配置问题

```
TUTORIAL.md - 配置章节
    ↓
检查 config.yaml
    ↓
运行: python demo.py
```

---

## 🎯 按场景查找

### 场景 1：我想快速开始使用

→ [README.md](README.md) + [TUTORIAL.md](TUTORIAL.md)

---

### 场景 2：我想理解系统是如何保证安全的

→ [SECURITY.md](SECURITY.md) + [ARCHITECTURE.md](ARCHITECTURE.md)

---

### 场景 3：模型分类不准确，我想优化

→ [FAILURES.md](FAILURES.md) - 查看对应的失败模式和修正策略  
→ [POLICY.md](POLICY.md) - 检查 Policy 规则是否可以兜底

---

### 场景 4：我想部署到生产环境

→ [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md)（必读） + [SECURITY.md](SECURITY.md)

---

### 场景 5：我想理解为什么要这样设计

→ [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 1  
→ [POLICY.md](POLICY.md) - Policy 规则设计理念

---

### 场景 6：我想配置 PagerDuty 触发

→ [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 2

---

### 场景 7：模型返回了无效的 JSON，我该怎么办

→ [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 3

---

### 场景 8：我想了解测试覆盖情况

→ [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 测试与验证章节

---

### 场景 9：我想查询故障相关的日志 ⭐ 新增

→ [LOG_SEARCH.md](LOG_SEARCH.md) - 日志搜索工具使用指南

---

## 📊 文档关系图

```
                    README.md (入口)
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   TUTORIAL.md    ARCHITECTURE.md  PROJECT_SUMMARY.md
   (使用教程)      (系统架构)       (项目总结)
        ↓               ↓
        └───────────────┼───────────────┐
                        ↓               ↓
                   SECURITY.md     FAILURES.md
                   (安全设计)       (故障模式)
                        ↓               ↓
                   POLICY.md       LOG_SEARCH.md ⭐
                   (规则引擎)       (日志搜索)
                        ↓               ↓
                        └───────────────┘
                                ↓
                    PRODUCTION_DECISIONS.md
                    (生产环境决策指南)
                         ↓
                    生产部署 ✅
```

---

## 🔍 关键词索引

### 安全相关
- **多层校验** → [SECURITY.md](SECURITY.md)
- **Pydantic 验证** → [SECURITY.md](SECURITY.md) + test_validation.py
- **不信任模型输出** → [SECURITY.md](SECURITY.md) + [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md)

### 准确率相关
- **测试结果** → [README.md](README.md) + [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **失败模式** → [FAILURES.md](FAILURES.md)
- **修正策略** → [FAILURES.md](FAILURES.md)
- **Policy 规则** → [POLICY.md](POLICY.md)

### 生产部署相关
- **PagerDuty** → [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 2
- **重试策略** → [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 3
- **规则兜底** → [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md) - 问题 1

### 使用相关
- **快速开始** → [README.md](README.md)
- **配置 API** → [TUTORIAL.md](TUTORIAL.md)
- **交互式工具** → quick_start.py
- **日志搜索** → [LOG_SEARCH.md](LOG_SEARCH.md) ⭐

---

## 📝 文档更新日志

| 日期 | 文档 | 更新内容 |
|------|------|----------|
| 2026-08-18 | DOCS_INDEX.md | 新增 POLICY.md 和 LOG_SEARCH.md 文档索引 |
| 2026-08-18 | LOG_SEARCH.md | 新增日志搜索工具完整文档 |
| 2026-08-18 | README.md | 更新版本到 v1.1，新增日志搜索相关内容 |
| 2026-08-17 | 所有文档 | 初始版本完成 |

---

## 💡 建议

1. **新用户**：按照"路径 1"阅读，30 分钟快速上手
2. **开发者**：重点阅读 ARCHITECTURE.md、SECURITY.md、FAILURES.md
3. **准备上线**：**必读** PRODUCTION_DECISIONS.md，这是生产环境的关键决策指南
4. **遇到问题**：在本文档中查找对应场景，直接跳转到相关章节

---

## 🎓 核心理念（贯穿所有文档）

> **绝不直接信任模型输出，永远校验、修正、记录。**

这个理念体现在：
- **SECURITY.md** → 三层防护机制
- **FAILURES.md** → 失败模式和修正策略
- **PRODUCTION_DECISIONS.md** → 规则兜底和降级策略

---

## 📞 需要帮助？

1. **使用问题** → 查看 [TUTORIAL.md](TUTORIAL.md) 常见问题章节
2. **设计问题** → 查看 [ARCHITECTURE.md](ARCHITECTURE.md)
3. **安全问题** → 查看 [SECURITY.md](SECURITY.md)
4. **生产问题** → 查看 [PRODUCTION_DECISIONS.md](PRODUCTION_DECISIONS.md)

---

**提示**：所有文档都使用 Markdown 格式，可以在任何文本编辑器或 GitHub 中查看。
