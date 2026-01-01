from typing import AsyncGenerator
from infrastructure.database import get_session

async def get_session_dep() -> AsyncGenerator:
    async with get_session() as session:
        yield session




# in file ro kollan motavajeh nistam . . . 