import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from .config import REDIS_URL

logger = logging.getLogger(__name__)
_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _client


async def set_value(key: str, value: Any, expire: int = None):
    r = await get_redis()
    data = json.dumps(value) if not isinstance(value, str) else value
    try:
        if expire:
            await r.setex(key, expire, data)
        else:
            await r.set(key, data)
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


async def get_value(key: str) -> Optional[Any]:
    r = await get_redis()
    try:
        data = await r.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
        return None


async def publish(channel: str, message: Any):
    r = await get_redis()
    data = json.dumps(message) if not isinstance(message, str) else message
    try:
        await r.publish(channel, data)
    except Exception as e:
        logger.warning(f"Redis publish error: {e}")


async def close():
    global _client
    if _client:
        await _client.aclose()
        _client = None
