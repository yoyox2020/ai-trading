import os
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "true").lower() == "true"

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
TRADING_INTERVAL = int(os.getenv("TRADING_INTERVAL", "60"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:tradingpass@postgres:5432/trading")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Risk parameters (from README)
RISK_PER_TRADE = 0.02       # 2% of balance
STOP_LOSS_PERCENT = 0.02    # 2% SL
TAKE_PROFIT_PERCENT = 0.04  # 4% TP
MAX_POSITIONS = 3

# RSI settings
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# MACD settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL_PERIOD = 9

DEMO_MODE = not bool(BYBIT_API_KEY and BYBIT_API_SECRET)
DEMO_BALANCE = 10000.0
