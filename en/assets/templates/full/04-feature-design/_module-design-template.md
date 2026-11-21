# [Module Name] Feature Design

> Static truth snapshot (Blueprint): defines the **currently active** business rules, data contracts, and APIs for this module.
> Copy this template to `04-feature-design/[module-name].md` when adding a module. Sync the module doc before archiving any feature/API/data change.

## 1. Responsibilities & Non-Goals

- **Domain**: [TODO]
- **Core responsibilities**: [TODO]
- **Out of scope**: [TODO]

## 2. Core Workflow

```text
[Trigger] -> [Validation & Auth] -> [Core Processing] -> [Persistence / Side Effects] -> [Response]
```

## 3. Business Rules & State Transitions

- **Rule 1**: [TODO: trigger condition, invariant, action]
- **State machine** (if applicable): [TODO: valid states & transitions]

## 4. API Contracts

### Endpoint 1: `[METHOD] /api/...`
- **Purpose & Auth**: [TODO]
- **Request Parameters**:
  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | [TODO] | | | |
- **Response**:
  ```json
  {
    "code": 0,
    "message": "ok",
    "data": {}
  }
  ```
- **Error Codes & Edge Cases**: [TODO]

## 5. Data & Dependencies

- **Tables touched**: `[table_a]` (see `05-database/schema-snapshot.md`)
- **Upstream / downstream modules**: [TODO]
- **Performance & idempotency constraints**: [TODO]
