import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import update_task, create_task_log
from app.schemas import TaskUpdate
from app.models import TaskStatus
from app.database import AsyncSessionLocal

async def simulate_long_task_processing(task_id: int, duration: int = 5):
    print(f"Background: Starting processing for task {task_id}")
    await asyncio.sleep(duration) # Simulate work
    print(f"Background: Finished processing for task {task_id}")


async def process_task_in_background(task_id: int):
    db: AsyncSession = AsyncSessionLocal()
    try:
        print(f"Background Task: Attempting to set task {task_id} to IN_PROGRESS")
        # Update status to IN_PROGRESS
        updated_task = await update_task(db, task_id, TaskUpdate(status=TaskStatus.IN_PROGRESS))
        if not updated_task:
            print(f"Background Task: Task {task_id} not found for processing.")
            return

        # Simulate the actual long-running work
        await simulate_long_task_processing(task_id, duration=10) # 10 seconds

        # Update status to COMPLETED
        print(f"Background Task: Attempting to set task {task_id} to COMPLETED")
        await update_task(db, task_id, TaskUpdate(status=TaskStatus.COMPLETED))
        print(f"Background Task: Task {task_id} marked as COMPLETED.")

    except Exception as e:
        print(f"Background Task: Error processing task {task_id}: {e}")
        await create_task_log(db, task_id=task_id, status_message=f"Error during background processing: {str(e)}")
    finally:
        await db.close()