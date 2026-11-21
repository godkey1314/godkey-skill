# Git Workflow

> Static truth snapshot: defines this project's branching conventions, commit message format, and safety rules.

## 1. Branches & Releases

- `main` / `master`: stable trunk kept releasable; tag releases with annotated tags (e.g., `v1.0.0`).
- `dev/<topic>` or `feat/<feature>`: feature or major refactor branches.
- `fix/<issue>` / `hotfix/<issue>`: bug-fix branches.

## 2. Commit Message Format

```text
<type>(<scope>): <subject>

<optional body explaining motivation and key changes>
```

| Type | Meaning |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation updates (static blueprints, change packages, templates) |
| `refactor` | Code refactor without external behavior change |
| `test` | Test additions or updates |
| `perf` | Performance improvement |
| `chore` | Build, dependency, script, or tooling maintenance |

## 3. Hard Safety Rules

- Never commit `.env`, private keys, tokens, or credentials (commit `.env.example` only);
- Never run `git push --force` or `git reset --hard` against shared trunk branches;
- Never commit stray debug prints or large commented-out code blocks;
- When `godkey_gate.py install-hook` is enabled, pre-commit automatically verifies progress/doc sync.
