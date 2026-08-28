# CI 测试策略 - 最终方案

## 分析结果

检查了所有测试文件，需要 API 的文件只有：
- `test_e2e_integration.py` ✅ 已符合命名规则
- `test_e2e_robust.py` ✅ 已符合命名规则  
- `test_agent.py` ✅ 已符合命名规则
- `test_agent_v2.py` ✅ 已符合命名规则

**无需重命名任何文件！**

## 最终 CI 配置

### 策略
使用命名约定 + 通配符排除，自动适应未来新增的测试。

### CI 配置修改

**文件**: `.github/workflows/ci.yml`

**修改前**（硬编码文件列表）:
```yaml
- name: 运行单元测试
  run: |
    pytest tests/test_policy.py tests/test_trace_manager.py tests/test_robust_executor.py tests/test_models.py -v
  continue-on-error: false
```

**修改后**（使用通配符）:
```yaml
- name: 运行单元测试
  run: |
    pytest tests/ --ignore-glob='tests/test_e2e_*.py' --ignore-glob='tests/test_agent*.py' -v
  continue-on-error: false
```

## 优势

### 1. 自动适应
新增任何单元测试文件（如 `test_cache.py`, `test_utils.py`），**无需修改 CI**。

### 2. 清晰分类
- `test_e2e_*.py` - 端到端测试
- `test_agent*.py` - Agent 相关测试
- 其他 `test_*.py` - 单元测试

### 3. 本地运行灵活
```bash
# 只运行单元测试（和 CI 一样）
pytest tests/ --ignore-glob='tests/test_e2e_*.py' --ignore-glob='tests/test_agent*.py' -v

# 运行所有测试（包括 E2E）
pytest tests/ -v

# 只运行 E2E 测试
pytest tests/test_e2e_*.py tests/test_agent*.py -v
```

## 同时应用的两个修改

### 修改 1: 简化 Python 版本（第 10-26 行）

删除 matrix，固定使用 Python 3.12:

```yaml
jobs:
  test:
    name: 测试与代码质量检查
    runs-on: ubuntu-latest

    steps:
    - name: 检出代码
      uses: actions/checkout@v4

    - name: 设置 Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'
```

### 修改 2: 使用通配符排除测试（测试命令行）

```yaml
- name: 运行单元测试
  run: |
    pytest tests/ --ignore-glob='tests/test_e2e_*.py' --ignore-glob='tests/test_agent*.py' -v
  continue-on-error: false
```

## 通过网页修改步骤

1. 打开: https://github.com/guozhenling/wo-x/blob/main/.github/workflows/ci.yml

2. 点击 ✏️ (Edit)

3. **删除第 14-16 行** (strategy/matrix):
   ```yaml
   # 删除这3行
   strategy:
     matrix:
       python-version: ['3.10', '3.11', '3.12']
   ```

4. **修改第 22 行**:
   ```yaml
   # 改前: - name: 设置 Python ${{ matrix.python-version }}
   # 改后:
   - name: 设置 Python 3.12
   ```

5. **修改第 25 行**:
   ```yaml
   # 改前: python-version: ${{ matrix.python-version }}
   # 改后:
   python-version: '3.12'
   ```

6. **找到"运行单元测试"部分，修改为**:
   ```yaml
   - name: 运行单元测试
     run: |
       pytest tests/ --ignore-glob='tests/test_e2e_*.py' --ignore-glob='tests/test_agent*.py' -v
     continue-on-error: false
   ```

7. 提交信息:
   ```
   fix: 优化 CI 配置 - 单一 Python 版本 + 通配符排除测试
   
   - 使用 Python 3.12（移除 matrix）
   - 使用通配符自动排除 E2E 和 Agent 测试
   - 新增单元测试无需修改 CI 配置
   - 节省 66% CI 时间
   ```

## 预期结果

### 当前运行的测试（34个）
```
tests/test_policy.py - 1 个测试
tests/test_trace_manager.py - 12 个测试
tests/test_robust_executor.py - 11 个测试
tests/test_models.py - 10 个测试
+ 其他未来新增的单元测试（自动包含）
```

### 自动排除的测试
```
tests/test_e2e_integration.py
tests/test_e2e_robust.py
tests/test_agent.py
tests/test_agent_v2.py
```

### CI 运行结果
```
✅ Python 3.12 - 测试与代码质量检查
  ✓ 代码格式检查
  ✓ 代码规范检查
  ✓ 单元测试 (34+ passed)
  ✓ 安全扫描
  
总耗时: ~10秒
```

## 验证

修改完成后，本地验证命令:
```bash
pytest tests/ --ignore-glob='tests/test_e2e_*.py' --ignore-glob='tests/test_agent*.py' -v
```

应该看到 34 个测试全部通过。

---

**生成时间**: 2026-08-28  
**优势**: 无需重命名文件，CI 自动适应新测试
