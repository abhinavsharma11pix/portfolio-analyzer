/**
 * pages/Home.tsx — Complete file.
 * Fixed: removed Github (not in lucide-react), TrendingUp, PieChart (unused)
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart3, Brain, Shield, FileText, Zap,
  Calculator, Bell, ChevronRight,
  ExternalLink, Activity,
  Sparkles, ArrowRight, CheckCircle,
} from 'lucide-react'
import { API_BASE } from '../config/api'

const FEATURES = [
  {
    icon: <BarChart3 size={20} className="text-blue-400" />,
    title: 'Portfolio Analytics',
    desc: 'Sharpe ratio, Value-at-Risk, Max Drawdown, Beta, Sortino. Institutional-grade risk metrics computed on real market data.',
    badge: 'Risk Engine',
    color: 'blue',
  },
  {
    icon: <Brain size={20} className="text-purple-400" />,
    title: 'ML Price Predictions',
    desc: 'Ensemble of ETS + Random Forest + LightGBM. 30-day forecast with confidence bands and A–D reliability grading.',
    badge: '3 Models',
    color: 'purple',
  },
  {
    icon: <Sparkles size={20} className="text-yellow-400" />,
    title: 'AI Investment Advisor',
    desc: '6-step wizard builds an optimised portfolio from 2,300+ NSE stocks. Whole-share enforcement for Indian markets.',
    badge: 'Groq LLaMA',
    color: 'yellow',
  },
  {
    icon: <Activity size={20} className="text-green-400" />,
    title: 'Live Price WebSocket',
    desc: 'Real-time price streaming via WebSocket with exponential-backoff reconnect. Stale detection and per-symbol tracking.',
    badge: 'WebSocket',
    color: 'green',
  },
  {
    icon: <Calculator size={20} className="text-orange-400" />,
    title: 'India Tax Engine',
    desc: 'STCG/LTCG computation under Budget 2024 rates. FIFO lot matching, ₹1.25L exemption, 4% cess, and harvest suggestions.',
    badge: 'FY 2024-25',
    color: 'orange',
  },
  {
    icon: <FileText size={20} className="text-pink-400" />,
    title: 'Institutional PDF Reports',
    desc: 'Goldman Sachs-style A4 report with executive summary, narrative insights, charts, and holdings table. Instant download.',
    badge: 'ReportLab',
    color: 'pink',
  },
  {
    icon: <Bell size={20} className="text-cyan-400" />,
    title: 'Price Alerts',
    desc: 'Rules-based alert engine. Set price-above, price-below, or ±% thresholds. Unread badge in navbar.',
    badge: 'Real-time',
    color: 'cyan',
  },
  {
    icon: <Shield size={20} className="text-red-400" />,
    title: 'JWT Authentication',
    desc: 'Bcrypt + SHA-256 password hashing. Access + refresh token pair. Auto-refresh interceptor on 401.',
    badge: 'Secure',
    color: 'red',
  },
]

const TECH_STACK = [
  { layer: 'Frontend',    items: ['React 18', 'TypeScript', 'Vite', 'Tailwind CSS', 'Recharts', 'Axios'] },
  { layer: 'Backend',     items: ['FastAPI', 'Python 3.11', 'SQLite', 'WebSocket', 'Uvicorn (2 workers)'] },
  { layer: 'ML / AI',     items: ['ETS (Holt-Winters)', 'Random Forest', 'LightGBM', 'Groq LLaMA 3'] },
  { layer: 'Market Data', items: ['yfinance', 'NSE (2,300+ stocks)', 'NYSE / NASDAQ', 'Real-time pricing'] },
  { layer: 'Hosting',     items: ['Vercel (frontend)', 'Render (backend)', 'UptimeRobot'] },
]

const STATS = [
  { label: 'NSE Stocks Covered',   value: '2,300+' },
  { label: 'ML Models in Ensemble', value: '3' },
  { label: 'Risk Metrics Computed', value: '12+' },
  { label: 'Avg Prediction Time',   value: '~30s' },
]

const DEMO_CSV = `Symbol,Qty,Buy_Price,Sector
RELIANCE.NS,10,1280,Energy
TCS.NS,5,2100,Technology
INFY.NS,8,1500,Technology
HDFCBANK.NS,15,700,Banking
BAJFINANCE.NS,3,6500,Finance
AAPL,3,190,Technology
GOOGL,2,165,Technology`

const BORDER_MAP: Record<string, string> = {
  blue:   'border-blue-800/40 hover:border-blue-700/60',
  purple: 'border-purple-800/40 hover:border-purple-700/60',
  yellow: 'border-yellow-800/40 hover:border-yellow-700/60',
  green:  'border-green-800/40 hover:border-green-700/60',
  orange: 'border-orange-800/40 hover:border-orange-700/60',
  pink:   'border-pink-800/40 hover:border-pink-700/60',
  cyan:   'border-cyan-800/40 hover:border-cyan-700/60',
  red:    'border-red-800/40 hover:border-red-700/60',
}

const BG_MAP: Record<string, string> = {
  blue:   'bg-blue-950/20',   purple: 'bg-purple-950/20',
  yellow: 'bg-yellow-950/20', green:  'bg-green-950/20',
  orange: 'bg-orange-950/20', pink:   'bg-pink-950/20',
  cyan:   'bg-cyan-950/20',   red:    'bg-red-950/20',
}

export default function Home() {
  const navigate = useNavigate()
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [backendAlive, setBackendAlive] = useState<boolean | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => setBackendAlive(r.ok))
      .catch(() => setBackendAlive(false))
  }, [])

  const handleDemo = async () => {
    setLoadingDemo(true)
    try {
      const blob = new Blob([DEMO_CSV], { type: 'text/csv' })
      const file = new File([blob], 'demo_portfolio.csv', { type: 'text/csv' })
      const form = new FormData()
      form.append('file', file)
      const res  = await fetch(`${API_BASE}/api/portfolio/upload`, { method: 'POST', body: form })
      const data = await res.json()
      if (data.holdings) {
        sessionStorage.setItem('portfolio_data', JSON.stringify(data))
      }
      navigate('/dashboard')
    } catch {
      navigate('/dashboard')
    } finally {
      setLoadingDemo(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-950/40 border border-blue-800/50 text-blue-400 text-xs px-4 py-1.5 rounded-full mb-6">
          <Zap size={12} />
          Live · NSE + NYSE · 2,300+ stocks · ML Predictions
        </div>

        <h1 className="text-4xl md:text-6xl font-black leading-tight mb-6">
          AI-Powered Portfolio
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
            Analyzer &amp; Advisor
          </span>
        </h1>

        <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
          Institutional-grade portfolio analytics, ML price predictions,
          AI investment recommendations, and India-specific tax calculations —
          all in one platform.
        </p>

        {backendAlive !== null && (
          <div className="flex items-center justify-center gap-2 mb-6">
            <span className={`w-2 h-2 rounded-full ${backendAlive ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`} />
            <span className={`text-xs ${backendAlive ? 'text-green-400' : 'text-yellow-400'}`}>
              {backendAlive ? 'All systems live' : 'Backend warming up — first load takes ~20s'}
            </span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-6">
          <button
            onClick={handleDemo}
            disabled={loadingDemo}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-70 text-white px-8 py-3.5 rounded-2xl font-bold text-base transition-all shadow-2xl shadow-blue-600/30 hover:scale-105 active:scale-100"
          >
            {loadingDemo ? (
              <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Loading demo...</>
            ) : (
              <><Sparkles size={18} /> Try Live Demo</>
            )}
          </button>

          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-2xl font-semibold text-base transition-all"
          >
            Upload Your Portfolio <ArrowRight size={16} />
          </button>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1"><CheckCircle size={11} /> No signup required for demo</span>
          <span className="flex items-center gap-1"><CheckCircle size={11} /> Real NSE market data</span>
          <span className="flex items-center gap-1"><CheckCircle size={11} /> Free forever</span>
        </div>
      </section>

      {/* ── Stats bar ─────────────────────────────────────────── */}
      <section className="border-y border-gray-800/60 bg-gray-900/30">
        <div className="max-w-4xl mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-black text-white tabular-nums">{s.value}</p>
              <p className="text-gray-500 text-sm mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Feature grid ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-3">Everything you need</h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            Built with production-grade architecture. Every feature backed by real market data.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map(f => (
            <div
              key={f.title}
              className={`border rounded-2xl p-5 transition-all duration-200 hover:scale-[1.01] ${BORDER_MAP[f.color]} ${BG_MAP[f.color]}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 bg-gray-800/60 rounded-xl flex items-center justify-center">
                  {f.icon}
                </div>
                <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
                  {f.badge}
                </span>
              </div>
              <h3 className="text-white font-semibold text-sm mb-1.5">{f.title}</h3>
              <p className="text-gray-500 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="bg-gray-900/30 border-y border-gray-800/60">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <h2 className="text-3xl font-bold text-white text-center mb-12">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { step: '01', title: 'Upload Portfolio',  desc: 'CSV, Excel, Zerodha or Groww export. AI validates and enriches symbols automatically.', icon: '📁' },
              { step: '02', title: 'Real-time Analysis', desc: 'Risk metrics, P&L, sector allocation, and benchmark comparison computed instantly.',    icon: '📊' },
              { step: '03', title: 'ML Predictions',    desc: '3-model ensemble forecasts 30-day price movement with confidence bands and reliability score.', icon: '🧠' },
              { step: '04', title: 'Act on Insights',   desc: 'AI advisor builds an optimised portfolio. Tax engine shows harvest opportunities.',      icon: '✅' },
            ].map(s => (
              <div key={s.step}>
                <div className="text-4xl mb-4">{s.icon}</div>
                <div className="text-blue-400 text-xs font-bold mb-1">STEP {s.step}</div>
                <h3 className="text-white font-semibold mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Tech stack ────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-white text-center mb-3">Built with</h2>
        <p className="text-gray-500 text-center mb-12">Production-grade stack, zero vendor lock-in</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {TECH_STACK.map(({ layer, items }) => (
            <div key={layer} className="bg-gray-900/50 border border-gray-800 rounded-2xl p-5">
              <p className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-3">{layer}</p>
              <div className="flex flex-wrap gap-2">
                {items.map(item => (
                  <span key={item} className="text-xs bg-gray-800 text-gray-300 px-2.5 py-1 rounded-lg">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Quick nav ─────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-4 pb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Dashboard',   path: '/dashboard', icon: <BarChart3 size={16} /> },
            { label: 'AI Advisor',  path: '/recommend', icon: <Sparkles size={16} /> },
            { label: 'Tax P&L',     path: '/tax',       icon: <Calculator size={16} /> },
            { label: 'PDF Reports', path: '/reports',   icon: <FileText size={16} /> },
          ].map(n => (
            <button
              key={n.path}
              onClick={() => navigate(n.path)}
              className="flex items-center justify-between bg-gray-900/50 hover:bg-gray-800/60 border border-gray-800 hover:border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-400 hover:text-white transition-all group"
            >
              <div className="flex items-center gap-2">{n.icon}{n.label}</div>
              <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="border-t border-gray-800/60 bg-gray-950">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                <BarChart3 size={14} className="text-white" />
              </div>
              <span className="text-white font-bold">PortfolioAI</span>
            </div>

            <div className="flex items-center gap-4">
              <a
                href="https://github.com/abhinavsharma11pix/portfolio-analyzer"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-gray-500 hover:text-white text-sm transition-colors"
              >
                GitHub <ExternalLink size={11} />
              </a>
              <a
                href={`${API_BASE}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-gray-500 hover:text-white text-sm transition-colors"
              >
                API Docs <ExternalLink size={11} />
              </a>
            </div>

            <p className="text-xs text-gray-700">
              Educational purposes only · Not SEBI-registered · Not investment advice
            </p>
          </div>
        </div>
      </footer>

    </div>
  )
}
