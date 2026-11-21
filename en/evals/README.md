# Evals: GodKey Skill Behavioral Verification Suite

## Why Evals Exist

GodKey Skill relies on **two-layer progressive disclosure + dual-layer documentation + deterministic script gates**:
- `SKILL.md` holds gate pass/block criteria; concrete execution steps live in `references/`;
- State transitions and static doc synchronization are verified mechanically by running `scripts/godkey_gate.py`.

This directory defines 8 cross-harness reproducible scenarios to verify that agents (especially weaker or shortcut-prone models) genuinely follow the methodology.

## How to Run

1. Open a **brand-new session** (clean context with zero prior residue);
2. Set up the precondition repository described in the eval;
3. Send the exact prompt in "User Prompt" to the target agent/harness;
4. Grade against the **tool call trace** (files read, `godkey_gate.py` commands actually executed, and real outputs) — never trust verbal claims alone.

## Pass Criteria

- **PASS**: All expected checklist items verified and zero "Failure Alarms" triggered;
- **FAIL**: Any Failure Alarm triggered (especially editing code without reading `references/`, or claiming docs are synced without showing `godkey_gate.py` `PASS` output);
- Run each scenario 3 times across clean sessions — 3/3 passes indicates stability.

## Scenario Index

| Scenario | Verification Focus |
|---|---|
| [eval-1-new-feature](eval-1-new-feature.md) | Standard full-chain flow: script audit -> Pass 0 blueprint -> Pass 1 read-only recon -> Pass 2 written plan -> implementation -> static sync + `archive PASS` |
| [eval-2-bug-hotfix](eval-2-bug-hotfix.md) | Hotfix routing: Pass 1 root-cause recon first -> single-file hotfix classification -> skip package -> `hotfix` log + `check-sync --mode hotfix` |
| [eval-3-code-review](eval-3-code-review.md) | Review flow: read `code-review.md` -> 5 dimensions -> pattern spread -> standalone `--type review` package archived |
| [eval-4-cold-start](eval-4-cold-start.md) | Cold start: detect `uninitialized` -> let user choose `full`/`lite` -> `godkey_gate.py init` -> user-led fill |
| [eval-5-external-repo](eval-5-external-repo.md) | External repo fallback: auto-enter `external` mode, never inject foreign dirs, keep full anti-hallucination rigor |
| [eval-6-states-and-gate](eval-6-states-and-gate.md) | Dynamic layer & gate: migration SQL in `ops/`, pausing to `03-paused/`, missing static docs blocked by `archive` then resolved |
| [eval-7-resume-and-blocking](eval-7-resume-and-blocking.md) | Cross-session resume & blocking invariants: resume existing `02-active/` package without duplicating; stop and ask on blueprint/code conflict |
| [eval-8-degraded-and-negative](eval-8-degraded-and-negative.md) | Anti-cheating & negative bounds: explicit constrained-environment degradation with no gate bypass; pure Q&A and demos skip doc workflow |
