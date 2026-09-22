from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: str | None = None

class Task(BaseModel):
    id: int
    title: str
    completed: bool
    created_at: str
    due_date: str | None = None
