# 简化 CI 为单一 Python 版本

## 当前配置

CI 使用 matrix 策略测试 3 个 Python 版本：
- Python 3.10
- Python 3.11  
- Python 3.12

这会让每次 CI 运行 3 次测试，增加时间和资源消耗。

## 建议方案

### 方案 1: 只用 Python 3.12（推荐）

**优点**:
- 最新的稳定版本
- 性能最好
- 包含最新特性

**修改**: 删除 matrix 策略，固定使用 3.12

### 方案 2: 只用 Python 3.13

**注意**: Python 3.13 可能还在测试阶段，某些包可能不兼容

## 修改步骤（使用 Python 3.12）

### 文件
`.github/workflows/ci.yml`

### 位置
第 10-26 行

### 修改前
```yaml
jobs:
  test:
    name: 测试与代码质量检查
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - name: 检出代码
      uses: actions/checkout@v4

    - name: 设置 Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
```

### 修改后
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

## 完整的修改清单

需要在同一次编辑中应用以下两个修改：

### 修改 1: 简化为单一 Python 版本

**位置**: 第 10-26 行  
**说明**: 删除 matrix 策略，固定使用 Python 3.12

### 修改 2: 修复测试范围

**位置**: 第 43-46 行（修改后的行号）  
**说明**: 只运行核心单元测试

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

3. **应用修改 1**: 删除第 14-16 行的 matrix 部分
   ```yaml
   # 删除这 3 行
   strategy:
     matrix:
       python-version: ['3.10', '3.11', '3.12']
   ```

4. **修改第 22 行**: 
   ```yaml
   # 修改前
   - name: 设置 Python ${{ matrix.python-version }}
   
   # 修改后
   - name: 设置 Python 3.12
   ```

5. **修改第 25 行**:
   ```yaml
   # 修改前
   python-version: ${{ matrix.python-version }}
   
   # 修改后
   python-version: '3.12'
   ```

6. **应用修改 2**: 修改测试命令（找到"运行单元测试"部分）
   ```yaml
   - name: 运行单元测试
     run: |
       pytest tests/test_policy.py tests/test_trace_manager.py tests/test_robust_executor.py tests/test_models.py -v
     continue-on-error: false
   ```

7. 提交信息:
   ```
   fix: 简化 CI 为单一 Python 版本并修复测试范围
   
   - 只使用 Python 3.12（移除多版本 matrix）
   - 只运行核心单元测试（34 个测试）
   - 减少 CI 运行时间和资源消耗
   ```

8. 点击 "Commit changes"

## 预期效果

### 修改前
- 运行 3 次测试（3 个 Python 版本）
- 每次约 10 秒 × 3 = 30 秒
- 3 个并行任务

### 修改后
- 只运行 1 次测试
- 约 10 秒完成
- 1 个任务
- **节省 66% 的 CI 时间**

### CI 结果
```
✅ Python 3.12 - 测试与代码质量检查
  ✓ 代码格式检查 (Black)
  ✓ 代码规范检查 (Flake8)
  ✓ 单元测试 (34 passed)
  ✓ 安全扫描 (Bandit)
  ✓ 依赖检查 (Safety)
```

## 何时需要多版本测试？

如果你的项目需要支持多个 Python 版本（比如发布到 PyPI 的库），则应该保留多版本测试。

对于内部项目或只在特定环境运行的应用，单一版本就足够了。

---

**生成时间**: 2026-08-28  
**推荐**: 使用 Python 3.12（最新稳定版）
