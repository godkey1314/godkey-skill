# Project Documentation Center (Full)

> Built for mid-to-large projects, multi-module services, and long-lived production systems. Core principle: **strict separation between static truth snapshots and dynamic change packages**.

## Directory Layout

```text
doc/ (or {project_name}_doc/ for multi-module repos)
├── .godkey.json              # Gate configuration (profile: full)
│
├── [Static Truth Layer — current system snapshot]
├── 01-product/               # Product overview & local quickstart
├── 02-user-guide/            # End-user manuals
├── 03-architecture/          # Layered architecture, module boundaries & tech stack
├── 04-feature-design/        # Active per-module feature blueprints (core)
├── 05-database/              # Latest complete database schema snapshot (DDL + docs)
├── 06-standards/             # Coding standards, Git workflow & framework rules
├── 07-deployment/            # Environment inventory, release & rollback guide
├── 08-assets/                # OpenAPI exports, diagrams & screenshots
│
└── [Dynamic Change Layer — feature-driven packages, folders as state]
    └── 09-changes/
        ├── 01-draft/         # Proposed plans awaiting approval
        ├── 02-active/        # In-progress feature packages (plan/progress/test/review/ops)
        ├── 03-paused/        # Shelved experiments or deferred initiatives
        ├── 99-archive/       # Completed packages verified by the static sync gate
        └── hotfix-log.md     # Structured ledger for single-file hotfixes
```

## Non-Negotiable Rules

1. **Static Layer Holds Current Truth Only**: Overwrite static docs in place to match current reality — never accumulate stale append-only graveyard docs.
2. **Dynamic Assets Stay in Feature Packages**: Plans, cross-session progress, test plans/reports, code reviews, migration SQL, one-off scripts, and rollout notes belong inside `09-changes/<state>/<date>_<feature>/`.
3. **Database Directory Stores Snapshots Only**: `05-database/` maintains the latest full schema snapshot; incremental migration SQL and one-off repair scripts stay in the feature package's `ops/` and archive with the package.
4. **Sync Before Archiving**: Every package moving from `02-active/` to `99-archive/` must synchronize affected static docs and pass `godkey_gate.py archive`.
