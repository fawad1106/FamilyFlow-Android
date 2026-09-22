# LifeOS

A personal command center for tasks, projects, notes, files, search and accounts.

## Run
```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000

## Current product
- Accounts and cookie sessions
- Tasks with due dates, projects and tags
- Task completion, editing and deletion
- Projects and progress
- Notes with tags
- File upload, open and delete
- Dashboard statistics
- Global search
- Responsive dark-mode interface
- SQLite migrations from the earlier LifeOS task schema

Before public production deployment: enable HTTPS/secure cookies, use PostgreSQL, use persistent file storage, add backups, rate limits and a security review.
