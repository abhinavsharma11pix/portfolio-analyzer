# 📊 AI Portfolio Analyzer

> Institutional-grade portfolio analytics, ML price predictions, AI investment recommendations, and India-specific tax calculations — in one platform.

**[🚀 Live Demo](https://https://portfolio-analyzer-sigma-amber.vercel.app/)** · [API Docs](https://portfolio-ai-backend-wtm1.onrender.com/docs)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📈 **Portfolio Analytics** | Sharpe ratio, VaR (95/99%), Max Drawdown, Beta, Sortino, Treynor — computed on real yfinance data |
| 🧠 **ML Price Predictions** | 3-model ensemble: ETS (Holt-Winters) + Random Forest + LightGBM. 30-day forecast with confidence bands and A–D reliability grade |
| 🤖 **AI Investment Advisor** | 6-step wizard builds optimised portfolios from 2,300+ NSE stocks. Whole-share allocation for Indian markets. Powered by Groq LLaMA 3 |
| ⚡ **Live Price Streaming** | WebSocket with exponential-backoff reconnect, stale detection, and per-symbol tracking |
| 🧾 **India Tax Engine** | STCG/LTCG under Budget 2024. FIFO lot matching, ₹1.25L LTCG exemption, 4% cess, harvest suggestions |
| 📄 **Institutional PDF Reports** | Goldman Sachs-style A4 report: executive summary, AI narrative insights, charts, holdings table |
| 🔔 **Price Alerts** | Rules-based alert engine with price thresholds and ±% triggers |
| 🔐 **JWT Authentication** | Bcrypt + SHA-256 password hashing. Access + refresh token pair with auto-refresh interceptor |

---

## 🛠 Tech Stack

```
Frontend        React 18 · TypeScript · Vite · Tailwind CSS · Recharts · Axios
Backend         FastAPI · Python 3.11 · SQLite · WebSocket · Uvicorn (2 workers)
ML / AI         ETS (Holt-Winters) · Random Forest · LightGBM · Groq LLaMA 3
Market Data     yfinance · NSE (2,300+ stocks) · NYSE / NASDAQ
Hosting         Vercel (frontend) · Render (backend) · UptimeRobot (uptime monitoring)
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Vercel CDN                                              │
│  React + TypeScript SPA                                  │
│  WebSocket client · Recharts · Tailwind                  │
└──────────────────────┬──────────────────────────────────┘
                        │ REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│  Render (2 workers)                                       │
│  FastAPI · Python 3.11                                    │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Risk Engine │  │ ML Pipeline │  │  AI Advisor     │ │
│  │ Sharpe/VaR  │  │ ETS+RF+LGB  │  │  Groq LLaMA 3   │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                           │
│  SQLite (persistent) · yfinance · diskcache              │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node 20+
- Git

### Backend
```bash
cd backend
python3 -m venv venv311
source venv311/bin/activate  # Windows: venv311\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# Create .env.development
echo "VITE_API_URL=http://localhost:8000" > .env.development
npm run dev
```

### Try the demo
```bash
# Upload demo portfolio
curl -X POST http://localhost:8000/api/portfolio/upload \
  -F "file=@backend/tests/demo_portfolio.csv"
```

---

## 📁 Project Structure

```
portfolio-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # FastAPI route handlers
│   │   ├── services/           # Business logic (prediction, risk, tax)
│   │   ├── ml/                 # ML models (ETS, RF, LightGBM)
│   │   ├── market_data/        # yfinance + price broadcaster
│   │   ├── core/               # Database, security, WebSocket manager
│   │   └── db/                 # Migrations, repositories
│   ├── Procfile                # Render deploy config
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/              # Route-level components
        ├── components/         # Shared UI components
        ├── services/           # API client, auth
        ├── hooks/              # useWebSocket, etc.
        └── config/             # API_BASE, WS_BASE
```

---

## 📊 ML Prediction Pipeline

```
yfinance (2y OHLCV)
       ↓
Feature Engineering
  (RSI, MACD, Bollinger Bands, momentum, lag features)
       ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ETS          │  │ Random       │  │ LightGBM     │
│ Holt-Winters │  │ Forest       │  │ (or GB)      │
│ 2-4s         │  │ ~30s         │  │ ~15s         │
│ Weight: 25%  │  │ Weight: 35%  │  │ Weight: 40%  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       └──────────────────┼──────────────────┘
                  Weighted Ensemble
                          ↓
              Reliability Score (A–D)
              Confidence Bands (±1.96σ)
                          ↓
                  SQLite Cache (8h TTL)
```

---

## 🔌 API Reference

Full interactive docs: `https://portfolio-ai-backend-wtm1.onrender.com/docs`

Key endpoints:
```
POST /api/portfolio/upload          Upload CSV/Excel/PDF portfolio
POST /api/portfolio/risk            Risk analytics (Sharpe, VaR, etc.)
POST /api/analytics/advanced        Advanced metrics (alpha, beta, correlation)
GET  /api/portfolio/predict/{sym}   ML price prediction (cached 8h)
POST /api/recommendation/generate   AI portfolio advisor
POST /api/tax/calculate             India capital gains calculator
POST /api/reports/generate          Generate PDF report (binary)
GET  /ws/prices                     WebSocket live price stream
GET  /health                        Health check
```

---

## ⚠️ Disclaimer

This application is for **educational and demonstration purposes only**. It is not registered with SEBI or any financial regulatory authority. Nothing in this application constitutes investment advice. Always consult a qualified financial advisor before making investment decisions.

---

## 👤 Author

Built by **Abhinav Sharma**  
[GitHub](https://github.com/abhinavsharma11pix) · [LinkedIn](https://www.linkedin.com/in/abhinav-sharma11/)

---

*Made with ☕ and a lot of yfinance API calls*
