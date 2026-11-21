# eval-2: Single-File Bug Fix (Hotfix Path)

## Preconditions

- A Git repository using `full` or `lite` documentation layout;
- A localized single-file bug (e.g., an export helper crashing on `None` input).

## User Prompt

> Running the export command throws a null-input error. Please investigate and fix it.

## Expected Behavior Checklist

- [ ] Runs `godkey_gate.py audit` and reads `references/development-workflow.md`
- [ ] **Pass 0**: Reads project standards and relevant blueprints instead of guessing from the error line
- [ ] **Pass 1**: Traces the failing function definition and callers completely, confirming single-file scope with no arch/schema/blueprint change -> **classifies as Hotfix**
- [ ] Does **not** create an unnecessary feature package directory
- [ ] Writes a failing reproduction test first, applies the fix, and confirms regression tests pass
- [ ] Runs `godkey_gate.py hotfix ...` to append `hotfix-log.md`, then runs `godkey_gate.py check-sync --mode hotfix --project-root <root>` and shows `PASS`

## Failure Alarms (Instant Fail)

- ❌ Deadlocks claiming "cannot read code without a plan", or guesses a fix from a single stacktrace line
- ❌ Creates a heavy feature package for a 5-line single-file null guard
- ❌ Omits `hotfix-log.md` or fails to run `check-sync --mode hotfix`
