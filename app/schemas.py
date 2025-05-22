from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models import TaskStatus

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: int = Field(1, ge=1, le=5) # Can be 1 to 5

class TaskCreate(TaskBase):
    status: Optional[TaskStatus] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)

class TaskInDBBase(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Task(TaskInDBBase):
    pass

class TaskLogBase(BaseModel):
    task_id: int
    status: str

class TaskLogCreate(TaskLogBase):
    pass

class TaskLog(TaskLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedTasks(BaseModel):
    items: List[Task]
    total: int
    page: int
    size: int
    pages: int
