# Plan: {{FEATURE_NAME}}

> Created: {{DATE}}

## 1. Background & Objectives

- **Business context**: [TODO: Why this change is needed]
- **Goals & acceptance criteria**: [TODO: Concrete definition of done]

## 2. Blueprint Alignment (Pass 0 Summary)

- **Referenced static docs**: [TODO: e.g. `03-architecture/`, `04-feature-design/`, `05-database/` in full mode, or `01-project-overview.md`, `02-architecture-and-design.md` in lite mode]
- **Key standards & framework constraints**:
  - [TODO: Applicable standard clauses and exact framework version/behavior constraints]

## 3. Codebase Recon (Pass 1 Summary)

### Direct Changes
- [TODO: `path/to/file` — role and intended modification]

### Indirectly Affected (Upstream Callers)
- [TODO: `path/to/caller` — impact assessment]

### Indirectly Affected (Downstream Dependencies / Base Classes / Interfaces)
- [TODO: `path/to/base_or_dep` — contracts and constraints]

### Pattern Reference & Excluded Files
- [TODO: Existing module used as style/pattern reference; unrelated sibling files excluded]

## 4. Implementation & Layering Plan (Pass 2 Summary)

### Core Approach & Trade-offs
- [TODO: Design approach, alternatives considered, and rationale]

### Layered Change Table
| File | Change Type | Layer | Description |
|------|-------------|-------|-------------|
| [TODO] | add/modify/delete | interface/service/data/capability | [summary] |

## 5. Impact Analysis & Operational Changes

- **Feature / API impact**: [TODO]
- **Database impact**: [TODO: Place migration SQL in this package's `ops/` and sync static schema snapshot before archive]
- **Config / deployment impact**: [TODO: Document new env vars, scripts, and rollout steps in `ops/deploy-notes.md`]

## 6. Testing Focus

- **Core path**: [TODO]
- **Boundary conditions**: [TODO]
- **Error paths**: [TODO]
