import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import SYMBOL, DEMO_MODE
from .database import init_db, get_recent_trades
from .redis_client import get_redis, get_value, close as close_redis
from .trading import start_bot, stop_bot, is_running
from .backtest import run_backtest
from .bybit_client import get_ticker_price, get_klines

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_ws_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(_redis_broadcast())
    logger.info(f"App ready — demo_mode={DEMO_MODE} symbol={SYMBOL}")
    yield
    await stop_bot()
    await close_redis()


app = FastAPI(title="AI Trading Bot", version="1.0.0", lifespan=lifespan)


# ── WebSocket broadcast via Redis pub/sub ───────────────────────────────────

async def _redis_broadcast():
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("trading:updates")
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        raw = message["data"]
        if not isinstance(raw, str):
            continue
        dead = []
        for ws in list(_ws_clients):
            try:
                await ws.send_text(raw)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in _ws_clients:
                _ws_clients.remove(ws)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    # push current state immediately so the dashboard loads fast
    state = await get_value("trading:state")
    if state:
        await websocket.send_text(json.dumps(state))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


# ── REST endpoints ───────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    state = await get_value("trading:state") or {}
    return {
        "bot_running": is_running(),
        "demo_mode": DEMO_MODE,
        "symbol": SYMBOL,
        "current_price": state.get("price"),
        "signal": state.get("signal", "HOLD"),
        "balance": state.get("balance"),
        "last_update": state.get("timestamp"),
    }


@app.get("/api/price")
async def api_price():
    price = await get_ticker_price(SYMBOL)
    return {"symbol": SYMBOL, "price": price, "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/price-history")
async def api_price_history(interval: str = "1", limit: int = 100):
    prices = await get_klines(SYMBOL, interval=interval, limit=limit)
    return {"symbol": SYMBOL, "prices": prices, "interval": interval}


@app.get("/api/trades")
async def api_trades():
    trades = await get_recent_trades(50)
    return {"trades": trades}


@app.get("/api/positions")
async def api_positions():
    positions = await get_value("trading:positions") or []
    return {"positions": positions}


@app.post("/api/start")
async def api_start():
    return await start_bot()


@app.post("/api/stop")
async def api_stop():
    return await stop_bot()


@app.post("/api/backtest")
async def api_backtest(symbol: str = SYMBOL, initial_balance: float = 10000.0, interval: str = "60"):
    result = await run_backtest(symbol, initial_balance, lookback=500, interval=interval)
    return result


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Serve frontend ───────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("/app/frontend/index.html")
