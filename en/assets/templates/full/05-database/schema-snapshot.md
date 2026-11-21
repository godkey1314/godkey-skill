# Database Schema Snapshot

> Static truth snapshot: `05-database/` maintains **only the latest complete schema snapshot**.
> Store incremental migration SQL and one-off data repair scripts inside the relevant feature package's `09-changes/<state>/<package>/ops/` directory; synchronize final table definitions back here and into `init_tables.sql` before archiving.

## 1. Overview

- **Engine & Version**: [TODO: e.g., PostgreSQL 16 / MySQL 8.0 / SQLite 3]
- **Charset / Collation**: `UTF-8` / `utf8mb4`
- **Baseline DDL Script**: `05-database/init_tables.sql`

## 2. Table Inventory

| Table | Module | Purpose | Estimated Scale |
|-------|--------|---------|-----------------|
| [TODO] | | | |

## 3. Table Definitions

### Table 1: `[table_name]` — [Summary]

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | BIGINT | No | Auto / Snowflake | Primary key |
| `created_at` | TIMESTAMP | No | CURRENT_TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | No | CURRENT_TIMESTAMP | Update time |

- **Indexes**: `PRIMARY (id)`, [TODO]
- **Constraints / Soft-delete convention**: [TODO]
