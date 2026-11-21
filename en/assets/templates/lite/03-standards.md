# Development Standards

> Project-specific coding and collaboration standards. List project overrides here; anything unspecified defaults to GodKey Skill's built-in engineering standards (pattern-first, layering discipline, zero dead/compat code, strict value semantics, no hardcoded secrets, real-chain testing).

## 1. Project Conventions

- **Formatting & linting**: [TODO: e.g. ruff / prettier / gofmt]
- **Naming & file layout**: [TODO: follow existing repo patterns]
- **Error handling & logging**: [TODO]
- **Framework version constraints** (anti-hallucination): [TODO: e.g. ORM session concurrency rules]

## 2. Verification Commands

- **Run tests**: `[TODO]`
- **Lint / typecheck**: `[TODO]`

## 3. Git Workflow

- **Branching strategy**: [TODO]
- **Commit format**: `<type>(<scope>): <subject>` (`feat` / `fix` / `docs` / `refactor` / `test` / `chore`)
- **Hard prohibitions**: Never commit `.env` or plaintext secrets; never leave commented-out code blocks or compatibility junk.
