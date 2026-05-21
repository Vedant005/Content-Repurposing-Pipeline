from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,

    # Connection pool settings
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,

    connect_args={
        "ssl": "require",
        "statement_cache_size": 0,
    },
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session