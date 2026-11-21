# Architecture & Feature Design

> Static truth snapshot: represents the currently active layered architecture, module blueprints, and database schema snapshot. Update this document before archiving any feature or schema change.

## 1. Layered Architecture & Directory Mapping

```text
[TODO: e.g.
src/
├── api/       # Interface layer: routing & input validation
├── service/   # Business layer: orchestration & domain rules
└── repo/      # Data layer: persistence & external I/O
]
```

### Dependency Direction Rules
- Interface -> Business -> Data / Capability (no reverse dependencies or layer skipping)
- [TODO: Project-specific boundary rules]

## 2. Core Module Blueprints

### Module 1: [Module Name]
- **Responsibility boundary**: [TODO]
- **Key entrypoints / APIs**: [TODO: signatures or HTTP routes, inputs, outputs]
- **Core business rules & error handling**: [TODO]

## 3. Database Schema Snapshot (write "None" if no DB)

> Maintain only the latest table structure snapshot here; store incremental migration SQL and one-off scripts inside each feature package's `ops/` folder.

### Table: `[table_name]`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| [TODO] | | | |

- **Indexes**: [TODO]
