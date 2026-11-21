# GodKey Skill

简体中文 | [English](README_EN.md)

> 跨 Harness 通用结构化编程方法论 —— 专治 AI 靠猜、钻局部补丁、文档与代码脱节。

---

## 这是什么

GodKey Skill 是一套**宿主无关**的 Agent 工程方法论与确定性文档门禁体系，适用于 Claude Code、Antigravity、Codex、Cursor、OpenCode 等任意支持 Skill / 指令加载的研发 Harness。

本仓库提供**完全独立、1:1 对等的双语版本**，各自包含完整的 `SKILL.md`、子流程、模板、确定性校验脚本、Hook 与行为验证集：

- **中文版（推荐优先）**：[`zh/`](zh/SKILL.md) — 中文流程、中文文档体系（`01-产品介绍` ~ `09-迭代变更`）与中文门禁输出
- **English Edition**：[`en/`](en/SKILL.md) — 原生英文流程、英文文档体系（`01-product` ~ `09-changes`）与英文门禁输出

它替换 AI 的默认行为模式：

```text
默认 AI：扫几行代码 → 凭训练记忆写补丁 → 改完不更文档 → 结束
加载后： 脚本审计定模式 → 蓝图与规范对齐 → 只读源码摸底 → 方案定层落盘
         → 精准施工清废 → 自检审查测试 → 同步静态真相 + 门禁脚本 PASS
```

---

## 核心设计

### 1. 动静双层文档架构（按功能驱动，目录即状态）
- **静态真相层**：只存系统当前生效的快照（产品、架构、功能蓝图、**最新数据库表结构快照**、规范、部署），拒绝僵尸文档。
- **动态迭代层**：按**功能/需求**建一体化工作包（方案、跨会话进展、测试、审查、`ops/` 伴生迁移 SQL 与一次性脚本），完整沉淀每次功能迭代上下文。
- **四态文件夹状态机**：`01-待确认/` → `02-进行中/` → `03-已搁置/` → `99-已归档/`，目录位置本身即状态，不在正文维护状态字段。

### 2. 四种运行模式（加待初始化态 `uninitialized`，全场景覆盖）
| 模式 | 适用对象 | 文档形态（中文版 `zh/`） |
|---|---|---|
| **`full`** | 中大型 / 多模块正式项目 | `01~08` 静态目录 + `09-迭代变更/`（4 态） |
| **`lite`** | 小型长期维护单体项目 / 工具 | `01~03` 精简静态文件 + `04-迭代变更/`（4 态） |
| **`external`** | 外部开源 / 已有老项目 | 不塞新目录，读既有文档，全量执行防幻觉纪律 |
| **`demo`** | 一次性 Demo / 验证脚本 | 豁免文档体系 |

### 3. 确定性门禁脚本 + 跨 Harness Hook
- 内置纯 Python 3.8+ 标准库工具 `scripts/godkey_gate.py`（零外部依赖，跨 Windows / Linux / macOS）：
  - `init`：一键初始化 `full` 或 `lite` 模板；
  - `audit`：机器输出静态文档健康度与 4 态变更包清单；
  - `new` / `move` / `hotfix`：规范建包（支持 `--type feature|review`）、状态流转、小修台账；
  - `check-sync`：机械核对 `git diff` 与功能包 `ops/`（支持 `archive` / `commit` / `strict` / `hotfix` 模式），代码/SQL/配置改了但静态真相文档未更新直接报 `FAIL`；
  - `archive`：先过产物完整性 + 静态同步门禁，全部 `PASS` 才迁入 `99-已归档/`；
  - `install-hook`：一键安装跨所有 Harness 通用的 Git `pre-commit` 钩子（兼容 worktree 与多模块 `--doc-root`）。

### 4. 双层渐进披露 + 行为验证集
- `SKILL.md`（判定层）只定义关卡标准与阻塞铁律；执行细节、模板与决策表全部下沉到 `references/`，从机制上要求 AI 先读子流程再开工。
- `evals/` 提供 8 个端到端行为验证场景，验证 AI 触发、下沉、外部项目降级、跨会话接力、阻塞铁律与门禁拦截。

---

## 仓库结构

```text
godkey-skill/
├── README.md                     # 中文主说明（本文件）
├── README_EN.md                  # English README
├── zh/                           # 中文版独立完整 Skill（可直接安装此目录）
│   ├── SKILL.md                  # 判定层：前置审计 + 四种运行模式 + 6 关判定标准 + 阻塞铁律
│   ├── references/               # 开发流程 / 代码审查 / 测试流程 / 文档与变更体系
│   ├── scripts/                  # godkey_gate.py + 7 组真实 Git 集成回归测试
│   ├── hooks/                    # Git pre-commit 与多 Harness Hook 接入指南
│   ├── evals/                    # 8 场景行为验证集
│   └── assets/templates/         # full / lite / change-package 模板
└── en/                           # English self-contained Skill（1:1 完整英文对等版）
    ├── SKILL.md
    ├── references/
    ├── scripts/
    ├── hooks/
    ├── evals/
    └── assets/templates/
```

---

## 安装与使用

### 1. 安装对应语言版本到 Harness 的 Skills 目录

由于 `zh/` 与 `en/` 各自是完整的自包含 Skill 目录，按需选择其中一个目录链接或复制到你的 Harness skills 路径：

```bash
# 先克隆仓库到本地
git clone https://github.com/godkey1314/godkey-skill.git ~/godkey-skill

# 安装中文版（以 Claude Code 为例，其他 Harness 替换为对应 skills 目录）
ln -s ~/godkey-skill/zh ~/.claude/skills/godkey-skill

# 或安装英文版
ln -s ~/godkey-skill/en ~/.claude/skills/godkey-skill
```

Windows PowerShell（复制或建目录联接）：

```powershell
git clone https://github.com/godkey1314/godkey-skill.git D:\tools\godkey-skill
Copy-Item -Recurse D:\tools\godkey-skill\zh "$HOME\.claude\skills\godkey-skill"
```

### 2. 常用门禁脚手架命令（以中文版 `zh/` 为例）

```bash
# 审计当前项目文档状态与进行中功能包
python zh/scripts/godkey_gate.py audit --project-root <项目路径>

# 初始化新项目文档体系（二选一：full 或 lite）
python zh/scripts/godkey_gate.py init --profile lite --project-root <项目路径>

# 新建功能包 / 流转搁置 / 门禁归档
python zh/scripts/godkey_gate.py new 用户导出Excel --state active --project-root <项目路径>
python zh/scripts/godkey_gate.py move 用户导出Excel paused --reason "先切去做支付修复" --project-root <项目路径>
python zh/scripts/godkey_gate.py archive 用户导出Excel --project-root <项目路径>

# 安装跨 Harness Git pre-commit 钩子
python zh/scripts/godkey_gate.py install-hook --project-root <项目路径>
```

### 3. 运行脚本自测

```bash
# 中文版测试套件
python -m unittest discover -s zh/scripts -p "test_*.py" -v

# 英文版测试套件
python -m unittest discover -s en/scripts -p "test_*.py" -v
```

---

## License

MIT
