# GodKey Skill

> 跨 Harness 通用结构化编程方法论 —— 专治 AI 靠猜、钻局部补丁、文档与代码脱节。

---

## 这是什么

GodKey Skill 是一套**宿主无关**的 Agent 工程方法论与确定性文档门禁体系，适用于 Claude Code、Antigravity、Codex、Cursor、OpenCode 等任意支持 Skill / 指令加载的研发 Harness。

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
| 模式 | 适用对象 | 文档形态 |
|---|---|---|
| **`full`** | 中大型 / 多模块正式项目 | `01~08` 静态目录 + `09-迭代变更/`（4 态） |
| **`lite`** | 小型长期维护单体项目 / 工具 | `01~03` 精简静态文件 + `04-迭代变更/`（4 态） |
| **`external`** | 外部开源 / 已有老项目 | 不塞新目录，读既有文档，全量执行防幻觉纪律 |
| **`demo`** | 一次性 Demo / 验证脚本 | 豁免文档体系 |

### 3. 确定性门禁脚本 + 跨 Harness Hook
- 内置纯 Python 标准库工具 `scripts/godkey_gate.py`（零外部依赖，跨 Windows / Linux / macOS）：
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

## 目录结构

```text
godkey-skill/
├── SKILL.md                      # 判定层：前置审计 + 四种运行模式 + 6 关判定标准 + 阻塞铁律
├── references/
│   ├── 开发流程.md                # 6 Pass 开发链路（先蓝图 → 再只读摸底 → 再落盘方案 → 施工归档）
│   ├── 代码审查.md                # 5 Pass 原则驱动审查（5 维度 + 模式扩散 + 报告落盘）
│   ├── 测试流程.md                # 6 Pass 测试链路（真实链路优先 + 受限环境显式降级）
│   └── 文档与变更体系.md           # 动静双层架构、四种运行模式、4 态工作包、ops/ 与脚本门禁详解
├── scripts/
│   ├── godkey_gate.py            # 确定性 CLI：init / audit / new / move / hotfix / check-sync / archive / install-hook
│   └── test_godkey_gate.py       # 真实 Git 仓库集成测试套件
├── hooks/
│   ├── README.md                 # Git pre-commit 与多 Harness Hook 接入指南
│   └── claude-code-settings.example.json
├── evals/                        # 8 场景行为验证集
└── assets/
    └── templates/
        ├── full/                 # 完整版文档骨架（01~08 + 09-迭代变更/）
        ├── lite/                 # 简化版文档骨架（01~03 + 04-迭代变更/）
        └── change-package/       # 功能包内部模板（01-方案/02-进展/03-测试/04-审查/ops）
```

---

## 安装与使用

### 1. 克隆到对应 Harness 的 Skills 目录

```bash
# 通用克隆（按你使用的 Harness 放进对应 skills / plugins 目录）
git clone https://github.com/godkey1314/godkey-skill.git <你的skills目录>/godkey-skill

# 例如 Claude Code：
git clone https://github.com/godkey1314/godkey-skill.git ~/.claude/skills/godkey-skill
```

### 2. 常用门禁脚手架命令

```bash
# 审计当前项目文档状态与进行中功能包
python scripts/godkey_gate.py audit --project-root <项目路径>

# 初始化新项目文档体系（二选一：full 或 lite）
python scripts/godkey_gate.py init --profile lite --project-root <项目路径>

# 新建功能包 / 流转搁置 / 门禁归档
python scripts/godkey_gate.py new 用户导出Excel --state active --project-root <项目路径>
python scripts/godkey_gate.py move 用户导出Excel paused --reason "先切去做支付修复" --project-root <项目路径>
python scripts/godkey_gate.py archive 用户导出Excel --project-root <项目路径>

# 安装跨 Harness Git pre-commit 钩子
python scripts/godkey_gate.py install-hook --project-root <项目路径>
```

### 3. 运行脚本自测

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
```

---

## License

MIT
