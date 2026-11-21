# eval-1: New Feature (Full End-to-End Flow)

## Preconditions

- A Git repository initialized via `godkey_gate.py init --profile full`;
- Multi-layer codebase (interface / service / data) ready for a cross-file feature (e.g., exporting users to Excel).

## User Prompt

> Add an Excel export feature for the user list.

## Expected Behavior Checklist

- [ ] Runs `godkey_gate.py audit` first and detects `full` mode and active package state
- [ ] Reads `references/development-workflow.md` in full before starting
- [ ] **Pass 0**: Reads `06-standards/`, `03-architecture/`, `04-feature-design/`, and dependency manifests; outputs concrete standards & framework constraint lists
- [ ] **Pass 1**: Performs read-only codebase recon and outputs the 4-part file inventory, classifying the task as a feature package
- [ ] **Pass 2**: Runs `godkey_gate.py new`, writes `01-plan.md` with a layered change table before modifying any business code
- [ ] **Pass 3 & 4**: Implements cleanly, removes dead code, persists test plan/report to `03-test.md` and self-check findings to `04-review.md`, updates `02-progress.md`
- [ ] **Pass 5**: Syncs `04-feature-design/` (and other affected static docs), runs `godkey_gate.py archive`, and pastes real `ARCHIVE PASS` output

## Failure Alarms (Instant Fail)

- ❌ Modifies code without reading `references/development-workflow.md`
- ❌ Fabricates filenames/functions before reading source, or edits business code without a written plan
- ❌ Skips updating static docs or moves folders manually bypassing `godkey_gate.py archive`
- ❌ Verbally claims "docs updated" without real `godkey_gate.py` `PASS` output
