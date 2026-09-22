# LifeOS

LifeOS is a personal command center for tasks, projects, notes, files, search, accounts and a dashboard.

## Features
- Account registration, login, logout and secure cookie sessions
- Per-user tasks with due dates, tags, projects, completion, editing and deletion
- Projects with descriptions, labels and progress counts
- Notes with tags, project links, editing and deletion
- File upload/download/delete with a 10 MB limit
- Dashboard statistics
- Global search across tasks, projects and notes
- Responsive mobile/desktop interface
- Persistent dark-mode preference
- PostgreSQL support for production and SQLite fallback for local development
- Railway healthcheck and Docker deployment configuration
- Admin user-count panel visible only to the LifeOS admin account

## Local development
```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000

## Production
Set `DATABASE_URL` to the Railway PostgreSQL connection string. The application automatically creates its required tables on startup and stores uploaded file bytes in the database so Railway deployments do not depend on an ephemeral local filesystem.

The container starts with:
```
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Health endpoint: `/health`.

## Project status
The application code and Railway deployment configuration are in the repository. Final production verification still requires a Railway PostgreSQL service, environment variable wiring, a successful build/deploy, and an HTTP healthcheck.

<!-- deployment sync -->
