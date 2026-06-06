import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

DATABASE_URL_ASYNC = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

if os.getenv("TESTING", "false").lower() == "true":
    pool_kwargs = {"poolclass": NullPool}
else:
    pool_kwargs = {
        "pool_size": 50,           
        "max_overflow": 50,        
        "pool_pre_ping": True,
        "pool_timeout": 60,        
        "pool_recycle": 3600,      
    }

async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    future=True,
    **pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()