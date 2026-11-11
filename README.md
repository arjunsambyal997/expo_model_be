# Expo AI Summit API

FastAPI backend for the Dubai Expo AI Summit app.

## Features
- Auth: sign up, email verification, sign in, refresh (rotating), sign out, sign out everywhere, forgot/reset password, change password
- Profile: view, edit, delete account
- Roles: attendee, speaker, organizer, admin
- Summit: sessions (agenda), speakers, personal schedule
- Admin: list users, change roles

## Run locally
```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

Demo data is seeded on first start. Demo admin: `admin@expo.test` / `admin12345`.

In development, verify and reset tokens are returned in the API response because no email service is wired yet (`EXPOSE_DEV_TOKENS=false` to disable).

## Test and lint
```bash
uv run pytest
uv run ruff check .
```

## Notes
- Default database is SQLite; set `DATABASE_URL` to a PostgreSQL URL (`postgresql+asyncpg://...`) for real use.
- Tables are created on startup for now; add Alembic migrations before production.
