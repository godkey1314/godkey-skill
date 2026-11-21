# Testing Workflow

Applies to: authoring tests, executing tests, validating functional behavior and regressions.

> **When to load**: Standalone testing tasks, or Pass 4 verification in [Development Workflow](development-workflow.md). Test tiers, real-chain rules, explicit constrained-environment degradation, and report format live exclusively here.

---

## Global Lock: Execute Pass 0 -> Pass 5 sequentially.

---

## Pass 0: Test Plan (Design Before Writing Tests)

1. **Standard feature package**: Fill Section 1 of **`03-test.md`** (in-scope, out-of-scope & reasons, environment/isolation, core test cases) before writing test code.
2. **Single-file hotfix**: Skip creating a separate plan file; write a minimal reproduction test first and log results in `hotfix-log.md`.
3. **`external` mode**: Present a concise test plan (scope, levels, edge cases) in chat before writing tests.

---

## Pass 1: Scope & Minimum Coverage Bar

Match change types to minimum verification requirements:

| Change Type | Minimum Requirement |
|---|---|
| New / updated data query | At least one integration test verifying real SQL / storage execution |
| New / updated business orchestration | Happy path + key error paths + transaction/side-effect assertions |
| New / updated endpoint | Status codes, response schema, auth, and invalid inputs |
| Threshold / numeric / boundary logic | Zero, null/None, below-limit, exact-limit, and over-limit cases |
| Bug fix | **Write a failing reproduction test first**, then verify it passes after the fix |
| CLI / scripts / gate tools | End-to-end execution in an isolated temporary directory |

Explicitly list **what is not tested and why** (already covered / environment constrained / N/A).

---

## Pass 2: Author Tests (Real Chains First + Explicit Degradation)

### 1. Default Invariant: Verify Real Execution Chains
Pure-function unit tests are only the starting point — **never mock away core dependencies and declare the full chain verified**:

| Chain | Default Requirement |
|---|---|
| Database queries | Real test DB / isolated temp DB / test container — do not mock SQL execution |
| Business orchestration | Wire real collaborators to verify end-to-end call flow & state transitions |
| Background / cron jobs | Trigger execution and verify persisted side effects & idempotency |
| HTTP / CLI interfaces | Issue real HTTP requests or subprocess invocations; assert exit/status codes & output |

### 2. Explicit Constrained-Environment Degradation (No Deadlocks, No Silent Cheating)
When the current environment **objectively lacks external dependencies** (e.g., no DB instance in sandbox, no paid third-party sandbox credentials, no network):
1. Use a controlled test double (Fake / Stub / recorded fixture) at that external boundary to verify contract serialization, parameters, and error paths;
2. **Explicitly mark it in `03-test.md`'s chain matrix and Uncovered Items**: `Constrained Degradation (reason: ...; boundary verified: ...; pending real-chain run in staging)`;
3. Never represent degraded tests as full real-chain verification.

### 3. Authoring Essentials
- **Layout**: Match existing repo test layout and naming (default `tests/<module>/test_<feature>.<ext>` mirroring source);
- **Edge cases first**: `None`/`null`, `0`, empty lists/strings, max limits, timeouts, race conditions;
- **Isolation**: Never touch production data; always clean up temp fixtures.

---

## Pass 3: Execute & Root-Cause Failures

1. Run **new tests + all related regression tests** to confirm nothing else broke.
2. On failure: **never comment out, `skip`, or weaken assertions to force green**. Diagnose root cause first:
   - Production code bug -> fix code;
   - Faulty test expectation -> fix test;
   - Fixture/environment issue -> fix environment and document it.

---

## Pass 4: Coverage Audit & Gap Closing

Cross-check against Pass 1 scope:
1. Does every directly modified behavior have automated verification?
2. Has every critical path and error path been exercised?
3. Are zero, null, and boundary thresholds covered?
4. Were any core dependencies silently mocked without explicit degradation notes?

Any gap found -> return to Pass 2, close it, and re-run Pass 3.

---

## Pass 5: Persist Test Report

Record exact commands run, pass/total counts, chain verification matrix (including any degradation notes), and uncovered items:
- **`full` / `lite` feature package**: Fill Section 2 ("Test Report") of **`03-test.md`**;
- **Hotfix**: Record via `godkey_gate.py hotfix --verify "..."` into `hotfix-log.md`;
- **`external` mode**: Output the full test report with actual command outputs in chat.

Never claim "tests passed" verbally without exact commands and real execution results.
