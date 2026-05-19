import httpx
import logging

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://api.binance.com"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"


async def get_klines(symbol: str, interval: str = "1h", limit: int = 100) -> list[dict]:
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        try:
            r = await client.get(
                f"{BINANCE_BASE}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
            )
            return [
                {
                    "open_time": c[0],
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                }
                for c in r.json()
            ]
        except Exception as e:
            logger.error(f"get_klines {symbol} error: {e}")
    return []


async def get_fear_greed() -> dict:
    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        try:
            r = await client.get(FEAR_GREED_URL)
            item = r.json()["data"][0]
            return {"value": int(item["value"]), "label": item["value_classification"]}
        except Exception as e:
            logger.error(f"get_fear_greed error: {e}")
    return {"value": 50, "label": "Neutral"}
