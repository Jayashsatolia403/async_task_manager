from sqlalchemy.orm import declarative_base
import os
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/task_manager")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(3),
    retry=retry_if_exception_type(OperationalError),
    reraise=True,
)
async def init_db_connection():
    try:
        async with engine.connect() as connection:
            print("Database connection successful.")
    except OperationalError as e:
        print(f"Database connection failed: {e}. Retrying...")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during DB connection: {e}")
        raise

async def close_db_connection():
    await engine.dispose()