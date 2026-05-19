import asyncio
import json
import logging
from datetime import datetime

from .config import SYMBOLS, ANALYSIS_INTERVAL, ALERT_COOLDOWN
from .data_fetcher import get_klines, get_fear_greed
from .analyzer import analyze
from .telegram_bot import send_alert
from .database import save_alert
from .redis_client import get_redis, publish

logger = logging.getLogger(__name__)

_running = False
_task = None


def is_running() -> bool:
    return _running


async def start_engine():
    global _running, _task
    if _running:
        return {"success": False, "message": "Already running"}
    _running = True
    _task = asyncio.create_task(_analysis_loop())
    logger.info("Analysis engine started")
    return {"success": True, "message": "Engine started"}


async def stop_engine():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        _task = None
    logger.info("Analysis engine stopped")
    return {"success": True, "message": "Engine stopped"}


async def _cooldown_ok(symbol: str, alert_type: str) -> bool:
    redis = await get_redis()
    key = f"cooldown:{symbol}:{alert_type}"
    if await redis.exists(key):
        return False
    await redis.setex(key, ALERT_COOLDOWN, "1")
    return True


def _build_messages(analysis: dict) -> dict[str, str]:
    sym = analysis["symbol"]
    price = analysis["price"]
    rsi = analysis.get("rsi") or 0
    vol_ratio = analysis.get("volume_spike", {}).get("ratio", 1)
    sup = analysis.get("support", 0)
    res = analysis.get("resistance", 0)

    return {
        "RSI_OVERSOLD": (
            f"🟢 <b>RSI OVERSOLD</b>\n"
            f"Coin: {sym}\nRSI: {rsi:.1f}\nHarga: ${price:,.4f}\n"
            f"📈 Potensi area bounce"
        ),
        "RSI_OVERBOUGHT": (
            f"🔴 <b>RSI OVERBOUGHT</b>\n"
            f"Coin: {sym}\nRSI: {rsi:.1f}\nHarga: ${price:,.4f}\n"
            f"📉 Potensi area reversal"
        ),
        "MACD_BULLISH": (
            f"📈 <b>MACD BULLISH CROSSOVER</b>\n"
            f"Coin: {sym}\nHarga: ${price:,.4f}\nMACD crossed ABOVE signal"
        ),
        "MACD_BEARISH": (
            f"📉 <b>MACD BEARISH CROSSOVER</b>\n"
            f"Coin: {sym}\nHarga: ${price:,.4f}\nMACD crossed BELOW signal"
        ),
        "VOLUME_SPIKE": (
            f"🚨 <b>VOLUME SPIKE</b>\n"
            f"Coin: {sym}\nHarga: ${price:,.4f}\nVolume: {vol_ratio}x rata-rata"
        ),
        "NEAR_SUPPORT": (
            f"🛡 <b>MENDEKATI SUPPORT</b>\n"
            f"Coin: {sym}\nHarga: ${price:,.4f}\nSupport: ${sup:,.4f}"
        ),
        "NEAR_RESISTANCE": (
            f"⚠️ <b>MENDEKATI RESISTANCE</b>\n"
            f"Coin: {sym}\nHarga: ${price:,.4f}\nResistance: ${res:,.4f}"
        ),
    }


async def _process_alerts(analysis: dict):
    sym = analysis["symbol"]
    price = analysis["price"]
    rsi = analysis.get("rsi")
    messages = _build_messages(analysis)

    for signal in analysis.get("signals", []):
        if signal not in messages:
            continue
        if not await _cooldown_ok(sym, signal):
            continue
        msg = messages[signal]
        await send_alert(msg)
        await save_alert({
            "symbol": sym,
            "alert_type": signal,
            "message": msg,
            "price": price,
            "rsi": rsi,
        })
        logger.info(f"Alert fired: {sym} {signal}")

    fear_greed = analysis.get("fear_greed", {})
    if sym == "BTCUSDT" and fear_greed:
        fg = fear_greed.get("value", 50)
        if fg <= 20 and await _cooldown_ok("GLOBAL", "EXTREME_FEAR"):
            msg = (
                f"😱 <b>EXTREME FEAR</b>\n"
                f"Fear & Greed Index: {fg} — {fear_greed.get('label', '')}\n"
                f"Secara historis ini area beli yang bagus"
            )
            await send_alert(msg)
        elif fg >= 80 and await _cooldown_ok("GLOBAL", "EXTREME_GREED"):
            msg = (
                f"🤑 <b>EXTREME GREED</b>\n"
                f"Fear & Greed Index: {fg} — {fear_greed.get('label', '')}\n"
                f"Pasar mungkin sudah terlalu panas"
            )
            await send_alert(msg)


async def _analysis_loop():
    global _running
    fear_greed = {"value": 50, "label": "Neutral"}
    cycle = 0

    while _running:
        try:
            if cycle % 5 == 0:
                fear_greed = await get_fear_greed()
            cycle += 1

            all_analysis = []
            for symbol in SYMBOLS:
                try:
                    klines = await get_klines(symbol, interval="1h", limit=100)
                    if not klines:
                        logger.warning(f"No klines for {symbol}")
                        continue
                    result = analyze(symbol, klines, fear_greed)
                    all_analysis.append(result)
                    await _process_alerts(result)
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")

            state = {
                "bot_status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "fear_greed": fear_greed,
                "symbols": all_analysis,
            }
            await publish("trading:updates", json.dumps(state))
            redis = await get_redis()
            await redis.setex("analysis:state", ANALYSIS_INTERVAL * 2, json.dumps(state))

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")

        await asyncio.sleep(ANALYSIS_INTERVAL)

    _running = False
