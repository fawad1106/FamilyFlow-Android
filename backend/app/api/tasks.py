from fastapi import APIRouter
from backend.app.database import get_connection
from backend.app.models.task import Task, TaskCreate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("", response_model=Task)
def create_task(payload: TaskCreate):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title) VALUES (?)",
            (payload.title.strip(),),
        )
        row = connection.execute(
            "SELECT id, title, completed, created_at FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        connection.commit()

    return Task(
        id=row["id"],
        title=row["title"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
    )

@router.get("", response_model=list[Task])
def list_tasks():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, completed, created_at FROM tasks ORDER BY id DESC"
        ).fetchall()

    return [
        Task(
            id=row["id"],
            title=row["title"],
            completed=bool(row["completed"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
