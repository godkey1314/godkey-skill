# System Architecture

> Static truth snapshot: defines active architectural layers, module boundaries, and key runtime invariants. Update before archiving any architectural or dependency change.

## 1. Topology Overview

```text
[TODO: Client / Interface / Service / Capability / Data & External Services diagram]
```

## 2. Layers & Directory Mapping

| Layer | Directory | Responsibilities | Prohibited Crossings |
|-------|-----------|------------------|----------------------|
| Interface | `[TODO]` | Routing, input validation, auth, response shaping | Business rules, raw SQL |
| Business | `[TODO]` | Domain rules, transactions, orchestration | Persistence implementation details |
| Data / Infra | `[TODO]` | Persistence I/O, query building, connection lifecycle | Business branching, resource tunneling |
| Capability (optional) | `[TODO]` | Pure computation, external API adapters, AI inference | Hardcoded upstream business decisions |

## 3. Module Boundaries & Dependencies

| Module | Boundary | Allowed Dependencies | Forbidden Dependencies |
|--------|----------|----------------------|------------------------|
| [Module 1] | [TODO] | | |

## 4. Cross-Cutting Invariants

- **Auth & Authorization**: [TODO]
- **Concurrency, Transactions & Session Lifecycle** (critical anti-hallucination guard): [TODO]
- **Caching & Hot Paths**: [TODO]
- **Error Handling & Observability**: [TODO]
