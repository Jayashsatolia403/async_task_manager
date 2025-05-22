from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
from app.database import Base
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Task(Base): # type: ignore
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLAlchemyEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Integer, nullable=False, default=1) # Higher number means higher priority
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class TaskLog(Base): # type: ignore
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    status = Column(String(50), nullable=False) # Can store old status or new status or a message
    created_at = Column(TIMESTAMP, server_default=func.now())