# Development Workflow

Applies to: new features, bug fixes, refactors, module additions, and architecture updates.

> **Split with `SKILL.md`**: `SKILL.md` defines gate pass/block criteria; this file defines the exact steps, output formats, and layering decision tables for Passes 0–5. Read this file in full before starting development work.

---

## Global Lock: Execute Pass 0 -> Pass 5 in order without skipping mandatory gates.

---

## Pass 0: Blueprint & Standards Alignment (Gate 0 — Read Docs & Dependencies Only)

**Goal**: Prevent diving into local code patches before understanding system blueprints, architectural boundaries, and exact framework behavior.

### 1. Read Static Truth Documentation
- **`full` mode**: Read `06-standards/`, `03-architecture/`, relevant `04-feature-design/` docs, and `05-database/schema-snapshot.md`.
- **`lite` mode**: Read `01-project-overview.md`, `02-architecture-and-design.md`, and `03-standards.md`.
- **`external` mode**: Read existing repo `README.md`, `AGENTS.md`/`CLAUDE.md`, and `docs/`.
- If no project-specific coding standards exist, use `assets/templates/full/06-standards/coding-standards.md` from this skill as the baseline.

### 2. Check Active Change Context
- If `godkey_gate.py audit` lists a related active package under `02-active/`, **read its `01-plan.md` and `02-progress.md` first** and continue inside that package — never open a duplicate package.

### 3. Verify Tech Stack & Exact Framework Constraints (Anti-Hallucination)
1. Inspect dependency manifests (`pyproject.toml`, `package.json`, `go.mod`, `pom.xml`, etc.) and list key frameworks with exact versions.
2. Verify critical runtime constraints (concurrency safety, session/connection lifecycle, transaction propagation, serialization):
   - Source available locally -> inspect source directly;
   - Otherwise -> check official documentation for that exact version.
3. **Never guess framework behavior from training memory**; block and ask the user if unverifiable.

**Output**: Concrete, checkable **standards constraint list + framework constraint list** (never vague platitudes like "watch layering").

---

## Pass 1: Codebase Boundary Recon (Gate 1 — Read-Only Source)

**Goal**: Read complete code relationships with Pass 0 blueprints in mind so the plan reflects reality rather than guesswork. **Read-only — do not edit code here.**

### Four Mandatory Traces
1. **Trace downward**: From entrypoints down the call chain to persistence or framework boundaries.
2. **Trace inheritance upward**: For any subclass/implementation touched, read the full base class / interface contracts.
3. **Trace callers upward**: Find every caller up to top-level entrypoints (HTTP routes, CLI commands, scheduled jobs, event handlers).
4. **Scan horizontally for patterns**: Inspect sibling modules to align with existing naming, layout, error handling, and test structure.

### Output: Four-Part File Inventory (Mandatory — No Inventory = Incomplete Read)

```markdown
### Direct Changes
- `path/file_a.ext` — role: ..., intended change: ...

### Indirectly Affected (Upstream Callers)
- `path/file_b.ext` — role: ..., calls file_a

### Indirectly Affected (Downstream Dependencies / Base Classes / Interfaces)
- `path/base_x.ext` — role: base/interface, constraint: ...

### Pattern Reference & Excluded
- `path/similar.ext` — pattern reference for style/structure alignment
- `path/other.ext` — excluded: sibling file handling a different domain object
```

### Scope Classification (Decide Only After Tracing Root Cause!)

- **Hotfix Path** (must satisfy **all 4** criteria):
  1. Modifies at most 1 business source file (excluding test files);
  2. Localized, clear root cause (e.g., missing null guard, boundary condition typo);
  3. No changes to public API contracts, DB schema, dependencies, deployment config, or architectural layers;
  4. Not part of an ongoing multi-iteration package in `02-active/`.
  -> Skip Pass 2 package creation, proceed to Pass 3, and finish via `hotfix-log.md`.
- **Standard Feature Package Path**: Fails any criterion above -> must execute Pass 2.

---

## Pass 2: Plan & Layering On Disk (Gate 2)

**Goal**: Lock the plan, layering, and operational changes on disk. **No business code edits are allowed until the plan is written.**

### 1. Create or Reuse Package (`full` / `lite` mode)
- Needs user sign-off before coding: `python <skill-path>/scripts/godkey_gate.py new <feature-name> --state draft --project-root <root>`
- Requirements already clear: `python <skill-path>/scripts/godkey_gate.py new <feature-name> --state active --project-root <root>`
- Continuing an active package: update existing `01-plan.md` and `02-progress.md`.
- `external` mode: present the complete plan and layered change table in chat before editing.

### 2. Layering Decision Tree & Cross-Layer Pollution Check

Verify every planned line against the architecture doc:

```text
What does this code do?
├─ Routing / HTTP / input validation / response formatting -> Interface Layer
├─ Domain rules / workflow orchestration / transactions    -> Business Layer
├─ SQL / ORM / storage I/O / queue client                  -> Data / Infra Layer
├─ Pure math / stats / external API adapter                -> Capability Layer
├─ Logging / caching / auth cross-cutting concerns         -> Shared Middleware / Utility
└─ Cannot clearly explain its layer?                       -> Stop and rethink
```

