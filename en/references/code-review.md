# Code Review

Applies to: standalone code reviews, PR reviews, workspace diff audits, and [Development Workflow](development-workflow.md) Pass 4 self-checks.

> **When to load**: ① Any standalone review task; ② Pass 4 self-check reusing Pass 2's 5 dimensions and Pass 3 pattern spread. Concrete dimensions and report structure are defined exclusively here.

---

## Review Discipline

1. **Load baseline standards first**: Open project coding standards and architecture docs to extract checkable clauses (defaulting to built-in `coding-standards.md` when uncustomized).
2. **Define exact scope**: List all files, modules, and baseline commits reviewed.
3. **Evidence over platitudes**: Never say "looks fine overall". Every finding must include `file:line`, violated rule, and concrete fix guidance.
4. **Sweep beyond the first hit**: Whenever a defect pattern surfaces, search the entire scope for sibling instances.

---

## Review Process (5 Passes, No Skipping)

### Pass 1: Panoramic Scan

**Goal**: Build global context and flag suspicious areas without diving into single lines prematurely.

1. Output the full file list with each file's architectural layer;
2. Map key call chains and shared resource dependencies (DB sessions, connections, caches, clients);
3. Mark all suspicious rule/layer/pattern anomalies for deep inspection.

**Output**: File list + layer tags + key dependency map + flagged hotspots.

### Pass 2: Five-Dimension Deep Dive

Inspect every flagged hotspot and all 5 dimensions thoroughly (can be checked concurrently):

1. **Dimension 1 — Architectural Compliance**
   - Layer breaches: data leaking upward, business rules leaking downward, layer skipping?
   - Resource tunneling: borrowing sessions/connections through unrelated modules?
   - Generic component purity: business branching inside shared utilities or middleware?
2. **Dimension 2 — Code Quality**
   - Horizontal comparison across sibling files: 3+ repeated structural patterns?
   - Cleanliness & semantics: dead code, compatibility junk, tombstone comments, bare magic values, value-semantics bugs (`0`/`""`/`[]` treated as missing)?
   - Pattern consistency, typing, and import hygiene.
3. **Dimension 3 — Performance & Data**
   - Query patterns: N+1 loops, loading full lists to count, unbounded scans, split multi-metric queries on the same source?
   - Concurrency & lifecycle: thread/coroutine safety of shared sessions, bounded concurrency caps, adherence to verified framework version rules?
   - Hot paths: precomputed snapshots/caching vs. full real-time recomputation per request?
4. **Dimension 4 — Test Coverage**
   - Do touched data queries, orchestration flows, endpoints, and boundary thresholds have automated tests?
   - Are real chains verified (or explicit degradation documented when environment-constrained)?
5. **Dimension 5 — Frontend Specifics** (if applicable)
   - Stable derived state (`computed`/`useMemo`/`$derived`) without rebuilding stateful objects on render?
   - Async race protection (request tokens / `AbortController`) and duplicate submit guards?
   - Reuse of shared formatters?

**Output**: Per-dimension findings with exact `file:line` and violated clauses.

### Pass 3: Pattern Spread (Key Depth Differentiator)

**Goal**: Take every defect pattern found in Pass 2 and sweep all other files for the same pattern.

> Mandatory question: **"Where else in this codebase does this exact mistake pattern exist?"**

Examples:
- One N+1 query found -> sweep all list/summary endpoints for query-in-loop patterns;
- One shared async session across concurrent tasks -> audit every concurrent entrypoint's session acquisition;
- One `if rate:` falsy bug -> search all numeric/optional field checks globally;
- One stray migration SQL in source dirs -> sweep repo for misplaced operational scripts.

**Output**: Sweep scope + newly discovered instances (explicitly state what was checked even if none found).

### Pass 4: Severity Triage & Full Report

1. Confirm every file and all 5 dimensions have explicit conclusions;
2. Document both **issues** and **well-implemented compliant parts**;
3. Group findings by `P0 (Blocker) / P1 (High) / P2 (Medium) / P3 (Low)` with a phased fix order and verifiable acceptance checklist.

Required report structure:

```markdown
## 1. Review Scope & Baseline
## 2. Readiness & Overall Verdict
## 3. Issue List (P0 / P1 / P2 / P3)
   Each item: Location (file:line) / Category / Violated Rule / Fix Suggestion (before & after)
## 4. Pattern Spread Results
## 5. Compliant Highlights
## 6. Fix Sequence & Acceptance Checklist
```

### Pass 5: Persist Report to Disk (Verbal-Only Conclusions Do Not Count)

- **Linked to an active feature package (`full` / `lite`)**: Write into that package's **`04-review.md`** (append round headings for multi-round reviews);
- **Standalone review (`full` / `lite`, no active feature package)**: Create a dedicated review package via `python <skill-path>/scripts/godkey_gate.py new review-<scope> --type review --state active --project-root <root>`, write the report into **`04-review.md`**, and archive it via `godkey_gate.py archive review-<scope> --project-root <root>` (standalone review packages validate `04-review.md` independently without colliding with uncommitted code being reviewed; open a standard feature package later if fixes are scheduled);
- **`external` mode**: Output the complete report in chat and persist to a user-specified path if requested.

> Never sign off based solely on pure-function unit tests while real-chain risks remain unchecked; never deliver a review report without concrete acceptance criteria.
