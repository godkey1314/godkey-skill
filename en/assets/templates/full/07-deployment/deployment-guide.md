# Deployment Guide

> Static truth snapshot: describes the standard release, verification, backup, and rollback procedure for the current system.
> Feature-specific migration SQL, one-off scripts, and release ordering live in the corresponding feature package's `ops/deploy-notes.md`.

## 1. Pre-Release Checklist

- [ ] Feature package passed `godkey_gate.py check-sync` and static docs are synchronized
- [ ] All tests pass with zero unresolved P0/P1 findings
- [ ] Any migration SQL and new env vars in the package's `ops/` have been reviewed
- [ ] Production backup completed (mandatory before any DB change)

## 2. Standard Release Steps

```bash
# 1. Pull target release code / image
[TODO]

# 2. Verify .env and new configuration keys
[TODO]

# 3. Apply release-specific migrations if any (see feature package ops/)
[TODO]

# 4. Build and restart services
[TODO]
```

## 3. Post-Release Verification

- **Health check**: `[TODO: e.g., curl -f http://localhost:8000/health]`
- **Log inspection**: `[TODO: command to tail service logs]`
- **Smoke checks**: [TODO]

## 4. Backup & Rollback

- **Database backup**: `[TODO]`
- **Application rollback**: `[TODO: revert to previous image/tag and restart]`
- **Data rollback strategy**: [TODO]
