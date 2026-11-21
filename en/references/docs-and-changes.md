# Docs & Change Management

Applies to: cold-start initialization, selecting among the four operating modes, 4-state change package transitions, `ops/` asset hygiene, static doc synchronization, and deterministic gate/hook setup.

> **When to load**: ① Pre-flight audit needs to initialize a new project's documentation; ② Moving packages across states (`draft`/`active`/`paused`), organizing `ops/` assets, or logging hotfixes; ③ Gate 5 static truth sync and `archive`.

---

## 1. Four Operating Modes & Selection Guide

| Mode | Best For | Docs Root | Static Layer | Dynamic Layer |
|---|---|---|---|---|
| **`full`** | Mid-to-large systems, multi-module services, dedicated ops | `doc/` or `{project}_doc/` | `01~08` dirs | `09-changes/` |
| **`lite`** | Small long-lived single-repo apps & tools | `doc/` (detects existing `docs/`) | `01~03` core files | `04-changes/` |
| **`external`** | Open-source or existing legacy repositories | Keep native repo layout | Native `README`/`docs` | No foreign dirs added |
| **`demo`** | Throwaway prototypes / verification scripts | None | Exempt | Exempt |

### Cold-Start Initialization (`uninitialized`)
1. Inform the user this is a fresh project, recommend **`full`** or **`lite`** based on scale, and **let the user decide** (also confirm `{project_name}_doc/` for multi-module repos).
2. Run the initializer to scaffold templates and `.godkey.json`:
   ```bash
   python <skill-path>/scripts/godkey_gate.py init --profile full|lite --doc-root doc --project-root <root>
   ```
3. **User-led fill, stop on "enough"**: Ask targeted questions (product scope, stack & layers, coding standards) and write the user's decisions to disk. Stop immediately when the user says "that's enough" — never invent product decisions on the user's behalf.

### External / Existing Repositories (`external`)
- Never inject `01~09` folders into an external repository unless the user explicitly asks;
- Read native `README.md`, `AGENTS.md`/`CLAUDE.md`, and `docs/` to establish context;
- Keep full anti-hallucination engineering discipline (verify framework versions, full codebase recon, layering, cleanup, pattern-spread review, real-chain tests) and sync existing repo docs.

### Upgrading from `lite` to `full`
When a small project outgrows `lite`: split `01~03` into `01~08` directories, rename `04-changes/` to `09-changes/`, and **replace `.godkey.json` with `assets/templates/full/.godkey.json`** (updating `profile`, `changesDir`, and `staticSyncRules`). Existing archived packages stay intact.

---

## 2. Static vs. Dynamic Separation

### Static Truth Layer = Current System Snapshot
- Reflects **what runs today**. Update in place to the latest truth — **never** keep obsolete specs around by "append-only" accretion.
- **Database directory stores snapshots only**: `05-database/schema-snapshot.md` and `05-database/init_tables.sql` (`lite`: `02-architecture-and-design.md`) hold only the latest complete table definitions, never incremental migration clutter.

### Dynamic Change Layer = Feature-Driven Packages
A real feature often spans multiple sessions and produces plans, progress logs, migration SQL, one-off backfill scripts, tests, and reviews. Everything lives together inside **one feature package** (`YYYY-MM-DD_<feature>/`):

```text
2026-11-21_export-users-excel/
├── 01-plan.md          # Objectives, blueprint alignment, recon, layered plan, impact & test focus
├── 02-progress.md      # Cross-session log, pre-change snapshot, decisions, sync record & base commit
├── 03-test.md          # Test plan + execution report
├── 04-review.md        # Self-check loop + code review report
└── ops/                # Feature-specific dynamic operational assets
    ├── 01_alter_xxx.sql    # Migration SQL / one-off data repair SQL
    ├── backfill_xxx.py     # One-off data cleanup or backfill script
    └── deploy-notes.md     # Release order, new env vars, rollback steps
```

- **Single cross-session resume point**: At the start of any follow-up session, read `02-active/<pkg>/01-plan.md` and `02-progress.md` to restore full context immediately.
- **What happens to `ops/` at archive**: Sync final schema into the static DB snapshot and permanent env vars into static deployment docs; keep migration SQL and one-off scripts archived inside `99-archive/<pkg>/ops/` as an audit trail.
- **Local-only dynamic layer (`.gitignore` compatible)**: If a project keeps `09-changes/` (or `04-changes/`) local via `.gitignore` and commits only static truth docs, `godkey_gate.py` automatically detects gitignored untracked dynamic paths and verifies active progress, `hotfix-log.md`, package artifacts, and package waivers directly on local disk (pass `--package <pkg>` explicitly when reading package waivers).

