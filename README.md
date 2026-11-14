# Expo AI Summit API

FastAPI backend for the Idea Board ideas app. The app is a place for the team to collect ideas for what to build and vote on them, so the best ones get picked.

## Features
- Auth: sign up, email verification, sign in, refresh (rotating), sign out, sign out everywhere, forgot/reset password, change password
- Profile: view, edit, delete account
- Roles: attendee, speaker, organizer, admin
- Ideas: create an idea (title + explanation), list ideas ranked by votes, vote / remove vote (one vote per user per idea), delete own idea
- Admin: list users, change roles

## Run locally
```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

### Windows
SQLAlchemy is pinned to its pure-Python wheel (see `[tool.uv.sources]` in `pyproject.toml`), so no compiled SQLAlchemy extensions are loaded. This avoids `DLL load failed ... An Application Control policy has blocked this file` on locked-down Windows machines. After pulling, run `uv sync` once; it replaces the compiled build already in `.venv`.

PostgreSQL support (`asyncpg`, a compiled package) is optional: `uv sync --extra postgres`.

Demo data is seeded on first start. Demo logins (also shown on the sign-in page): `demo@expo-summit.dev` / `demo12345`, admin `admin@expo-summit.dev` / `admin12345`.

In development, verify and reset tokens are returned in the API response because no email service is wired yet (`EXPOSE_DEV_TOKENS=false` to disable).

## Test and lint
```bash
uv run pytest
uv run ruff check .
```

## Notes
- Default database is SQLite; set `DATABASE_URL` to a PostgreSQL URL (`postgresql+asyncpg://...`) for real use.
- Tables are created on startup for now; add Alembic migrations before production.
