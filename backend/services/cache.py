"""
EduGenAI - Redis In-Memory Cache & Job State Service
Provides sub-millisecond caching for LLM generation, quizzes, and live render progress.
Includes automated in-memory fallback if Redis server is unreachable.
"""
import json
import logging
import time
from typing import Any, Optional
import redis.asyncio as aioredis
from config import REDIS_URL

logger = logging.getLogger("EduGenAI.Cache")

_redis_client: Optional[aioredis.Redis] = None
_redis_available: bool = False
_local_memory_cache: dict[str, tuple[float, Any]] = {}  # {key: (expiry_timestamp, value)}


async def init_redis() -> bool:
    """Initialize Redis connection and test ping."""
    global _redis_client, _redis_available
    try:
        _redis_client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await _redis_client.ping()
        _redis_available = True
        logger.info(f"⚡ Redis Cache connected successfully at {REDIS_URL}")
        return True
    except Exception as e:
        _redis_available = False
        logger.info(f"ℹ️ Redis not reachable ({e}). Using ultra-fast in-memory fallback cache.")
        return False


def make_cache_key(prefix: str, *args: Any) -> str:
    """Construct a clean, normalized cache key."""
    parts = [prefix] + [str(a).strip().lower().replace(" ", "_") for a in args if a]
    return ":".join(parts)


async def get_cached_json(key: str) -> Optional[dict | list]:
    """Retrieve and deserialize JSON data from Redis or in-memory cache."""
    global _redis_client, _redis_available

    # 1. Try Redis
    if _redis_available and _redis_client is not None:
        try:
            val = await _redis_client.get(key)
            if val:
                logger.info(f"🎯 Redis Cache HIT: {key}")
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")

    # 2. Fallback to Local In-Memory Cache
    if key in _local_memory_cache:
        expiry, val = _local_memory_cache[key]
        if time.time() < expiry:
            logger.info(f"🎯 In-Memory Cache HIT: {key}")
            return val
        else:
            del _local_memory_cache[key]

    return None


async def set_cached_json(key: str, data: Any, ttl_seconds: int = 86400) -> None:
    """Store JSON data in Redis (default TTL: 24 hours)."""
    global _redis_client, _redis_available

    # 1. Store in Redis
    if _redis_available and _redis_client is not None:
        try:
            serialized = json.dumps(data, default=str)
            await _redis_client.setex(key, ttl_seconds, serialized)
            logger.info(f"💾 Redis Cache SET: {key} (TTL: {ttl_seconds}s)")
            return
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")

    # 2. Fallback to Local In-Memory Cache
    _local_memory_cache[key] = (time.time() + ttl_seconds, data)


# ── Live Generation Progress Tracking ────────────────────────

async def set_job_progress(job_id: str, percent: int, step_message: str) -> None:
    """Update live video generation progress in Redis."""
    key = f"job_progress:{job_id}"
    progress_data = {
        "job_id": job_id,
        "progress": percent,
        "step": step_message,
        "updated_at": time.time(),
    }
    await set_cached_json(key, progress_data, ttl_seconds=3600)


async def get_job_progress(job_id: str) -> Optional[dict]:
    """Get live video generation progress from Redis."""
    key = f"job_progress:{job_id}"
    return await get_cached_json(key)
