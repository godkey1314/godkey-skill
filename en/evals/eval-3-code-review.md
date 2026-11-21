# eval-3: Standalone Code Review

## Preconditions

- A `full` or `lite` project with 2–3 uncommitted modified files containing deliberate issues (e.g., SQL built inside the service layer + two sibling `if rate:` value-semantics traps).

## User Prompt

> Please review my uncommitted workspace changes.

## Expected Behavior Checklist

- [ ] Runs `godkey_gate.py audit` and reads `references/code-review.md` in full
- [ ] **Pass 1**: Loads project standards, outputs full file list + architectural layer tags + flagged hotspots
- [ ] **Pass 2**: Provides concrete per-dimension findings across all 5 dimensions (`file:line` + violated clause + before/after fix)
- [ ] **Pass 3**: After catching the first value-semantics bug or layer violation, sweeps other files and uncovers sibling occurrences
- [ ] **Pass 4**: Triages by `P0/P1/P2/P3`, lists compliant highlights, phased fix order, and an acceptance checklist
- [ ] **Pass 5**: Persists report to active package `04-review.md` (or creates a standalone review package via `godkey_gate.py new review-<scope> --type review --state active --project-root <root>` and archives it via `godkey_gate.py archive`)

## Failure Alarms (Instant Fail)

- ❌ Skips reading `references/code-review.md` and gives generic high-level advice
- ❌ Stops after the first defect without running Pass 3 pattern spread
- ❌ Outputs verbal conclusions only without persisting `04-review.md` or omitting acceptance criteria
