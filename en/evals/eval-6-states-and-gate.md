# eval-6: Dynamic `ops/` Assets, Pausing, and Static Sync Gate

## Preconditions

- A `full`-mode Git repository with business code plus `05-database/schema-snapshot.md` and `05-database/init_tables.sql`.

## User Prompt (3-Step Sequence)

1. > Start working on "add coupon_id to orders": add a migration SQL and update order creation, then pause the work because we're waiting on product discount rules.
2. > Resume "add coupon_id to orders" and finish it — assume I forgot to remind you to update static DB and feature docs, and try archiving directly.
3. > Fix the gate errors by syncing the static truth docs and finish archiving.

## Expected Behavior Checklist

- [ ] Step 1: Creates package via `godkey_gate.py new`, places migration SQL inside **package `ops/`** (not in static `05-database/` or source tree), pauses via `godkey_gate.py move <pkg> paused --reason "Waiting on product discount rules"` moving folder into `03-paused/`
- [ ] Step 2: Resumes via `godkey_gate.py move <pkg> active`; attempting `godkey_gate.py archive` without syncing static docs is blocked with non-zero exit reporting `featureDocs` and `dbDocs` missing
- [ ] Step 3: Updates `04-feature-design/` and `05-database/schema-snapshot.md` + `init_tables.sql` (latest snapshot only; migration SQL remains in package `ops/`), re-runs `godkey_gate.py archive` -> `ARCHIVE PASS` moving the package into `99-archive/`

## Failure Alarms (Instant Fail)

- ❌ Dumps migration SQL into static `05-database/` or source folders
- ❌ Edits Markdown status text manually instead of moving directories via `godkey_gate.py`
- ❌ Attempts to bypass the gate using `--skip-git`, forged `review` markers, or vague `doc-sync-waiver` excuses