| Pollution Pattern | Symptom | Fix |
|---|---|---|
| Data leakage upward | Business layer builds raw SQL or queries | Push down to data layer |
| Business leakage downward | Data layer contains business branching | Pull up to business layer |
| Bloated interface | Controller/router holds core orchestration | Push down to business layer |
| Resource tunneling | Borrowing sessions/clients via unrelated module | Inject explicit module dependency |
| Layer skipping | Interface calls data layer directly | Route through business layer |
| Inline heavy compute | Business/data layer embeds complex calculation | Extract to capability layer |

### 3. Write Plan to Disk
Complete `01-plan.md` (objectives, blueprint alignment, recon summary, layered change table, impact & ops changes, testing focus) and record the Pre-Change Behavior Snapshot in `02-progress.md`.
If created in `01-draft/`, wait for user approval and run `python <skill-path>/scripts/godkey_gate.py move <feature-name> active --project-root <root>` before Pass 3.

---

## Pass 3: Disciplined Implementation & Cleanup (Gate 3)

**Goal**: Execute strictly to plan, leave zero trash, keep operational assets contained.

1. **Respect planned boundaries**: Edit only files listed in the Pass 2 change table; if scope must expand, update `01-plan.md` and notify the user first.
2. **Match existing patterns**: Follow the style and conventions identified in Pass 1.
3. **Cleanup discipline**: Delete obsolete fields, methods, imports, compatibility bridges, and tombstone comments immediately — zero "just in case" fallbacks.
4. **No drive-by refactors**: Log unrelated debt in `02-progress.md` under Open Items for a separate task.
5. **Store dynamic operational assets in `ops/`**:
   - Place migration SQL, one-off backfill/repair scripts, new env var notes, and rollout steps inside the package's `ops/` folder (`ops/01_alter_xxx.sql`, `ops/backfill.py`, `ops/deploy-notes.md`);
   - Never dump incremental migration SQL or temporary scripts into static `05-database/` or business source directories.
6. **Keep `02-progress.md` current**: Record completed work, key decisions, and pitfalls so future sessions resume effortlessly.

---

## Pass 4: Self-Check, Review & Testing (Gate 4)

**Goal**: Catch defects with reviewer rigor and verify real chains before delivery.

1. **Standards Self-Check Loop**:
   - Re-read project coding standards and check every modified file across the 5 dimensions + Pass 3 pattern spread defined in [Code Review](code-review.md);
   - Output concrete per-dimension findings (never rubber-stamp "looks good");
   - Fix violations -> re-check until zero remain (max 3 rounds; escalate if exceeded);
   - Write conclusions to `04-review.md`.
2. **Testing**:
   - Follow [Testing Workflow](testing-workflow.md) (write plan & report in `03-test.md` for feature packages; record reproduction & regression verification in `hotfix-log.md` for hotfixes).

---

## Pass 5: Static Truth Sync & Deterministic Gate Verification (Gate 5 — Hard Gate)

**Goal**: Keep static truth docs perpetually synchronized and eliminate verbal hand-waving.

### 1. Synchronize Affected Static Truth Snapshots
- Feature/API/business rules changed -> update `04-feature-design/` (`lite`: `02-architecture-and-design.md`)
- Layers/module boundaries/stack changed -> update `03-architecture/` (`lite`: `02-architecture-and-design.md`)
- Schema changed or `ops/` contains `.sql` -> update `05-database/schema-snapshot.md` & `init_tables.sql` (`lite`: `02-architecture-and-design.md`)
- Env vars / deployment changed -> update `07-deployment/` (`lite`: `01-project-overview.md`)
- `external` mode -> update affected existing repo `README.md` / `docs/`

> If a change genuinely does not affect a static doc category (e.g., pure internal refactor), add an auditable waiver on its own line in `02-progress.md`:
> `<!-- doc-sync-waiver: featureDocs|archDocs|dbDocs|opsDocs | concrete reason (min 12 chars) -->`

### 2. Run the Deterministic Gate CLI & Show Actual `PASS` Output

- **Mid-iteration checkpoint (feature spans more sessions)**:
  ```bash
  python <skill-path>/scripts/godkey_gate.py check-sync --package <pkg> --mode commit --project-root <root>
  ```
- **Feature complete (mandatory archive gate)**:
  ```bash
  python <skill-path>/scripts/godkey_gate.py archive <pkg> --project-root <root>
  ```
- **Hotfix complete (enforces single-file scope + hotfix log)**:
  ```bash
  python <skill-path>/scripts/godkey_gate.py hotfix --title "..." --symptom "..." --root-cause "..." --files "..." --verify "..." --project-root <root>
  python <skill-path>/scripts/godkey_gate.py check-sync --mode hotfix --project-root <root>
  ```
- **External repo complete**:
  ```bash
  python <skill-path>/scripts/godkey_gate.py check-sync --project-root <root>
  ```
- **Pause / shelve an experiment**:
  ```bash
  python <skill-path>/scripts/godkey_gate.py move <pkg> paused --reason "<why paused>" --project-root <root>
  ```

Task completion is permitted **only** after showing the real `PASS` output from `godkey_gate.py`.

---

## Refactoring Rules

1. **Understand the existing design first**: Know why it was built that way and map every downstream dependent before editing.
2. **Clean cut, no transition shims**: Do not leave dual-track legacy compatibility paths inside a refactor package.
3. **Sync architecture docs before archiving**: Update static architecture snapshots whenever module boundaries or dependency directions change.
