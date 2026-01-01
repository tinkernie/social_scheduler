import os
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, create_engine
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio.engine import create_async_engine, AsyncEngine


DATABASE_URL = os.getenv("DATABASE_URL")

# engine = create_async_engine(DATABASE_URL, echo=False)
engine: AsyncEngine = create_engine(DATABASE_URL, echo=False)


async def init_db():
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

    except Exception as e:
        print(f"an error accured during creation of the db tables : {e}")


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSession(engine) as session:
        yield session
