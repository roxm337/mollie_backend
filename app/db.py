from sqlmodel import create_engine, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from .config import settings

DATABASE_URL = settings.database_url

# async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# helper to create tables (call at startup)
async def init_db():
    async with engine.begin() as conn:
        # if you prefer migrations, run alembic instead
        await conn.run_sync(SQLModel.metadata.create_all)

