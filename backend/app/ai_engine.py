from typing import Optional
import pandas as pd
from .config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL_PERIOD,
)


def calculate_rsi(prices: list[float], period: int = RSI_PERIOD) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def calculate_macd(prices: list[float]) -> dict:
    empty = {"macd": None, "signal": None, "histogram": None, "prev_histogram": None}
    if len(prices) < MACD_SLOW + MACD_SIGNAL_PERIOD:
        return empty
    s = pd.Series(prices)
    ema_fast = s.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = s.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "histogram": float(histogram.iloc[-1]),
        "prev_histogram": float(histogram.iloc[-2]) if len(histogram) >= 2 else 0.0,
    }


def generate_signal(prices: list[float]) -> dict:
    rsi = calculate_rsi(prices)
    macd_data = calculate_macd(prices)

    if rsi is None or macd_data["macd"] is None:
        return {
            "signal": "HOLD",
            "rsi": rsi,
            "macd": macd_data,
            "reason": "Insufficient data",
        }

    reasons: list[str] = []

    # RSI direction
    rsi_dir = "HOLD"
    if rsi < RSI_OVERSOLD:
        rsi_dir = "BUY"
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > RSI_OVERBOUGHT:
        rsi_dir = "SELL"
        reasons.append(f"RSI overbought ({rsi:.1f})")

    # MACD crossover
    macd_dir = "HOLD"
    hist = macd_data["histogram"]
    prev_hist = macd_data["prev_histogram"]
    if hist is not None and prev_hist is not None:
        if hist > 0 and prev_hist <= 0:
            macd_dir = "BUY"
            reasons.append("MACD bullish crossover")
        elif hist < 0 and prev_hist >= 0:
            macd_dir = "SELL"
            reasons.append("MACD bearish crossover")

    # Combine: both must agree or one is neutral
    if rsi_dir == "BUY" and macd_dir in ("BUY", "HOLD"):
        signal = "BUY"
    elif rsi_dir == "SELL" and macd_dir in ("SELL", "HOLD"):
        signal = "SELL"
    elif macd_dir == "BUY" and rsi_dir == "HOLD":
        signal = "BUY"
    elif macd_dir == "SELL" and rsi_dir == "HOLD":
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "signal": signal,
        "rsi": round(rsi, 2),
        "macd": {
            "macd": round(macd_data["macd"], 6),
            "signal": round(macd_data["signal"], 6),
            "histogram": round(hist, 6),
        },
        "reason": " | ".join(reasons) if reasons else "No clear signal",
    }
