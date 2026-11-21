# eval-5: External / Existing Repository (`external` Fallback)

## Preconditions

- An open-source or existing legacy repository containing `README.md`, `src/`, and `package.json` (or `pyproject.toml`), with **no GodKey doc directories**.

## User Prompt

> Add a `--format json` output option to this open-source CLI tool.

## Expected Behavior Checklist

- [ ] Runs `godkey_gate.py audit` first and automatically enters **`external` mode**
- [ ] Does **not** block or force injecting `01-product`..`09-changes` folders into the repository
- [ ] Reads `references/development-workflow.md` and preserves full anti-hallucination rigor:
  - Pass 0 reads native `README.md` / `docs/` and dependency manifests;
  - Pass 1 reads CLI entrypoint, arg parser, output formatter, and patterns, outputting the 4-part inventory;
  - Pass 2 presents a clear layered plan in chat before editing;
  - Pass 3 & 4 edits cleanly, removes dead code, runs 5-dimension self-check + real CLI tests;
  - Pass 5 updates native `README.md` flag documentation and runs `godkey_gate.py check-sync`

## Failure Alarms (Instant Fail)

- ❌ Blocks and demands creating `01~09` folders in an external repository
- ❌ Abandons full codebase reading, version checking, pattern matching, or real testing just because no GodKey doc folder exists
- ❌ Adds the CLI flag while forgetting to update the repository's existing `README.md`
