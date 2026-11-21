---
name: godkey-skill
description: >
  Cross-harness structured engineering methodology for all projects and models. Prevents guessing,
  skipping source code, drive-by patches, and stale documentation using a dual-layer doc architecture
  (static truth snapshots + four-state feature change packages) backed by deterministic script gates.
  Triggers: new features, bug fixes, code reviews, refactors, architecture updates, module additions,
  and documentation setup. Not for pure Q&A, copy-only tweaks, or throwaway demos.
---

# GodKey Skill

You are now operating under a **structured engineering methodology**. Your default behavior is replaced:

- Not: "skim a few lines -> patch from training memory -> skip doc updates -> finish"
- Instead: "script audit & mode detection -> blueprint & standards alignment -> read-only codebase recon -> written plan & layering -> disciplined edits & cleanup -> self-check/review/tests -> static truth sync + gate PASS"

## Step 1: Pre-Flight Audit + Load Reference Workflow (Always First)

### 1. Pre-Flight Audit: Run the Gate Script to Detect Mode & Active Work

Run the deterministic audit script first — never guess directory state by eye (`<skill-path>` is the directory containing this `SKILL.md`):

```bash
python <skill-path>/scripts/godkey_gate.py audit --project-root <project-root>
```

Route by the 4 operating modes (plus `uninitialized` cold start; initialization & communication details live in [Docs & Changes](references/docs-and-changes.md)):

| Mode | Detection Condition | Execution Policy |
|---|---|---|
| **`full`** | Mid-to-large / multi-module projects (`01~08` static + `09-changes/`) | Full dual-layer closed loop + script gate |
| **`lite`** | Small long-lived single-repo projects (`01~03` static files + `04-changes/`) | Compact static snapshots + full 4-state packages + script gate |
| **`uninitialized`** | Brand-new empty project (no docs and no existing source) | Recommend & let user choose `full` or `lite` -> `godkey_gate.py init` -> user-led fill, stop when user says enough |
| **`external`** | Open-source or existing legacy project (no GodKey layout, existing code/docs) | **Never inject foreign dirs**; read existing repo docs, keep full anti-hallucination engineering discipline, sync existing docs |
| **`demo`** | User explicitly marks task as a throwaway demo / prototype | Exempt from documentation system; keep basic code cleanliness |

### 2. Identify Task Type and Read the Full Reference Document

| Task Type | Triggers | Must Read First |
|---|---|---|
| Development (incl. design & bug fixes) | New feature, bug fix, refactor, new module, architecture change | [Development Workflow](references/development-workflow.md) |
| Code Review | PR review, workspace diff review, code audit | [Code Review](references/code-review.md) |
| Testing | Writing tests, running tests, coverage & real-chain validation | [Testing Workflow](references/testing-workflow.md) |
| Docs & Change Management | Cold-start init, state moves, archiving, hook setup | [Docs & Changes](references/docs-and-changes.md) |

> **Two-Layer Split (Acting from `SKILL.md` alone is a violation)**: This file defines only **gate pass/block criteria**. Exact step checklists, output formats, decision tables, and CLI flags live exclusively in `references/`.

## Core Architecture: Static Truth Snapshots vs. Dynamic Change Packages

```text
Static Layer (full: 01~08 / lite: 01~03)  <- Single source of current truth (blueprints, arch, DB snapshot, deployment)
Dynamic Layer (09-changes/ or 04-changes/) <- Feature-driven packages; directory location IS state:
  ├── 01-draft/      Proposed plans awaiting sign-off
  ├── 02-active/     Active feature packages (01-plan / 02-progress / 03-test / 04-review / ops/)
  ├── 03-paused/     Shelved experiments or deferred work
  ├── 99-archive/    Completed packages verified by the static sync gate
  └── hotfix-log.md  Single-file hotfix ledger
```

- **Dynamic assets go in `ops/`; DB docs store snapshots only**: Put migration SQL, one-off backfill scripts, and release notes in the feature package's `ops/`. Update the static DB schema snapshot before archiving; `ops/` archives alongside the package.
- **Folders as state**: Never maintain manual "In Progress / Done" status lines in Markdown prose. Move state exclusively via `godkey_gate.py move` or `archive`.

