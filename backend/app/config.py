import os
from dotenv import load_dotenv

load_dotenv()

SYMBOLS = os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,DOGEUSDT").split(",")
ANALYSIS_INTERVAL = int(os.getenv("ANALYSIS_INTERVAL", "60"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:tradingpass@postgres:5432/trading")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL_PERIOD = 9

VOLUME_SPIKE_THRESHOLD = 2.0
SR_PROXIMITY_PCT = 0.01
ALERT_COOLDOWN = 3600
