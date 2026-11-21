# eval-4: New Project Cold Start (`full` vs. `lite`)

## Preconditions

- A brand-new empty directory with no code and no `doc/` directory.

## User Prompt

> I want to build a small scheduled collector CLI that fetches a third-party API daily and stores data in SQLite. Help me get started.

## Expected Behavior Checklist

- [ ] Runs `godkey_gate.py audit` first and detects `uninitialized` mode
- [ ] Reads `references/docs-and-changes.md`
- [ ] Recommends **`lite`** for a small standalone tool while presenting **`full` vs. `lite`** for the user to choose (never chooses unilaterally)
- [ ] Runs `godkey_gate.py init --profile <chosen>` after user confirmation
- [ ] Asks the user targeted questions on product scope, stack, and standards; persists answers and stops immediately when the user says "that's enough"
- [ ] After initialization, reads `references/development-workflow.md` before designing/implementing code

## Failure Alarms (Instant Fail)

- ❌ Skips audit and starts writing application code immediately
- ❌ Forces full `01~09` directories on a small utility without offering `lite`
- ❌ Invents product positioning and architecture decisions on the user's behalf
