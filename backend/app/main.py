import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import SYMBOLS
from .database import init_db, get_recent_alerts, close as close_db
from .redis_client import get_redis, get_value, close as close_redis
from .alert_engine import start_engine, stop_engine, is_running

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
    logger.info(f"App ready — monitoring {SYMBOLS}")
    yield
    await stop_engine()
    await close_db()
    await close_redis()


app = FastAPI(title="Crypto Analysis Bot", version="2.0.0", lifespan=lifespan)


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
    state = await get_value("analysis:state")
    if state:
        await websocket.send_text(json.dumps(state) if not isinstance(state, str) else state)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


@app.get("/api/status")
async def api_status():
    return {
        "running": is_running(),
        "symbols": SYMBOLS,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/analysis")
async def api_analysis():
    state = await get_value("analysis:state") or {}
    return state


@app.get("/api/alerts")
async def api_alerts():
    alerts = await get_recent_alerts(50)
    return {"alerts": alerts}


@app.post("/api/start")
async def api_start():
    return await start_engine()


@app.post("/api/stop")
async def api_stop():
    return await stop_engine()


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("/app/frontend/index.html")
