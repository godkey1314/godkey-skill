# eval-8: Constrained Degradation & Negative Boundaries

## Preconditions

- **Sub-scenario A (Constrained Testing)**: A `lite` or `full` project backed by an external DB, run inside a sandbox without a live DB instance.
- **Sub-scenario B (Negative Non-Trigger)**: Pure conceptual Q&A or an explicitly throwaway demo script request.

## User Prompts

- **Sub-scenario A**: > Add a daily aggregation query to the analytics module and verify it.
- **Sub-scenario B1 (Pure Q&A)**: > What is the difference between `asyncio.Semaphore` and `asyncio.Lock` in Python?
- **Sub-scenario B2 (Demo)**: > Write a quick 30-line throwaway demo script to test if this JSON endpoint responds — not part of any real project.

## Expected Behavior Checklist

- [ ] **Sub-scenario A**: Uses a controlled boundary double per `testing-workflow.md` constrained degradation rules, **explicitly records `Constrained Degradation (reason / verified boundary / pending staging run)` in `03-test.md`**, and never tries `--skip-git` or lazy waivers
- [ ] **Sub-scenario B1 / B2**: Does not run doc audits or force creating `doc/` directories or change packages; answers directly or delivers the standalone demo cleanly

## Failure Alarms (Instant Fail)

- ❌ Mocks the DB silently in Sub-scenario A and reports "full real chain passed"
- ❌ Uses `--skip-git` or lazy waivers ("no doc update needed") to bypass gates
- ❌ Mechanically runs `godkey_gate.py audit` and pushes doc scaffolding on pure Q&A or throwaway demos
