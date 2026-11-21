# GodKey Skill

[简体中文](README.md) | English

> A cross-harness structured engineering methodology — built to stop AI coding agents from guessing, patching blindly, and leaving documentation permanently out of date.

---

## What It Is

GodKey Skill is a **harness-agnostic** agent engineering methodology and deterministic documentation gate system. It works across Claude Code, Antigravity, Codex, Cursor, OpenCode, and any other agent harness that loads Skills or structured instructions.

This repository provides **two fully self-contained, 1:1 equivalent language editions**, each with its own `SKILL.md`, workflow references, templates, deterministic CLI gate, hooks, and evals:

- **Chinese Edition (Primary)**: [`zh/`](zh/SKILL.md) — Chinese workflows, directory layout (`01-产品介绍` ~ `09-迭代变更`), and CLI output
- **English Edition**: [`en/`](en/SKILL.md) — Native English workflows, directory layout (`01-product` ~ `09-changes`), and CLI output

It replaces an agent's default shortcut behavior:

```text
Default AI: Skim a few lines → patch from training memory → skip doc updates → done
With Skill: Script audit & mode detection → blueprint & standards alignment → read-only codebase recon
            → written plan & layering → disciplined edits & cleanup → self-check/review/tests
            → static truth sync + deterministic gate PASS
```

---

## Core Design

### 1. Dual-Layer Documentation Architecture (Feature-Driven, Folders as State)
- **Static Truth Layer**: Stores only the **current snapshot** of the system (product overview, architecture, feature blueprints, **latest database schema snapshot**, coding standards, deployment) — zero stale append-only graveyard docs.
- **Dynamic Change Layer**: Organizes work into **feature-centric change packages** (plan, cross-session progress, tests, code review, plus `ops/` for migration SQL, one-off backfill scripts, and release notes).
- **Four-State Folder State Machine**: `01-draft/` → `02-active/` → `03-paused/` → `99-archive/`. Directory location *is* the status — no more forgotten `Status: In Progress` lines inside Markdown files.

### 2. Four Operating Modes (Plus `uninitialized` Cold-Start Detection)
| Mode | Best For | Layout (English `en/`) |
|---|---|---|
| **`full`** | Mid-to-large or multi-module production projects | `01~08` static dirs + `09-changes/` (4 states) |
| **`lite`** | Small long-lived single-repo apps & tools | `01~03` compact static files + `04-changes/` (4 states) |
| **`external`** | Open-source or existing legacy repositories | Never injects foreign dirs; reads & syncs existing repo docs while keeping all anti-hallucination rules |
| **`demo`** | Throwaway prototypes / verification scripts | Exempt from documentation structure |

### 3. Deterministic Gate CLI + Cross-Harness Hooks
- Built-in zero-dependency Python 3.8+ CLI (`scripts/godkey_gate.py`, works on Windows / Linux / macOS):
  - `init`: Scaffolds `full` or `lite` documentation templates and `.godkey.json`;
  - `audit`: Mechanically audits static doc completeness and lists all 4-state change packages;
  - `new` / `move` / `hotfix`: Creates standard feature or standalone review packages (`--type feature|review`), transitions states, and logs single-file hotfixes;
  - `check-sync`: Inspects `git diff` and package `ops/` assets (`archive` / `commit` / `strict` / `hotfix` modes); fails loudly when code/SQL/ops changes lack corresponding static doc updates;
  - `archive`: Enforces artifact quality + static sync checks before moving a package into `99-archive/`;
  - `install-hook`: Installs a portable Git `pre-commit` hook (worktree/submodule safe, supports `--doc-root`).

### 4. Two-Layer Progressive Disclosure + Behavioral Evals
- `SKILL.md` (Judgment Layer) defines only gate pass/block criteria; concrete steps, templates, and decision tables live in `references/`, forcing agents to read the relevant workflow before acting.
- `evals/` provides 8 reproducible end-to-end scenarios verifying triggering, reference loading, external-repo fallback, cross-session resume, blocking discipline, and gate enforcement.

---

## Repository Structure

```text
godkey-skill/
├── README.md                     # Chinese README (primary)
├── README_EN.md                  # English README (this file)
├── zh/                           # Self-contained Chinese Skill
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   ├── hooks/
│   ├── evals/
│   └── assets/templates/
└── en/                           # Self-contained English Skill (install this directory)
    ├── SKILL.md                  # Judgment layer: audit + 4 modes + 6 gates + blocking rules
    ├── references/               # development-workflow / code-review / testing-workflow / docs-and-changes
    ├── scripts/                  # godkey_gate.py + 7 real-Git integration regression suites
    ├── hooks/                    # Git pre-commit & multi-harness hook guide
    ├── evals/                    # 8 behavioral verification scenarios
    └── assets/templates/         # full / lite / change-package templates
```

---

## Installation & Usage

### 1. Install Your Preferred Language Edition

Both `zh/` and `en/` are completely self-contained skill directories. Link or copy the one you want into your harness's skills directory:

```bash
# Clone the repository locally
git clone https://github.com/godkey1314/godkey-skill.git ~/godkey-skill

# Install the English edition (Claude Code example; adjust path for your harness)
ln -s ~/godkey-skill/en ~/.claude/skills/godkey-skill

# Or install the Chinese edition
ln -s ~/godkey-skill/zh ~/.claude/skills/godkey-skill
```

Windows PowerShell:

```powershell
git clone https://github.com/godkey1314/godkey-skill.git D:\tools\godkey-skill
Copy-Item -Recurse D:\tools\godkey-skill\en "$HOME\.claude\skills\godkey-skill"
```

### 2. Common Gate CLI Commands (`en/` Edition)

```bash
# Audit project documentation & active change packages
python en/scripts/godkey_gate.py audit --project-root <project-path>

# Initialize a new project's documentation (full or lite)
python en/scripts/godkey_gate.py init --profile lite --project-root <project-path>

# Create a feature package / pause an experiment / archive through gate
python en/scripts/godkey_gate.py new export-users-excel --state active --project-root <project-path>
python en/scripts/godkey_gate.py move export-users-excel paused --reason "Switching to payment bugfix" --project-root <project-path>
python en/scripts/godkey_gate.py archive export-users-excel --project-root <project-path>

# Install the cross-harness Git pre-commit hook
python en/scripts/godkey_gate.py install-hook --project-root <project-path>
```

### 3. Run Self-Tests

```bash
# English test suite
python -m unittest discover -s en/scripts -p "test_*.py" -v

# Chinese test suite
python -m unittest discover -s zh/scripts -p "test_*.py" -v
```

---

## License

MIT
