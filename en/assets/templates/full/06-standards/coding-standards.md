# Coding Standards

> Language-agnostic engineering baseline. When a project defines its own standards, project standards take precedence; otherwise this document serves as the default baseline.
> Priority split: **Sections 1–11 are hard engineering discipline**; **Section 12 lists default style suggestions when a project has no established convention yet** (Section 1 Pattern-First always wins over Section 12).

---

## 1. Pattern-First

Before writing new code in any codebase, find an existing similar implementation and align with it. File layout, naming, method signatures, error handling, and tooling choices follow **the project's existing patterns**, never personal habits or training-data defaults.

1. Locate an existing module solving a similar problem;
2. Read its directory layout, naming, parameter/return conventions, and error handling;
3. Match that pattern in new code; if no precedent exists, prefer the simplest direct solution.

---

## 2. Layering Discipline

Every line of code belongs to a clear architectural layer. Dependencies flow strictly downward — never upward or across skipped layers.

| Layer | Responsibilities | Prohibited |
|---|---|---|
| **Interface Layer** | Request/event intake, input validation, business invocation, response formatting | Complex business branching, direct persistence access |
| **Business Layer** | Domain rules, workflow orchestration, transaction boundaries, cross-module coordination | Raw query building or low-level storage connection handling |
| **Data / Infra Layer** | Persistence I/O, external storage/queue clients | Business branching, borrowing unrelated modules' resources |
| **Capability Layer** (optional) | Pure math/stats, external API adapters, AI inference | Hardcoding upstream business decisions |

---

## 3. Module Boundaries & Anti-Overengineering

- **Create a new module when**: it owns a distinct domain, owns its own data model, or is shared by multiple modules.
- **Extend an existing module when**: it operates on the same domain entity, shares data models, or extends existing behavior.
- **Anti-overengineering**:
  - Do not implement unrequested features or "drive-by" refactors;
  - Do not create abstractions or wrapper layers for single-use scenarios or hypothetical future needs;
  - Three similar code blocks > one premature abstraction; direct calls > pointless pass-through delegation.

---

## 4. Code Cleanliness (Deletion Beats Retention)

- Delete unused fields, methods, imports, and obsolete compatibility bridges immediately;
- Never leave tombstone comments ("removed", "temporary workaround", "just in case"), commented-out code blocks, or speculative fallback shims;
- Comments explain **why** (domain invariants, non-obvious trade-offs, framework pitfalls), never obvious **what**;
- Never hardcode credentials (API keys, passwords, tokens); never substitute `print` / `console.log` for structured logging.

---

## 5. Dependency Direction & Resource Ownership

- Dependencies remain acyclic and unidirectional;
- **No resource tunneling**: never borrow database sessions, connections, or clients indirectly through unrelated modules — inject dependencies explicitly.

---

## 6. Data & I/O Performance Invariants

| Prohibited | Required Alternative |
|---|---|
| Loading full entity lists just to count them | Run a `COUNT` query |
| Per-item queries inside loops (N+1) | Batch queries or join once |
| Splitting multi-metric aggregates on the same table into separate queries | Combine into a single aggregate query |
| Unbounded table scans (no pagination / time window) | Always bound by pagination, window, or limit |
| Unbounded concurrency (launching N tasks with no cap) | Bound concurrency with a semaphore / worker pool |
| Sharing non-thread/coroutine-safe sessions across concurrent tasks | Acquire isolated sessions or run sequentially |

Hot paths (dashboards, landing endpoints, high-QPS summaries) should read precomputed snapshots or caches instead of recomputing from scratch per request.

---

## 7. Duplication & Abstraction Threshold

Compare sibling files horizontally (same directory, base class, or interface):

| Occurrences | Action |
|---|---|
| 1–2 | Keep inline; do not abstract prematurely |
| 3–5 | Extract a shared module helper |
| 5+ | Extract a base class, helper module, or shared utility |

---

## 8. Value Semantics Traps

`0`, `""`, `[]`, and `False` are **valid values**, distinct from "missing" (`None` / `null` / `undefined`). Never substitute truthy/falsy checks for null checks:

```python
# Wrong: rate=0 is silently treated as missing!
value = result.get("rate")
rate = to_number(value) if value else None

# Correct: distinguish None from 0 explicitly
rate = to_number(value) if value is not None else None
```

| Language | Proper Missing Check |
|---|---|
| Python | `x is not None` (not `if x`) |
| JavaScript / TS | `x != null` or `x !== undefined && x !== null` (not `!x`) |
| Go | Distinguish pointer `nil` from zero values explicitly |
| Java / Kotlin | `Optional` or explicit `!= null` |
| Rust | `Option<T>` pattern matching |
| C# | `x is not null` / `Nullable<T>.HasValue` |

---

## 9. Generic Component Purity

Generic infrastructure components (executors, middleware, utilities) **must not embed domain-specific branching**. Keep generic protocols domain-agnostic and handle business semantics in business modules.

---

## 10. Testing Discipline

- Pure-function unit tests are only the starting point; **never hide real-chain defects behind mocked core dependencies** (see GodKey Skill Testing Workflow);
- New data queries, business orchestration, endpoints, boundary thresholds, and bug fixes require automated verification;
- Never comment out or `skip` failing tests without fixing the root cause; keep test data isolated from production and clean up after runs.

---

## 11. Frontend Standards (If Applicable)

- **Stable derived state**: use `computed` / `useMemo` / `$derived`; never rebuild stateful objects inside render loops;
- **Async race protection**: guard overlapping async requests with monotonic request tokens or `AbortController`;
- **Duplicate request guards**: prevent concurrent double-submits while loading;
- **Shared formatters**: centralize status labels, dates, currency, and badge styles rather than copying across pages.

---

## 12. Default Style Suggestions (When No Project Pattern Exists)

> Applies only when the project has no established convention; if the project uses another convention (e.g., Go/Pydantic multi-model files, Tailwind/CSS Modules), **Section 1 Pattern-First always wins**.

- **Magic values**: promote repeated status codes, type tags, and domain constants into named enums or constants.
- **Model separation**: keep persistence entities separated from public API DTOs / view models.
- **Styling**: prefer existing UI library components and theme tokens over ad-hoc inline styles.
- **Formatting**: keep consistent indentation (no mixed tabs/spaces), group imports (stdlib -> third-party -> local), and follow native language naming conventions.
