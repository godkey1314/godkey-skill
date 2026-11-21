# Operational & Release Notes: {{FEATURE_NAME}}

> This directory (`ops/`) stores **dynamic operational assets** tied specifically to this feature:
> - Migration SQL or one-off data repair SQL (e.g. `01_alter_xxx.sql`)
> - One-off backfill / cleanup scripts (e.g. `backfill_xxx.py`)
> - New environment variables, rollout order, and rollback instructions for this release
>
> **Tip**: If this feature introduces no new env vars, scripts, or special rollout steps, leave this file untouched so it does not trigger the `opsDocs` gate.
> When archiving, update the static database schema snapshot and static environment docs; this `ops/` folder stays archived with the feature package as an audit trail.

## 1. Pre-Release & Rollout Order

1. [TODO: e.g., run `ops/01_alter_xxx.sql`]
2. [TODO: e.g., set new env var `XXX`]
3. [TODO: e.g., deploy service and verify health endpoint]

## 2. New / Changed Environment Variables

| Variable | Example Value | Description | Required |
|----------|---------------|-------------|----------|
| [Leave blank if none] | | | |

## 3. SQL & Script Execution Log

| File | Purpose | Idempotent | Environment & Status |
|------|---------|------------|----------------------|
| [Leave blank if none] | | Yes/No | Pending / Staging Done / Prod Done |

## 4. Rollback Plan

- [TODO: How to revert code, config, and data safely]
