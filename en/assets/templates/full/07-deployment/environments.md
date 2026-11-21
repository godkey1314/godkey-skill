# Environments & Configuration

> Static truth snapshot: documents active dev/staging/prod environment requirements and environment variables.
> Never put real secrets here; document iteration-specific temporary rollout notes in the feature package's `ops/deploy-notes.md`, then sync permanent env vars here before archiving.

## 1. Environment Matrix

| Environment | Purpose | Entrypoint / Domain | DB / Middleware |
|-------------|---------|---------------------|-----------------|
| Development (`dev`) | Local dev & debugging | `localhost` | [TODO] |
| Staging (`test`) | Integration & regression testing | [TODO] | [TODO] |
| Production (`prod`) | Live traffic | [TODO] | [TODO] |

## 2. Environment Variable Inventory (matches `.env.example`)

| Variable | Description | Required | Example Value (never commit secrets) |
|----------|-------------|----------|--------------------------------------|
| `APP_ENV` | Runtime mode (`dev`/`test`/`prod`) | Yes | `dev` |
| `DATABASE_URL` | Database connection URL | [Yes/No] | `postgresql://user:pass@localhost:5432/app` |
| [TODO] | | | |

## 3. Security Rules

- Commit only `.env.example`; keep `.env` in `.gitignore`;
- Disable debug mode in production (`DEBUG=false`) and use strong random secrets.