---

## 3. Four-State Folder Machine

Folder location *is* the state — **never maintain manual "In Progress / Done" status fields in Markdown prose**:

```text
01-draft/  ──plan approved──▶  02-active/  ──static docs synced + archive PASS──▶  99-archive/
                                  │  ▲
                   experiment     │  │ resume work
                   paused         ▼  │
                               03-paused/
```

| Folder | Meaning | Transition Command |
|---|---|---|
| `01-draft/` | Plan drafted, awaiting sign-off | `godkey_gate.py new <name> --state draft --project-root <root>` |
| `02-active/` | Actively developed feature package | `godkey_gate.py new <name> --project-root <root>` or `move <name> active` |
| `03-paused/` | Shelved experiment or deferred work (out of active view, context preserved) | `godkey_gate.py move <name> paused --reason "..." --project-root <root>` |
| `99-archive/` | Completed, verified, **static-doc-synced** history | **Exclusively** via `godkey_gate.py archive <name> --project-root <root>` |

- Standalone code reviews (with no active feature package) use `godkey_gate.py new review-<topic> --type review --state active --project-root <root>`, generating only `04-review.md` and validating it cleanly on `archive`.

> Never move packages into `99-archive/` manually, and never pass `--skip-git` inside a Git repository (rejected by the script).

---

## 4. Hotfix Ledger

For single-file, localized fixes confirmed in Pass 1 that do not alter blueprints, DB schema, or architecture, skip creating a package and run:

```bash
python <skill-path>/scripts/godkey_gate.py hotfix \
  --title "Guard null input in export" \
  --symptom "AttributeError when exporting empty list" \
  --root-cause "Missing explicit None check" \
  --files "src/export.py" \
  --verify "pytest tests/test_export.py passed (including new regression test)" \
  --project-root <root>

python <skill-path>/scripts/godkey_gate.py check-sync --mode hotfix --project-root <root>
```

> `--mode hotfix` mechanically verifies: ① `hotfix-log.md` was updated; ② at most 1 business code file changed; ③ no DB/ops/architecture triggers fired. Exceeding any rule blocks and directs work into a feature package.

---

## 5. Deterministic Gate & Sync Mapping

### Static Sync Triggers (Enforced by `godkey_gate.py check-sync`)

| Change Signal (Git Diff + `ops/`) | `full` Required Target | `lite` Required Target | Rule Key |
|---|---|---|---|
| Business source files changed (excluding pure tests) | `04-feature-design/` | `02-architecture-and-design.md` | `featureDocs` |
| DB/ORM/schema paths changed, or `.sql` exists in `ops/` | `05-database/` | `02-architecture-and-design.md` | `dbDocs` |
| Dependency manifests changed, or new top-level source module dir added | `03-architecture/` | `02-architecture-and-design.md` | `archDocs` |
| Docker/deploy/env-example changed, or scripts / real rollout notes in `ops/` | `07-deployment/` | `01-project-overview.md` | `opsDocs` |

### Auditable Waivers (Anti-Laziness, Anti-Poison-Pill)
If a change genuinely does not impact a static doc category (e.g., internal refactoring preserving external contracts), add a concrete waiver on its own line in **the current package's `02-progress.md`** (minimum 12 chars with concrete technical/business rationale; vague excuses like "no doc update needed" are rejected, and non-package checks accept only waivers newly added in the current diff):

```markdown
<!-- doc-sync-waiver: featureDocs | Internal loop refactored to batch query with identical API and behavior -->
```

For doc-only packages needing no tests or review, use in `03-test.md` / `04-review.md`:

```markdown
<!-- artifact-waiver: test | Documentation-only clarification with zero executable code changes -->
```

### Cross-Harness Hook Enforcement
- Install the portable Git `pre-commit` hook in any project:
  ```bash
  python <skill-path>/scripts/godkey_gate.py install-hook --project-root <root>
  ```
- Harness-specific optional native hooks are documented in [hooks/README.md](../hooks/README.md).
