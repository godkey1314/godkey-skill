# Changes (Dynamic Workspace)

> Organizes active development by **feature/change package**. **Directory location is the state** — do not maintain manual status text inside Markdown documents.

## State Machine

```text
01-draft/  ──plan approved──▶  02-active/  ──static docs synced + gate PASS──▶  99-archive/
                                  │  ▲
                   experiment     │  │ resume work
                   paused         ▼  │
                               03-paused/
```

## Standard Feature Package Contents

- `01-plan.md`: Objectives, blueprint alignment, codebase recon, layered change table, and test focus
- `02-progress.md`: Cross-session iteration log, decisions, pre-change behavior snapshot, and static sync record
- `03-test.md`: Test plan + execution report
- `04-review.md`: Self-check loop & code review report
- `ops/`: Feature-specific migration SQL, one-off data scripts, env changes, and rollout/rollback notes

## Hotfixes

Single-file, localized bug fixes that do not alter architecture, database schema, or feature blueprints do not need a package folder — record them directly in `hotfix-log.md`.
