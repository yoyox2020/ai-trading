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
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                price DECIMAL(20, 8) NOT NULL,
                quantity DECIMAL(20, 8) NOT NULL,
                stop_loss DECIMAL(20, 8),
                take_profit DECIMAL(20, 8),
                pnl DECIMAL(20, 8) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'open',
                order_id VARCHAR(100)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                start_date TIMESTAMPTZ NOT NULL,
                end_date TIMESTAMPTZ NOT NULL,
                initial_balance DECIMAL(20, 8) NOT NULL,
                final_balance DECIMAL(20, 8) NOT NULL,
                total_trades INT DEFAULT 0,
                winning_trades INT DEFAULT 0,
                losing_trades INT DEFAULT 0,
                profit_loss DECIMAL(20, 8) DEFAULT 0,
                win_rate DECIMAL(5, 2) DEFAULT 0,
                max_drawdown DECIMAL(5, 2) DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    logger.info("Database tables ready")


async def save_trade(trade: dict) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO trades (symbol, side, price, quantity, stop_loss, take_profit, order_id, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            trade["symbol"], trade["side"],
            float(trade["price"]), float(trade["quantity"]),
            float(trade["stop_loss"]) if trade.get("stop_loss") else None,
            float(trade["take_profit"]) if trade.get("take_profit") else None,
            trade.get("order_id", "demo"),
            trade.get("status", "open")
        )
        return row["id"]


async def get_recent_trades(limit: int = 50) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, timestamp, symbol, side, price, quantity,
                   stop_loss, take_profit, pnl, status, order_id
            FROM trades ORDER BY timestamp DESC LIMIT $1
        """, limit)
        result = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
                elif v is not None:
                    r[k] = float(v) if k in ('price', 'quantity', 'stop_loss', 'take_profit', 'pnl') else v
            result.append(r)
        return result


async def save_backtest_result(result: dict) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO backtest_results
            (symbol, start_date, end_date, initial_balance, final_balance,
             total_trades, winning_trades, losing_trades, profit_loss, win_rate, max_drawdown)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """,
            result["symbol"], result["start_date"], result["end_date"],
            float(result["initial_balance"]), float(result["final_balance"]),
            int(result["total_trades"]), int(result["winning_trades"]),
            int(result["losing_trades"]), float(result["profit_loss"]),
            float(result["win_rate"]), float(result["max_drawdown"])
        )
        return row["id"]


async def close():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
