from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.app.database import get_connection
from backend.app.models.task import Task, TaskCreate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: str | None = None

def row_to_task(row):
    return Task(
        id=row["id"],
        title=row["title"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
        due_date=row["due_date"],
    )

@router.post("", response_model=Task)
def create_task(payload: TaskCreate):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title cannot be empty.")
    due_date = payload.due_date

    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, due_date) VALUES (?, ?)",
            (title, due_date),
        )
        row = connection.execute(
            "SELECT id, title, completed, created_at, due_date FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        connection.commit()
    return row_to_task(row)

@router.get("", response_model=list[Task])
def list_tasks():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, completed, created_at, due_date FROM tasks ORDER BY id DESC"
        ).fetchall()
    return [row_to_task(row) for row in rows]

@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    updates = []
    values = []
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Task title cannot be empty.")
        updates.append("title = ?")
        values.append(title)
    if payload.due_date is not None:
        updates.append("due_date = ?")
        values.append(payload.due_date)

    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update.")

    values.append(task_id)
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        row = connection.execute(
            "SELECT id, title, completed, created_at, due_date FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        connection.commit()
    if cursor.rowcount == 0 or row is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return row_to_task(row)

@router.patch("/{task_id}/complete", response_model=Task)
def complete_task(task_id: int):
    with get_connection() as connection:
        connection.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        row = connection.execute(
            "SELECT id, title, completed, created_at, due_date FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        connection.commit()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return row_to_task(row)

@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found.")
