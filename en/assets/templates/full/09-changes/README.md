# Changes (Dynamic Workspace)

> Central **dynamic workspace** organized by **feature/change package**, using **directories themselves as the state machine**.

## Four-State Machine

```text
01-draft/  ──plan approved──▶  02-active/  ──static docs synced + gate PASS──▶  99-archive/
                                  │  ▲
                   experiment     │  │ resume work
                   paused         ▼  │
                               03-paused/
```

- **`01-draft/`**: Drafted plan awaiting sign-off before major implementation;
- **`02-active/`**: Currently active iterations — open a new session and scan this folder to recover full context;
- **`03-paused/`**: Shelved experiments or deferred work, kept out of active view with preserved state and pause rationale;
- **`99-archive/`**: Completed, tested, reviewed, and **static-doc-synced** history packages (must move via `godkey_gate.py archive`).

## Feature Package Layout (`YYYY-MM-DD_<feature>/`)

- `01-plan.md`: Objectives, blueprint alignment, codebase recon, layered change table, impact analysis, and test focus
- `02-progress.md`: Cross-session iteration log, decisions, pre-change behavior snapshot, and static doc sync record
- `03-test.md`: Test plan + execution report
- `04-review.md`: Self-check loop + code review report
- `ops/`: Feature-specific migration SQL, one-off data scripts, env changes, and rollout/rollback notes

## Hotfixes

Single-file, localized bug fixes that do not alter blueprints or architecture skip creating a package folder and append directly to `hotfix-log.md` (via `godkey_gate.py hotfix`).
