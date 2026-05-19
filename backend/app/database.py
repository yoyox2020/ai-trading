import asyncio
import asyncpg
import logging
from typing import Optional
from .config import DATABASE_URL

logger = logging.getLogger(__name__)
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        for attempt in range(10):
            try:
                _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
                logger.info("Database connected")
                break
            except Exception as e:
                logger.warning(f"DB connection attempt {attempt+1}/10 failed: {e}")
                await asyncio.sleep(3)
        if _pool is None:
            raise RuntimeError("Could not connect to database")
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                symbol VARCHAR(20) NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                price DECIMAL(20, 8),
                rsi DECIMAL(8, 4)
            )
        """)
    logger.info("Database tables ready")


async def save_alert(alert: dict) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO alerts (symbol, alert_type, message, price, rsi)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """,
            alert["symbol"],
            alert["alert_type"],
            alert["message"],
            float(alert["price"]) if alert.get("price") else None,
            float(alert["rsi"]) if alert.get("rsi") else None,
        )
        return row["id"]


async def get_recent_alerts(limit: int = 50) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, timestamp, symbol, alert_type, message, price, rsi
            FROM alerts ORDER BY timestamp DESC LIMIT $1
        """, limit)
        result = []
        for row in rows:
            r = dict(row)
            r["timestamp"] = r["timestamp"].isoformat()
            if r["price"] is not None:
                r["price"] = float(r["price"])
            if r["rsi"] is not None:
                r["rsi"] = float(r["rsi"])
            result.append(r)
        return result


async def close():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