## Gate Criteria (Sequential, Non-Skippable)

### Gate 0: Blueprint & Standards Alignment (Pass 0 — Read Docs & Dependencies Only)

- **Pass criteria**: Read project static standards, architecture, relevant feature blueprints, and any related package in `02-active/`; inspect dependency manifests and actual framework version source/docs to output an actionable **standards constraint list + framework constraint list**.
- **Anti-tunnel-vision rule**: Do **not** jump straight into patching business code in this gate; never guess framework behavior from training memory.

### Gate 1: Codebase Boundary Recon (Pass 1 — Read-Only Source Inspection)

- **Pass criteria**: Guided by the blueprint, read all directly affected files, upstream callers, downstream dependencies/base classes, and sibling pattern references; output the **4-part file inventory** (direct changes / upstream callers / downstream & base classes / pattern reference & excluded) and classify as **Feature Package** vs. **Hotfix**.
- **Block**: Never conclude without reading base classes/interfaces or from partial snippets.

### Gate 2: Plan & Layering On Disk (Pass 2)

- **Pass criteria**: Feature work must create/reuse a package via `godkey_gate.py new` (`draft` or `active`) and write `01-plan.md` with a **layered change table** aligned with the architecture doc.
- **Hotfix exemption**: Single-file, localized fixes confirmed in Pass 1 that do not alter architecture, schema, or blueprints skip creating a package and log to `hotfix-log.md`.
- **Block**: **No written plan = no business code edits** for feature work. If you cannot explain which architectural layer a line belongs to, stop and think first.

### Gate 3: Disciplined Implementation & Cleanup (Pass 3)

- **Pass criteria**: Edit strictly within the planned change table, match existing repo patterns, delete all dead fields/methods/imports/compatibility shims and tombstone comments, place migration SQL/scripts/release notes in `ops/`, and keep `02-progress.md` current.
- **Boundary**: Do not "drive-by refactor" unrelated code; log discovered debt under open items.

### Gate 4: Self-Check, Review & Testing (Pass 4)

- **Pass criteria**: Re-read project standards, run the 5-dimension self-check + pattern spread until zero violations remain (max 3 rounds; escalate if exceeded), run real-chain tests (or explicitly document constrained degradation), and record findings in `03-test.md` and `04-review.md`.

### Gate 5: Static Truth Sync & Deterministic Gate Verification (Pass 5 — Hard Gate)

- **Pass criteria**: Update all affected static truth snapshots (feature design / architecture / DB schema snapshot / deployment), then **actually run the gate CLI and paste the `PASS` output to the user**:
  - Mid-iteration checkpoint: `godkey_gate.py check-sync --package <pkg> --mode commit --project-root <root>`
  - Feature completion: `godkey_gate.py archive <pkg> --project-root <root>` (runs full static sync gate and moves to `99-archive/`)
  - Hotfix completion: `godkey_gate.py hotfix ...` followed by `godkey_gate.py check-sync --mode hotfix --project-root <root>`
  - External repo completion: sync existing repo `README`/`docs`, then run `godkey_gate.py check-sync --project-root <root>`
- **Block**: Verbal claims of "docs updated" do not count. Any script `FAIL` or lazy waiver blocks completion.

## Blocking Invariants

**Uncertain = Stop. Never guess and push ahead.**

Pause immediately and ask the user whenever:
- Project standards, exact framework versions, or source definitions cannot be located;
- Task boundaries or acceptance criteria are ambiguous, or impact spans > 5 modules;
- A static feature blueprint conflicts with existing code behavior (ask which is authoritative);
- Self-check fails to reach zero violations after 3 rounds, or the sync gate fails on an ambiguous domain rule.

## Absolute Prohibitions

- Never skip pre-flight audit or start work without reading the matching `references/` workflow
- Never guess framework behavior from training memory, or modify a subclass without reading its base class/interface
- Never modify feature code without a written plan, or bypass `godkey_gate.py archive` via manual directory moves or `--skip-git` in Git repos
- Never dump migration SQL or one-off scripts into static doc directories or random source folders
- Never keep dead code, tombstone comments, speculative compatibility shims, or zero-value abstraction layers
- Never substitute verbal assurances for actual `godkey_gate.py` `PASS` output
