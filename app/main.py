from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Annotated
from contextlib import asynccontextmanager
import math

from app import crud, models, schemas
from app.database import get_db, engine, init_db_connection, close_db_connection
from app.background_tasks import process_task_in_background
from app.models import TaskStatus

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_connection() # Check DB connection
    print("FastAPI application startup complete.")
    yield
    await close_db_connection()
    print("FastAPI application shutdown.")

app = FastAPI(title="Async Task Management API", version="0.1.0", lifespan=lifespan)


@app.post("/tasks", response_model=schemas.Task, status_code=http_status.HTTP_201_CREATED)
async def create_new_task(task: schemas.TaskCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_task(db=db, task=task)

@app.get("/tasks", response_model=schemas.PaginatedTasks)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    title: Optional[str] = Query(None, min_length=1, max_length=50),
    status: Optional[TaskStatus] = Query(None)
):
    skip = (page - 1) * size
    tasks, total_count = await crud.get_tasks(db, skip=skip, limit=size, title=title, status=status)
    total_pages = math.ceil(total_count / size) if total_count > 0 else 1
    return schemas.PaginatedTasks(items=tasks, total=total_count, page=page, size=size, pages=total_pages)

@app.get("/tasks/{task_id}", response_model=schemas.Task)
async def read_task(task_id: int, db: AsyncSession = Depends(get_db)):
    db_task = await crud.get_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task)
async def update_existing_task(task_id: int, task: schemas.TaskUpdate, db: AsyncSession = Depends(get_db)):
    updated_task = await crud.update_task(db=db, task_id=task_id, task_update_data=task)
    if updated_task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")
    return updated_task

@app.delete("/tasks/{task_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def remove_task(task_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_task(db=db, task_id=task_id)
    if not deleted:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")
    return None

@app.post("/tasks/{task_id}/process", status_code=http_status.HTTP_202_ACCEPTED)
async def start_task_processing(task_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    db_task = await crud.get_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")
    if db_task.status == TaskStatus.IN_PROGRESS:
         raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Task is already {db_task.status.value}")
    elif db_task.status == TaskStatus.COMPLETED:
         raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Task is already {db_task.status.value}")

    background_tasks.add_task(process_task_in_background, task_id)
    await crud.create_task_log(db, task_id=task_id, status_message="Task processing initiated in background.")
    return {"message": "Task processing started in the background."}

@app.get("/tasks/{task_id}/logs", response_model=List[schemas.TaskLog])
async def read_task_logs(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    db_task = await crud.get_task(db=db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Task not found")

    skip = (page - 1) * size
    logs = await crud.get_task_logs(db, task_id=task_id, skip=skip, limit=size)
    return logs
