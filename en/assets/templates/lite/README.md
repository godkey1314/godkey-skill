# Project Documentation Center (Lite)

> Designed for small single-repo apps, utilities, or standalone microservices. Retains static/dynamic separation and the 4-state change package workflow without heavy directory overhead.

## Directory Layout

```text
doc/
├── .godkey.json                  # Gate configuration (profile: lite)
├── 01-project-overview.md        # Static snapshot: product summary, quickstart, env & deployment
├── 02-architecture-and-design.md # Static snapshot: layers, feature blueprints, DB schema snapshot
├── 03-standards.md               # Static snapshot: project-specific coding & Git conventions
└── 04-changes/                   # Dynamic workspace: feature packages with folders as state
    ├── 01-draft/                 # Proposed plans awaiting approval
    ├── 02-active/                # Active in-progress feature packages
    ├── 03-paused/                # Shelved experiments or deferred work
    ├── 99-archive/               # Completed packages verified by the static sync gate
    └── hotfix-log.md             # Structured log for single-file hotfixes
```

## Core Rules

1. **Static vs. Dynamic Separation**: `01~03` describe only what the system *is today*. Plans, progress logs, test reports, code reviews, migration SQL, and one-off scripts live inside `04-changes/`.
2. **Folders as State**: Move package folders via `godkey_gate.py move` / `archive` rather than editing text status labels inside Markdown files.
3. **Archive Gate**: Before archiving any feature package, synchronize `01~02` static snapshots and run `godkey_gate.py archive`.

## Upgrading to Full

When the project grows to multiple business modules, multiple database tables, or independent deployment workflows, split the 3 static files into the `01~08` directories, rename `04-changes/` to `09-changes/`, and replace `.godkey.json` with the full profile template (updating `profile`, `changesDir`, and `staticSyncRules`).
