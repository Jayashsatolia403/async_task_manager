from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import  func

from app.models import Task, TaskLog, TaskStatus
from app.schemas import TaskCreate, TaskUpdate, TaskLogCreate
from typing import List, Optional, Tuple

async def create_task_log(db: AsyncSession, task_id: int, status_message: str):
    db_task_log = TaskLog(task_id=task_id, status=status_message)
    db.add(db_task_log)
    await db.commit()
    await db.refresh(db_task_log)
    return db_task_log

async def create_task(db: AsyncSession, task: TaskCreate) -> Task:
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    await create_task_log(db, task_id=db_task.id, status_message=f"Task created with status {db_task.status.value}")
    return db_task

async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()

async def get_tasks(
    db: AsyncSession, skip: int = 0, limit: int = 10, title: Optional[str] = None, status: Optional[TaskStatus] = None
) -> Tuple[List[Task], int]:
    query = select(Task).order_by(Task.priority.desc(), Task.created_at.desc())
    count_query = select(func.count()).select_from(Task)

    if title:
        query = query.where(Task.title.ilike(f"%{title}%"))
        count_query = count_query.where(Task.title.ilike(f"%{title}%"))
    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    total_count_result = await db.execute(count_query)
    total = total_count_result.scalar_one()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return list(tasks), total


async def update_task(db: AsyncSession, task_id: int, task_update_data: TaskUpdate) -> Optional[Task]:
    db_task = await get_task(db, task_id)
    if not db_task:
        return None

    old_status = db_task.status
    update_data = task_update_data.model_dump(exclude_unset=True)

    if not update_data: # No fields to update
        return db_task

    for key, value in update_data.items():
        setattr(db_task, key, value)

    await db.commit()
    await db.refresh(db_task)

    if "status" in update_data and old_status != db_task.status:
        await create_task_log(db, task_id=db_task.id, status_message=f"Status changed from {old_status.value} to {db_task.status.value}")
    elif update_data: # Log general update if not status change
         await create_task_log(db, task_id=db_task.id, status_message=f"Task details updated.")

    return db_task

async def delete_task(db: AsyncSession, task_id: int) -> bool:
    db_task = await get_task(db, task_id)
    if not db_task:
        return False
    # TaskLogs are deleted by CASCADE on foreign key
    await db.delete(db_task)
    await db.commit()
    return True

async def get_task_logs(db: AsyncSession, task_id: int, skip: int = 0, limit: int = 10) -> List[TaskLog]:
    result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())