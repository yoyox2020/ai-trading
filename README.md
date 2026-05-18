# 🚀 AI Trading Bot System (Full Stack + Risk Engine + Backtesting)
## by@youyou
---

## 📌 Overview

AI Trading Bot System:
- Bybit trading bot
- AI decision (RSI + MACD)
- Redis realtime cache
- Dashboard modern (WebSocket + animasi)
- Risk management engine ✅
- Backtesting simulator ✅

---

# 🏗️ Architecture
ai-trading-system/
├── backend/app/
│   ├── main.py
│   ├── trading.py
│   ├── ai_engine.py
│   ├── risk_engine.py ✅
│   ├── backtest.py ✅
│   ├── bybit_client.py
│   ├── redis_client.py
│
├── frontend/
├── docker-compose.yml
└── README.md

---

# 📊 Trading Strategy

## RSI + MACD

---

# ⚠️ RISK MANAGEMENT ENGINE ✅

## 📌 Tujuan
Mencegah loss besar & menjaga profit konsisten

---

## ✅ Parameter

```python
RISK_PER_TRADE = 0.02   # 2% dari balance
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.04 # 4%

✅ Realtime price
✅ AI Thinking animation
✅ Signal visualization
✅ Position monitoring
✅ Risk (SL/TP display) ✅
✅ Trade log

#trading flow
1. Ambil harga Bybit
2. Hitung RSI + MACD
3. Generate signal
4. Apply risk management
5. Calculate position size
6. Execute trade
7. Update dashboard
8. (Optional) Store for backtest



---

# 📄 ✅ SRS (UPDATED – PROFESSIONAL)

```md
# Software Requirements Specification (SRS)

---

## 1. Purpose

Membangun AI Trading Bot dengan:
- trading otomatis
- risk management
- monitoring realtime
- backtesting

---

## 2. Scope

System mencakup:
- market data ingestion
- AI signal generation
- risk control
- trade execution
- dashboard monitoring
- historical simulation

---

## 3. Functional Requirements

### FR1 Market Data
- Sistem mengambil harga real-time dari Bybit

---

### FR2 AI Signal
- System generate signal berdasarkan RSI + MACD

---

### FR3 Risk Management ✅
- Stop loss otomatis
- Take profit otomatis
- Position sizing maksimum 2% risk

---

### FR4 Trade Execution
- System execute BUY / SELL ke Bybit

---

### FR5 Dashboard
- Menampilkan:
  - harga
  - signal
  - status AI
  - posisi

---

### FR6 Backtesting ✅
- System mampu simulasi strategi
- Output:
  - profit
  - loss
  - balance

---

## 4. Non Functional Requirements

### Performance
- Response < 2 detik

### Availability
- 24/7 uptime

### Security
- API key aman (ENV)

### Scalability
- Support scale untuk multi-pair

---

## 5. Constraints

- Single server (8GB)
- Docker-based
- No Kubernetes

---

## 6. Risk Consideration

- Market volatility tinggi
- Loss tidak bisa dihindari 100%
- System harus fail-safe

---

## 7. Future Enhancements

- Machine learning model
- GPT reasoning
- Bittensor integration
- Auto optimization strategy

---

## 8. Acceptance Criteria

System dianggap sukses jika:
✅ Trading berjalan otomatis  
✅ Risk management aktif  
✅ Dashboard realtime  
✅ Backtesting menghasilkan report  

---

# ✅ END OF SRS
