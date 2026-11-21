# Cross-Harness Hooks & Deterministic Gate Setup

Pure prompt rules cannot reliably stop models from forgetting static documentation updates at the end of a long context window.
GodKey Skill moves all enforcement into the harness-agnostic `scripts/godkey_gate.py` CLI (zero external dependencies, pure Python 3.8+ standard library) with two layers of enforcement:

---

## 1. Recommended Default: Git `pre-commit` Hook (Works Across Every Harness)

Works identically across Antigravity, Claude Code, Codex, Cursor, OpenCode, and human commits (supports standard repos, Git worktrees, submodules, and probes for a working Python 3 interpreter to avoid Windows Store empty `python3` stubs).

```bash
# Install in target repo (default mode=commit: verifies progress/doc log without blocking WIP commits)
python <godkey-skill-path>/scripts/godkey_gate.py install-hook --project-root .

# Bind to a specific docs root in multi-module repos
python <godkey-skill-path>/scripts/godkey_gate.py install-hook --project-root . --doc-root backend_doc

# Enforce full static doc sync on every commit
python <godkey-skill-path>/scripts/godkey_gate.py install-hook --project-root . --mode strict --force
```

When collaborating across machines with different install paths, set `GODKEY_GATE_SCRIPT` in your environment to point to your local `godkey_gate.py`.

---

## 2. Optional Enhancement: Harness-Native Hooks

If your harness supports session-stop hooks (such as Claude Code's `Stop` hook), invoke the same `godkey_gate.py` to catch agents that edit files without committing:

- **Linux / macOS (POSIX sh)**: See [claude-code-settings.example.json](claude-code-settings.example.json) (uses `$HOME` instead of unexpanded `~` inside quotes, and returns exit code **`2`** so Claude Code blocks stopping and feeds stderr back to the model).
- **Windows (PowerShell)**: Replace `command` with:
  ```text
  pwsh -NoProfile -Command "$s = if ($env:GODKEY_GATE_SCRIPT) { $env:GODKEY_GATE_SCRIPT } else { Join-Path $HOME '.claude\skills\godkey-skill\scripts\godkey_gate.py' }; if (Test-Path $s) { python $s check-sync --mode commit --project-root .; if ($LASTEXITCODE -ne 0) { exit 2 } }"
  ```
- **Scope note**: A `Stop` hook inspects the working tree at the end of every session; if you leave dirty uncommitted code around while running pure Q&A chats, prefer the Git `pre-commit` hook.
- **Other harnesses (Antigravity / Codex / OpenCode / Cursor)**: Rely directly on Gate 5 — the agent must run `godkey_gate.py check-sync` or `godkey_gate.py archive` and show the actual `PASS` output before claiming completion.
