# Review & Self-Check: {{FEATURE_NAME}}

> Records the 5-dimension self-check loop or standalone code review findings and pattern-spread checks.
> For doc-only/non-code changes, add an auditable waiver on its own line:
> `<!-- artifact-waiver: review | concrete reason (min 12 chars) -->`

## 1. Review Scope & Baseline

- **Standards referenced**: [TODO: Project coding standards & framework constraints]
- **Files reviewed**: [TODO]

## 2. Five-Dimension Findings

- **Dimension 1 — Architectural Compliance** (layering / resource tunneling / generic component purity): [TODO: concrete finding]
- **Dimension 2 — Code Quality** (cross-file duplication / magic values / compatibility junk / value semantics / pattern consistency): [TODO: concrete finding]
- **Dimension 3 — Performance & Data** (N+1 / unbounded scans / concurrency safety / hot-path caching): [TODO: concrete finding]
- **Dimension 4 — Test Coverage** (real-chain validation / boundary cases / regression protection): [TODO: concrete finding]
- **Dimension 5 — Frontend Specifics** (if applicable: derived state stability / async race guard / duplicate request prevention / formatter reuse): [TODO or N/A]

## 3. Pattern Spread (Code Review Pass 3)

- [TODO: Sweep across sibling/similar files for any defect pattern found above]

## 4. Issue List & Closure

### P0 Blocker
- [None / file:line + violated rule + fix verification]

### P1 High Priority
- [None / file:line + violated rule + fix verification]

### P2 / P3 Medium & Low
- [None / file:line + suggestion]

## 5. Acceptance Checklist

- [ ] All P0/P1 issues resolved and re-verified
- [ ] Dead code and compatibility shims completely removed
- [ ] Static truth documentation synchronized with latest design
