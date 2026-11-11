import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from src.core.config import settings

connect_args = {"statement_cache_size": 0}
if settings.DB_SSL is True:
    connect_args["ssl"] = "require"
elif settings.DB_SSL is False:
    pass
else:
    is_local_or_docker = any(
        host in settings.DATABASE_URL.lower()
        for host in ["localhost", "127.0.0.1", "@postgres", "@db", "host.docker.internal"]
    )
    if not is_local_or_docker and "sslmode=disable" not in settings.DATABASE_URL.lower():
        connect_args["ssl"] = "require"

is_testing = "pytest" in sys.modules or os.environ.get("ENV") == "test"
poolclass = NullPool if is_testing else AsyncAdaptedQueuePool

engine_kwargs = {"connect_args": connect_args, "echo": False, "poolclass": poolclass}
if not is_testing:
    engine_kwargs.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
