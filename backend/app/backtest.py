import logging
from datetime import datetime, timedelta

from .bybit_client import get_klines
from .ai_engine import generate_signal
from .risk_engine import calculate_position_size, calculate_stop_loss, calculate_take_profit, calculate_pnl
from .database import save_backtest_result

logger = logging.getLogger(__name__)


async def run_backtest(
    symbol: str,
    initial_balance: float = 10000.0,
    lookback: int = 500,
    interval: str = "60",
) -> dict:
    prices = await get_klines(symbol, interval=interval, limit=lookback)

    if len(prices) < 60:
        return {"error": "Not enough historical data (need ≥60 candles)"}

    balance = initial_balance
    positions: list[dict] = []
    closed_trades: list[dict] = []
    peak = initial_balance
    max_dd = 0.0
    window = 50  # minimum candles needed for indicators

    for i in range(window, len(prices)):
        price = prices[i]
        window_prices = prices[: i + 1]

        # Check SL/TP on open positions
        still_open = []
        for pos in positions:
            hit = None
            if pos["side"] == "BUY":
                if price <= pos["sl"]:
                    hit = "SL"
                elif price >= pos["tp"]:
                    hit = "TP"
            else:
                if price >= pos["sl"]:
                    hit = "SL"
                elif price <= pos["tp"]:
                    hit = "TP"

            if hit:
                pnl = calculate_pnl(pos["entry"], price, pos["qty"], pos["side"])
                balance += pos["entry"] * pos["qty"] + pnl
                closed_trades.append({**pos, "exit": price, "pnl": pnl, "close": hit})
            else:
                still_open.append(pos)
        positions = still_open

        # Update max drawdown
        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak * 100
        if dd > max_dd:
            max_dd = dd

        # Generate signal and maybe open a position
        if len(positions) < 3:
            analysis = generate_signal(window_prices)
            sig = analysis["signal"]

            if sig in ("BUY", "SELL"):
                qty = calculate_position_size(balance, price)
                cost = price * qty
                if cost <= balance * 0.20 and cost <= balance:
                    balance -= cost
                    positions.append({
                        "side": sig,
                        "entry": price,
                        "qty": qty,
                        "sl": calculate_stop_loss(price, sig),
                        "tp": calculate_take_profit(price, sig),
                        "bar": i,
                    })

    # Close remaining positions at last price
    last = prices[-1]
    for pos in positions:
        pnl = calculate_pnl(pos["entry"], last, pos["qty"], pos["side"])
        balance += pos["entry"] * pos["qty"] + pnl
        closed_trades.append({**pos, "exit": last, "pnl": pnl, "close": "end"})

    winners = [t for t in closed_trades if t["pnl"] > 0]
    losers = [t for t in closed_trades if t["pnl"] <= 0]
    total_pnl = balance - initial_balance
    win_rate = len(winners) / len(closed_trades) * 100 if closed_trades else 0.0

    now = datetime.utcnow()
    result = {
        "symbol": symbol,
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "profit_loss": round(total_pnl, 2),
        "profit_loss_pct": round(total_pnl / initial_balance * 100, 2),
        "total_trades": len(closed_trades),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_dd, 2),
        "start_date": now - timedelta(minutes=int(interval) * lookback),
        "end_date": now,
        "candles_used": len(prices),
        "interval_minutes": int(interval),
    }

    try:
        await save_backtest_result(result)
    except Exception as e:
        logger.warning(f"Could not persist backtest result: {e}")

    # Return JSON-serialisable version
    result["start_date"] = result["start_date"].isoformat()
    result["end_date"] = result["end_date"].isoformat()
    return result
