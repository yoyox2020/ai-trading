import hashlib
import hmac
import json
import logging
import time
from typing import Optional
import httpx
from .config import BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_TESTNET, DEMO_MODE, DEMO_BALANCE

logger = logging.getLogger(__name__)

BASE_URL = "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"


def _sign(params_str: str) -> tuple[str, str, str]:
    ts = str(int(time.time() * 1000))
    recv_window = "5000"
    raw = f"{ts}{BYBIT_API_KEY}{recv_window}{params_str}"
    sig = hmac.new(
        BYBIT_API_SECRET.encode(),
        raw.encode(),
        hashlib.sha256
    ).hexdigest()
    return ts, recv_window, sig


def _auth_headers(params_str: str) -> dict:
    ts, rw, sig = _sign(params_str)
    return {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-SIGN": sig,
        "X-BAPI-RECV-WINDOW": rw,
    }


async def get_ticker_price(symbol: str) -> Optional[float]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                f"{BASE_URL}/v5/market/tickers",
                params={"category": "spot", "symbol": symbol}
            )
            data = r.json()
            if data["retCode"] == 0 and data["result"]["list"]:
                return float(data["result"]["list"][0]["lastPrice"])
        except Exception as e:
            logger.error(f"get_ticker_price error: {e}")
    return None


async def get_klines(symbol: str, interval: str = "1", limit: int = 200) -> list[float]:
    """Return list of close prices, oldest first."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                f"{BASE_URL}/v5/market/kline",
                params={"category": "spot", "symbol": symbol, "interval": interval, "limit": limit}
            )
            data = r.json()
            if data["retCode"] == 0:
                # each candle: [timestamp, open, high, low, close, volume, turnover]
                candles = data["result"]["list"]
                return [float(c[4]) for c in reversed(candles)]
        except Exception as e:
            logger.error(f"get_klines error: {e}")
    return []


async def get_wallet_balance() -> float:
    if DEMO_MODE:
        return DEMO_BALANCE

    params_str = "accountType=UNIFIED"
    headers = _auth_headers(params_str)
    headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                f"{BASE_URL}/v5/account/wallet-balance",
                params={"accountType": "UNIFIED"},
                headers=headers
            )
            data = r.json()
            if data["retCode"] == 0:
                accounts = data["result"]["list"]
                if accounts:
                    return float(accounts[0]["totalWalletBalance"])
        except Exception as e:
            logger.error(f"get_wallet_balance error: {e}")
    return DEMO_BALANCE


async def place_order(
    symbol: str,
    side: str,
    qty: float,
    stop_loss: float = None,
    take_profit: float = None,
) -> dict:
    if DEMO_MODE:
        logger.info(f"[DEMO] {side} {qty} {symbol} SL={stop_loss} TP={take_profit}")
        return {"success": True, "order_id": f"demo_{int(time.time())}"}

    body = {
        "category": "spot",
        "symbol": symbol,
        "side": side.capitalize(),
        "orderType": "Market",
        "qty": str(round(qty, 6)),
    }
    if stop_loss:
        body["stopLoss"] = str(stop_loss)
    if take_profit:
        body["takeProfit"] = str(take_profit)

    body_str = json.dumps(body)
    headers = _auth_headers(body_str)
    headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(
                f"{BASE_URL}/v5/order/create",
                content=body_str,
                headers=headers
            )
            data = r.json()
            if data["retCode"] == 0:
                return {"success": True, "order_id": data["result"]["orderId"]}
            return {"success": False, "reason": data.get("retMsg", "Unknown error")}
        except Exception as e:
            logger.error(f"place_order error: {e}")
            return {"success": False, "reason": str(e)}
