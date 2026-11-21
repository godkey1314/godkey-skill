# 跨 Harness Hook 与硬门禁接入指南

纯 Prompt 约束无法根治模型在长上下文末期“忘记更新静态真相文档”的问题。
GodKey Skill 把核心校验逻辑全部沉淀在平台无关的 `scripts/godkey_gate.py`（纯 Python 标准库，零外部依赖）中，提供两层接入方式：

---

## 一、推荐默认：Git `pre-commit` Hook（所有 Harness 通用）

无论使用 Antigravity、Claude Code、Codex、Cursor 还是人工提交，只要走 Git 就会触发同一份校验脚本（支持常规仓库、Git Worktree 与 Submodule，并自动探测可用 Python 3 解释器以避开 Windows Store 空壳 `python3`）。

```bash
# 在目标项目根目录一键安装（默认 mode=commit：WIP 提交检查进展记录，不阻断中间提交）
python <godkey-skill路径>/scripts/godkey_gate.py install-hook --project-root .

# 多模块仓库可显式绑定对应文档目录
python <godkey-skill路径>/scripts/godkey_gate.py install-hook --project-root . --doc-root backend_doc

# 若团队要求每次提交都必须同步更新静态真相文档，可改为 strict 模式
python <godkey-skill路径>/scripts/godkey_gate.py install-hook --project-root . --mode strict --force
```

如跨机器协作导致 `godkey-skill` 安装路径不同，可在环境变量中设置 `GODKEY_GATE_SCRIPT` 指向本机的 `godkey_gate.py`。

---

## 二、可选增强：Harness 原生 Hook

如果宿主支持会话结束钩子（例如 Claude Code 的 `Stop` Hook），可直接调用同一个 `godkey_gate.py`，防止 AI 在“不提交 Git、直接改完文件就收工”的场景下跳过进度/文档更新：

- **Linux / macOS（POSIX sh）**：参考 [claude-code-settings.example.json](claude-code-settings.example.json)（注意双引号内必须用 `$HOME` 而非 `~`；Claude Code `Stop` Hook 需返回退出码 **`2`** 才会真正阻断停止并把 stderr 回传给模型修复）。
- **Windows（PowerShell）**：将 `command` 替换为：
  ```text
  pwsh -NoProfile -Command "$s = if ($env:GODKEY_GATE_SCRIPT) { $env:GODKEY_GATE_SCRIPT } else { Join-Path $HOME '.claude\skills\godkey-skill\scripts\godkey_gate.py' }; if (Test-Path $s) { python $s check-sync --mode commit --project-root .; if ($LASTEXITCODE -ne 0) { exit 2 } }"
  ```
- **触发边界提示**：`Stop` Hook 会在每次会话结束时检查当前工作区；如果工作区本就残留了未处理的临时代码改动而你在跑纯问答会话，建议先暂存/清理工作区或只用 Git `pre-commit` Hook。
- **其他 Harness（Antigravity / Codex / OpenCode / Cursor）**：直接依赖 Skill 的**关卡 5 铁律**——任务宣称完成前，必须实际运行 `godkey_gate.py check-sync` 或 `godkey_gate.py archive` 并将 `PASS` 输出贴给用户。
