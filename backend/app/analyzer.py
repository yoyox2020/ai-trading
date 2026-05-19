import numpy as np
from typing import Optional


def calculate_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    return round(100.0 - 100.0 / (1.0 + avg_gain / avg_loss), 2)


def calculate_macd(closes: list[float], fast=12, slow=26, signal_period=9) -> Optional[dict]:
    if len(closes) < slow + signal_period:
        return None
    arr = np.array(closes, dtype=float)

    def ema(data: np.ndarray, period: int) -> np.ndarray:
        k = 2.0 / (period + 1)
        out = np.empty_like(data)
        out[0] = data[0]
        for i in range(1, len(data)):
            out[i] = data[i] * k + out[i - 1] * (1 - k)
        return out

    macd_line = ema(arr, fast) - ema(arr, slow)
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return {
        "macd": round(float(macd_line[-1]), 6),
        "signal": round(float(signal_line[-1]), 6),
        "histogram": round(float(histogram[-1]), 6),
        "macd_prev": round(float(macd_line[-2]), 6),
        "signal_prev": round(float(signal_line[-2]), 6),
    }


def detect_volume_spike(volumes: list[float], window: int = 20) -> dict:
    if len(volumes) < window + 1:
        return {"spike": False, "ratio": 1.0}
    avg = float(np.mean(volumes[-window - 1:-1]))
    ratio = round(volumes[-1] / avg, 2) if avg > 0 else 1.0
    return {"spike": ratio >= 2.0, "ratio": ratio}


def find_support_resistance(highs: list[float], lows: list[float], closes: list[float], window: int = 5) -> dict:
    current = closes[-1]
    if len(closes) < window * 3:
        return {"support": round(current * 0.97, 6), "resistance": round(current * 1.03, 6)}

    local_highs, local_lows = [], []
    for i in range(window, len(closes) - window):
        if highs[i] == max(highs[i - window:i + window + 1]):
            local_highs.append(highs[i])
        if lows[i] == min(lows[i - window:i + window + 1]):
            local_lows.append(lows[i])

    supports = [l for l in local_lows if l < current]
    resistances = [h for h in local_highs if h > current]

    return {
        "support": round(max(supports) if supports else current * 0.97, 6),
        "resistance": round(min(resistances) if resistances else current * 1.03, 6),
    }


def analyze(symbol: str, klines: list[dict], fear_greed: dict) -> dict:
    if not klines:
        return {"symbol": symbol, "error": "No data"}

    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    volumes = [k["volume"] for k in klines]

    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    vol_spike = detect_volume_spike(volumes)
    sr = find_support_resistance(highs, lows, closes)

    current_price = closes[-1]
    price_change_pct = round((current_price - closes[-2]) / closes[-2] * 100, 2) if len(closes) > 1 else 0.0

    signals = []
    if rsi is not None:
        if rsi < 30:
            signals.append("RSI_OVERSOLD")
        elif rsi > 70:
            signals.append("RSI_OVERBOUGHT")

    if macd:
        if macd["macd_prev"] < macd["signal_prev"] and macd["macd"] > macd["signal"]:
            signals.append("MACD_BULLISH")
        elif macd["macd_prev"] > macd["signal_prev"] and macd["macd"] < macd["signal"]:
            signals.append("MACD_BEARISH")

    if vol_spike["spike"]:
        signals.append("VOLUME_SPIKE")

    if sr["support"] > 0 and abs(current_price - sr["support"]) / current_price <= 0.01:
        signals.append("NEAR_SUPPORT")
    if sr["resistance"] > 0 and abs(sr["resistance"] - current_price) / current_price <= 0.01:
        signals.append("NEAR_RESISTANCE")

    return {
        "symbol": symbol,
        "price": round(current_price, 6),
        "price_change_pct": price_change_pct,
        "volume": round(volumes[-1], 2),
        "rsi": rsi,
        "macd": macd,
        "volume_spike": vol_spike,
        "support": sr["support"],
        "resistance": sr["resistance"],
        "fear_greed": fear_greed,
        "signals": signals,
    }
