# GitHub 仓库设置指南

## ✅ 当前状态

- **仓库地址**: https://github.com/guozhenling/wo-x
- **代码推送**: ✅ 已完成（除 CI/CD 配置外）
- **CI/CD 配置**: ⏳ 需要手动添加（权限限制）

---

## 🚨 问题说明

GitHub CLI 的 OAuth token 缺少 `workflow` 权限，导致无法通过命令行推送 `.github/workflows/` 文件。

**错误信息**:
```
! [remote rejected] main -> main (refusing to allow an OAuth App to create 
or update workflow `.github/workflows/ci.yml` without `workflow` scope)
```

---

## 📋 解决方案：通过网页添加 CI/CD（推荐）

### 步骤 1: 添加 CI 配置文件

1. 打开仓库：https://github.com/guozhenling/wo-x

2. 点击 **"Add file"** → **"Create new file"**

3. 文件名输入：`.github/workflows/ci.yml`

4. 复制本地文件内容：
   ```bash
   # 在本地运行，复制输出内容
   cat .github/workflows/ci.yml
   ```

5. 粘贴到网页编辑器

6. 填写提交信息：
   - Commit message: `ci: 添加 GitHub Actions CI 配置`
   - Description: `多版本测试、代码检查、安全扫描`

7. 点击 **"Commit new file"**

### 步骤 2: 添加 PR 模板

1. 继续点击 **"Add file"** → **"Create new file"**

2. 文件名输入：`.github/pull_request_template.md`

3. 复制本地文件内容：
   ```bash
   cat .github/pull_request_template.md
   ```

4. 粘贴并提交

### 步骤 3: 配置 Secrets（可选）

如果需要在 CI 中运行集成测试，需要配置 API 密钥：

1. 进入 **Settings** → **Secrets and variables** → **Actions**

2. 点击 **"New repository secret"**

3. 添加以下 secrets：
   - `OPENAI_API_KEY`: 你的 OpenAI API 密钥
   - `OPENAI_BASE_URL`: API 基础地址
   - `OPENAI_MODEL`: 使用的模型名称

### 步骤 4: 查看 CI 运行

1. 进入 **Actions** 标签页

2. 看到 CI Pipeline 自动运行

3. 点击查看详细日志

---

## 🔧 替代方案：重新授权 GitHub CLI

如果你想通过命令行推送，需要重新授权：

### 方法 1: 交互式登录

```bash
# 1. 退出当前登录
gh auth logout

# 2. 重新登录（选择浏览器登录）
gh auth login

# 按提示选择：
# - GitHub.com
# - HTTPS
# - Login with a web browser
# - 输入 one-time code
# - 在浏览器中完成授权（确保勾选 workflow 权限）

# 3. 验证权限
gh auth status

# 4. 推送代码
git push
```

### 方法 2: 使用 Personal Access Token (PAT)

1. 进入 GitHub **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**

2. 点击 **"Generate new token"** → **"Generate new token (classic)"**

3. 勾选权限：
   - ✅ `repo` (完整仓库权限)
   - ✅ `workflow` (工作流权限)

4. 生成后复制 token

5. 配置本地：
   ```bash
   # 更新远程 URL（使用 token）
   git remote set-url origin https://YOUR_TOKEN@github.com/guozhenling/wo-x.git
   
   # 推送
   git push
   ```

---

## 📦 当前本地状态

```bash
# 查看本地提交
git log --oneline -3

# 最新提交包含 CI 配置，但未推送到远程
# 可以通过网页添加，或重新授权后推送
```

---

## ✅ 验证清单

完成以下步骤后，项目完全就绪：

- [x] 核心代码已推送
- [x] 测试代码已推送
- [x] 文档已推送
- [x] Docker 配置已推送
- [ ] CI/CD 配置已添加（通过网页或重新授权）
- [ ] CI 首次运行成功
- [ ] 配置了必要的 Secrets（可选）

---

## 🚀 下一步

1. **立即**: 通过网页添加 CI/CD 配置（3 分钟）

2. **本周**:
   - 创建 README.md 说明文档
   - 添加 LICENSE 文件
   - 创建第一个 Issue/PR 测试流程

3. **本月**:
   - 设置分支保护规则
   - 配置代码审查流程
   - 添加更多测试用例

---

## 📞 需要帮助？

- GitHub Actions 文档: https://docs.github.com/actions
- GitHub CLI 文档: https://cli.github.com/manual/
- 项目文档: `docs/CI_CD_QUICKSTART.md`

---

**最后更新**: 2026-08-27
