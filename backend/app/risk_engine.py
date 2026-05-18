from .config import RISK_PER_TRADE, STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT, MAX_POSITIONS


def calculate_position_size(balance: float, price: float, risk_pct: float = RISK_PER_TRADE) -> float:
    """Max loss per trade = risk_pct * balance; SL distance = SL_PERCENT * price."""
    risk_amount = balance * risk_pct
    sl_distance = price * STOP_LOSS_PERCENT
    qty = risk_amount / sl_distance
    return round(max(qty, 0.000001), 6)


def calculate_stop_loss(price: float, side: str) -> float:
    if side == "BUY":
        return round(price * (1 - STOP_LOSS_PERCENT), 2)
    return round(price * (1 + STOP_LOSS_PERCENT), 2)


def calculate_take_profit(price: float, side: str) -> float:
    if side == "BUY":
        return round(price * (1 + TAKE_PROFIT_PERCENT), 2)
    return round(price * (1 - TAKE_PROFIT_PERCENT), 2)


def validate_trade(
    balance: float,
    price: float,
    quantity: float,
    current_positions: int = 0,
) -> dict:
    if balance < 10:
        return {"valid": False, "reason": "Insufficient balance (< $10)"}

    if current_positions >= MAX_POSITIONS:
        return {"valid": False, "reason": f"Max {MAX_POSITIONS} open positions reached"}

    trade_value = price * quantity
    max_trade_value = balance * 0.20  # never risk more than 20% per trade
    if trade_value > max_trade_value:
        return {
            "valid": False,
            "reason": f"Trade value ${trade_value:.2f} > max ${max_trade_value:.2f}",
        }

    return {"valid": True, "reason": "Trade approved"}


def calculate_pnl(entry: float, exit_price: float, qty: float, side: str) -> float:
    if side == "BUY":
        return (exit_price - entry) * qty
    return (entry - exit_price) * qty
