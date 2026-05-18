import asyncio
import logging
from datetime import datetime
from typing import Optional

from .config import SYMBOL, TRADING_INTERVAL
from .bybit_client import get_ticker_price, get_klines, get_wallet_balance, place_order
from .ai_engine import generate_signal
from .risk_engine import calculate_position_size, calculate_stop_loss, calculate_take_profit, validate_trade
from .redis_client import set_value, get_value, publish
from .database import save_trade

logger = logging.getLogger(__name__)

_bot_running = False
_trading_task: Optional[asyncio.Task] = None


async def _trading_loop():
    global _bot_running
    logger.info(f"Bot started — symbol={SYMBOL} interval={TRADING_INTERVAL}s")

    while _bot_running:
        try:
            # Step 1: price
            price = await get_ticker_price(SYMBOL)
            if not price:
                await asyncio.sleep(10)
                continue

            # Step 2: OHLCV for indicators
            prices = await get_klines(SYMBOL, interval="1", limit=200)
            if len(prices) < 50:
                await asyncio.sleep(10)
                continue

            # Step 3: balance
            balance = await get_wallet_balance()

            # Step 4: AI signal
            analysis = generate_signal(prices)
            signal = analysis["signal"]

            # Step 5: build state snapshot
            state = {
                "price": price,
                "signal": signal,
                "rsi": analysis["rsi"],
                "macd": analysis["macd"],
                "reason": analysis["reason"],
                "balance": balance,
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": SYMBOL,
                "bot_status": "running",
            }

            # Step 6: cache + broadcast
            await set_value("trading:state", state, expire=300)
            await publish("trading:updates", state)

            # Step 7: execute if actionable
            if signal in ("BUY", "SELL"):
                open_positions = await get_value("trading:positions") or []
                pos_count = len(open_positions) if isinstance(open_positions, list) else 0
                qty = calculate_position_size(balance, price)
                check = validate_trade(balance, price, qty, current_positions=pos_count)

                if check["valid"]:
                    sl = calculate_stop_loss(price, signal)
                    tp = calculate_take_profit(price, signal)
                    order = await place_order(SYMBOL, signal, qty, sl, tp)

                    trade = {
                        "symbol": SYMBOL,
                        "side": signal,
                        "price": price,
                        "quantity": qty,
                        "stop_loss": sl,
                        "take_profit": tp,
                        "order_id": order.get("order_id", "demo"),
                        "status": "open" if order.get("success") else "failed",
                    }
                    await save_trade(trade)

                    positions = await get_value("trading:positions") or []
                    positions.append(trade)
                    await set_value("trading:positions", positions)

                    await publish("trading:updates", {**state, "trade_executed": trade})
                    logger.info(f"Trade: {signal} {qty} {SYMBOL} @ {price}")
                else:
                    logger.info(f"Trade skipped: {check['reason']}")

            await asyncio.sleep(TRADING_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Trading loop error: {e}", exc_info=True)
            await asyncio.sleep(30)

    logger.info("Bot stopped")


async def start_bot() -> dict:
    global _bot_running, _trading_task
    if _bot_running:
        return {"success": False, "message": "Bot already running"}
    _bot_running = True
    _trading_task = asyncio.create_task(_trading_loop())
    await set_value("trading:bot_status", "running")
    return {"success": True, "message": "Bot started"}


async def stop_bot() -> dict:
    global _bot_running, _trading_task
    if not _bot_running:
        return {"success": False, "message": "Bot not running"}
    _bot_running = False
    if _trading_task:
        _trading_task.cancel()
        try:
            await _trading_task
        except asyncio.CancelledError:
            pass
    await set_value("trading:bot_status", "stopped")
    return {"success": True, "message": "Bot stopped"}


def is_running() -> bool:
    return _bot_running
