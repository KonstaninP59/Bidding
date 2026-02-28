import aioredis
import os
from fastapi import HTTPException

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

RATE_LIMIT = 20  # запросов
WINDOW = 60  # секунд


async def check_rate_limit(key: str):
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, WINDOW)

    if current > RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests")
