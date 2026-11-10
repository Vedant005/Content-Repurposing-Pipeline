import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from src.core.config import settings

logger = logging.getLogger("repurpose_api.redis")

_redis_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.REDIS_URL)


async def get_redis_pool() -> ArqRedis:
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = await create_pool(get_redis_settings())
            logger.info("Connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            logger.warning("Could not connect to Redis: %s", e)
            raise
    return _redis_pool


async def close_redis_pool() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Closed Redis connection pool.")
