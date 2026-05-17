# Git使用规范

> **Git分支管理和提交规范**

---

## 🌳 分支管理

### 分支类型

#### 主分支
- `main` / `master`：生产环境分支，只能合并，不能直接提交
- `develop`：开发分支，日常开发基于此分支

#### 功能分支
- `feature/功能名称`：新功能开发
- 示例：`feature/user-login`、`feature/order-system`

#### 修复分支
- `fix/bug名称`：bug修复
- 示例：`fix/login-error`、`fix/payment-bug`

#### 发布分支
- `release/版本号`：发布准备
- 示例：`release/v1.0.0`

#### 热修复分支
- `hotfix/问题名称`：生产环境紧急修复
- 示例：`hotfix/critical-bug`

---

## 🔄 工作流程

### 日常开发流程
```bash
# 1. 从develop创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/user-login

# 2. 开发功能
# ... 编写代码 ...

# 3. 提交代码
git add .
git commit -m "feat(user): 实现用户登录功能"

# 4. 推送到远程
git push origin feature/user-login

# 5. 创建PR/MR，合并到develop
# ... 在Git平台操作 ...

# 6. 删除功能分支
git branch -d feature/user-login
```

### 发布流程
```bash
# 1. 从develop创建release分支
git checkout develop
git checkout -b release/v1.0.0

# 2. 进行版本号更新等操作
# ... 修改版本号 ...

# 3. 合并到main
git checkout main
git merge release/v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# 4. 合并回develop
git checkout develop
git merge release/v1.0.0
git push origin develop

# 5. 删除release分支
git branch -d release/v1.0.0
```

---

## 📝 Commit Message规范

### 格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型
| Type | 说明 | 示例 |
|------|------|------|
| feat | 新功能 | feat(user): 添加登录功能 |
| fix | 修复bug | fix(order): 修复订单计算错误 |
| docs | 文档更新 | docs: 更新API文档 |
| style | 代码格式 | style: 格式化代码 |
| refactor | 重构 | refactor(user): 重构用户服务 |
| test | 测试 | test: 添加单元测试 |
| chore | 构建/工具 | chore: 更新依赖包 |
| perf | 性能优化 | perf: 优化查询性能 |

### Scope（可选）
模块名称：user、order、payment等

### Subject
- 简短描述（不超过50字符）
- 动词开头，使用第一人称现在时
- 首字母小写
- 结尾不加句号

### Body（可选）
- 详细描述变更内容
- 说明变更原因

### Footer（可选）
- 关闭Issue：`Closes #123`
- 破坏性变更：`BREAKING CHANGE: xxx`

### 示例
```bash
# 简单提交
git commit -m "feat(user): 实现用户登录"

# 详细提交
git commit -m "feat(user): 实现用户登录功能

- 添加登录接口
- 实现JWT认证
- 添加登录日志

Closes #123"
```

---

## 🚫 禁止操作

### 1. 禁止直接在main/master上提交
```bash
# ❌ 不要这样
git checkout main
git commit -m "fix something"

# ✅ 应该这样
git checkout -b hotfix/something
# ... 修复后创建PR合并 ...
```

### 2. 禁止强制推送到主分支
```bash
# ❌ 绝对禁止
git push -f origin main

# ✅ 只在自己的功能分支使用
git push -f origin feature/my-feature
```

### 3. 禁止提交敏感信息
```bash
# ❌ 不要提交这些
.env         # 环境变量文件
config.json  # 包含密码的配置
*.key        # 密钥文件
```

---

## 📋 提交前检查清单

- [ ] 代码已测试通过
- [ ] 没有console.log/print调试代码
- [ ] 没有提交敏感信息
- [ ] Commit message符合规范
- [ ] 代码符合编码规范

---

## 🔧 常用命令

### 查看状态
```bash
git status              # 查看工作区状态
git log --oneline       # 查看提交历史
git branch -a           # 查看所有分支
```

### 撤销操作
```bash
git checkout -- file    # 撤销工作区修改
git reset HEAD file     # 撤销暂存区
git revert commit-id    # 撤销某次提交
```

### 分支操作
```bash
git branch feature-name          # 创建分支
git checkout feature-name        # 切换分支
git checkout -b feature-name     # 创建并切换
git branch -d feature-name       # 删除分支
```

### 合并操作
```bash
git merge branch-name            # 合并分支
git rebase branch-name           # 变基合并
```

---

## 🔗 .gitignore配置

### Python项目
```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.Python
*.egg-info/
venv/

# 环境变量
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
```

### Node.js项目
```gitignore
# Node.js
node_modules/
npm-debug.log*

# 环境变量
.env
.env.local

# 构建产物
dist/
build/
```

---

**文档版本**：v1.0  
**最后更新**：[日期]

