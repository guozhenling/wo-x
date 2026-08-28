# CI 测试范围修复说明

## 问题

CI 尝试运行所有测试时，遇到以下文件导入失败：
- `test_e2e_integration.py` - 需要 API 配置
- `test_e2e_robust.py` - 需要 API 配置
- `test_agent.py` - 需要 anthropic 包和 API
- `test_agent_v2.py` - 需要 anthropic 包和 API
- `test_classifier.py` - 需要 API 配置

这些都是端到端测试或需要外部 API 的测试，不应该在 CI 的单元测试阶段运行。

## 解决方案

**只运行不依赖外部 API 的核心单元测试**：
- `test_policy.py` - Policy 引擎测试 (1 个)
- `test_trace_manager.py` - 轨迹管理测试 (12 个)
- `test_robust_executor.py` - 健壮执行器测试 (11 个)
- `test_models.py` - 数据模型测试 (10 个)

**总计**: 34 个核心单元测试

## 需要的 CI 配置更改

### 文件
`.github/workflows/ci.yml`

### 位置
第 43-46 行

### 修改前
```yaml
- name: 运行单元测试
  run: |
    pytest tests/ --ignore-glob='tests/test_e2e*.py' -v
  continue-on-error: false
```

### 修改后
```yaml
- name: 运行单元测试
  run: |
    pytest tests/test_policy.py tests/test_trace_manager.py tests/test_robust_executor.py tests/test_models.py -v
  continue-on-error: false
```

## 通过网页修改步骤

1. 打开文件:  
   https://github.com/guozhenling/wo-x/blob/main/.github/workflows/ci.yml

2. 点击右上角的 ✏️ (Edit this file)

3. 找到第 43-46 行，替换为上述"修改后"的内容

4. 提交信息:
   ```
   fix: CI 只运行核心单元测试（不依赖 API）
   
   - 明确列出要测试的文件
   - 排除需要 API 配置的 E2E 测试
   - 总计 34 个核心单元测试
   ```

5. 点击 "Commit changes"

## 预期结果

CI 运行后应该显示：
```
✅ test_policy.py - 1 passed
✅ test_trace_manager.py - 12 passed  
✅ test_robust_executor.py - 11 passed
✅ test_models.py - 10 passed
────────────────────────────────────
✅ 34 passed in ~10s
```

## 测试分类

### 核心单元测试（在 CI 中运行）
- ✅ `test_policy.py` - Policy 引擎
- ✅ `test_trace_manager.py` - 轨迹管理
- ✅ `test_robust_executor.py` - 健壮执行器
- ✅ `test_models.py` - 数据模型

### E2E/集成测试（需要本地运行）
- ⏸️ `test_e2e_integration.py` - 端到端集成
- ⏸️ `test_e2e_robust.py` - 健壮性集成
- ⏸️ `test_agent.py` - Agent 工具循环
- ⏸️ `test_agent_v2.py` - Agent V2
- ⏸️ `test_classifier.py` - 分类器

### 本地运行完整测试

```bash
# 需要先配置 .env
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 只运行单元测试（不需要 API）
pytest tests/test_policy.py tests/test_trace_manager.py tests/test_robust_executor.py tests/test_models.py -v

# 运行所有测试（需要 API）
pytest tests/ -v
```

## 验证

修改后运行 CI，应该看到：
- ✅ 34 个测试全部通过
- ⚡ 运行时间约 10 秒
- 🚫 没有导入错误
- ✅ 所有检查通过

---

**生成时间**: 2026-08-28  
**状态**: 待通过网页应用
