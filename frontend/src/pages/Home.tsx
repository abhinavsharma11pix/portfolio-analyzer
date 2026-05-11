import { useNavigate } from 'react-router-dom'
import {
  BarChart3, Shield, TrendingUp, Brain,
  Zap, ArrowRight, CheckCircle, Star
} from 'lucide-react'

const features = [
  {
    icon: <BarChart3 size={22} className="text-blue-400" />,
    title: 'Real-Time Tracking',
    description: 'Live prices for Indian & US stocks via NSE + yfinance with WebSocket push updates.',
    badge: 'Live',
    badgeColor: 'bg-green-900/50 text-green-400',
  },
  {
    icon: <Shield size={22} className="text-purple-400" />,
    title: 'Advanced Risk Analytics',
    description: 'Sharpe ratio, VaR, CVaR, Alpha, Max Drawdown, Beta — hedge-fund grade metrics.',
    badge: 'Quant',
    badgeColor: 'bg-purple-900/50 text-purple-400',
  },
  {
    icon: <TrendingUp size={22} className="text-yellow-400" />,
    title: 'ML Price Predictions',
    description: 'ARIMA + Random Forest + LightGBM ensemble with reliability scoring and confidence intervals.',
    badge: 'AI/ML',
    badgeColor: 'bg-yellow-900/50 text-yellow-400',
  },
  {
    icon: <Brain size={22} className="text-pink-400" />,
    title: 'AI Decision Engine',
    description: 'Explainable buy/sell/hold decisions with specific amounts, triggered metrics, and WHY reasoning.',
    badge: 'Unique',
    badgeColor: 'bg-pink-900/50 text-pink-400',
  },
  {
    icon: <Zap size={22} className="text-orange-400" />,
    title: 'Crash Simulator',
    description: 'Simulate your portfolio under tech crash, banking crisis, market correction scenarios.',
    badge: 'New',
    badgeColor: 'bg-orange-900/50 text-orange-400',
  },
  {
    icon: <BarChart3 size={22} className="text-cyan-400" />,
    title: 'Benchmark Comparison',
    description: 'Compare your returns vs Nifty 50, S&P 500, and Sensex with alpha calculation.',
    badge: 'Pro',
    badgeColor: 'bg-cyan-900/50 text-cyan-400',
  },
]

const stats = [
  { value: '15+', label: 'Risk Metrics' },
  { value: '3',   label: 'ML Models' },
  { value: '9',   label: 'Decision Rules' },
  { value: '5',   label: 'Crash Scenarios' },
]

const steps = [
  { step: '01', title: 'Upload Portfolio', desc: 'CSV, Excel, Zerodha, Groww — we detect the format automatically.' },
  { step: '02', title: 'Get Live Analysis', desc: 'Live prices, P&L, risk metrics and AI insights in under 10 seconds.' },
  { step: '03', title: 'Act on Decisions', desc: 'Specific, explainable actions — what to buy, sell, or trim today.' },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="bg-gray-950 min-h-screen">

      {/* ── Hero ────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-600/5 rounded-full blur-3xl" />
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-purple-600/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-24 text-center">

          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-blue-600/10 border border-blue-600/20 text-blue-400 text-sm px-4 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
            AI-Powered · Hedge-Fund Grade · Free to Use
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-6xl font-black text-white mb-6 leading-tight tracking-tight">
            Understand Your Portfolio
            <br />
            <span className="gradient-text">Like Never Before</span>
          </h1>

          <p className="text-gray-400 text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload your holdings and get institutional-grade analytics,
            AI-powered decisions, and 30-day price predictions — in seconds.
          </p>

          {/* CTAs */}
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-all shadow-xl shadow-blue-600/25"
            >
              Analyze My Portfolio
              <ArrowRight size={18} />
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-all"
            >
              See Live Demo
            </button>
          </div>

          {/* AI Advisor CTA */}
          <div className="mt-4 flex items-center justify-center gap-3">
            <button
              onClick={() => navigate('/recommend')}
              className="flex items-center gap-2 border border-purple-700/60 bg-purple-950/20 hover:bg-purple-950/40 text-purple-400 px-6 py-3 rounded-xl font-medium text-sm transition-all"
            >
              <Brain size={16} />
              Build AI Portfolio from Scratch
            </button>
          </div>

          {/* Trust signals */}
          <div className="flex items-center justify-center gap-6 mt-10 text-sm text-gray-500 flex-wrap">
            {['No signup required', 'Free forever', 'Indian + US stocks', 'Data stays local'].map(t => (
              <div key={t} className="flex items-center gap-1.5">
                <CheckCircle size={14} className="text-green-500" />
                {t}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats ───────────────────────────────────── */}
      <section className="border-y border-gray-800/50 bg-gray-900/30">
        <div className="max-w-4xl mx-auto px-6 py-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map(s => (
              <div key={s.label} className="text-center">
                <p className="text-4xl font-black text-white mb-1">{s.value}</p>
                <p className="text-gray-500 text-sm">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-blue-400 text-sm font-medium uppercase tracking-widest mb-3">
            Everything you need
          </p>
          <h2 className="text-4xl font-bold text-white mb-4">
            Built for serious investors
          </h2>
          <p className="text-gray-400 text-lg max-w-xl mx-auto">
            The same analytics used by quant funds — now accessible to everyone.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f, i) => (
            <div
              key={i}
              className="group bg-gray-900 border border-gray-800 rounded-2xl p-6 hover:border-gray-600 hover:bg-gray-900/80 transition-all duration-300 cursor-default"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-11 h-11 bg-gray-800 group-hover:bg-gray-700 rounded-xl flex items-center justify-center transition-colors">
                  {f.icon}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${f.badgeColor}`}>
                  {f.badge}
                </span>
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ────────────────────────────── */}
      <section className="bg-gray-900/40 border-y border-gray-800/50">
        <div className="max-w-4xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              How it works
            </h2>
            <p className="text-gray-400">From upload to insight in under 30 seconds.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((s, i) => (
              <div key={i} className="relative">
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-6 left-full w-full h-px bg-gradient-to-r from-gray-700 to-transparent z-0" />
                )}
                <div className="relative z-10">
                  <div className="w-12 h-12 bg-blue-600/20 border border-blue-600/30 rounded-xl flex items-center justify-center mb-4">
                    <span className="text-blue-400 font-bold text-sm">{s.step}</span>
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-2">{s.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ──────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <div className="bg-gradient-to-r from-blue-600/10 to-purple-600/10 border border-blue-600/20 rounded-3xl p-12">
          <div className="flex items-center justify-center gap-1 mb-4">
            {[...Array(5)].map((_, i) => (
              <Star key={i} size={16} className="text-yellow-400 fill-yellow-400" />
            ))}
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to take control?
          </h2>
          <p className="text-gray-400 text-lg mb-8 max-w-xl mx-auto">
            Upload your portfolio CSV in 30 seconds and get a complete
            institutional-grade analysis for free.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-10 py-4 rounded-xl font-semibold text-lg transition-all shadow-xl shadow-blue-600/25"
          >
            Start Free Analysis
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────── */}
      <footer className="border-t border-gray-800/50 py-8">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-2 text-white font-bold">
            <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center">
              <BarChart3 size={14} className="text-white" />
            </div>
            Portfolio<span className="text-blue-400">AI</span>
          </div>
          <p className="text-gray-600 text-sm">
            Not financial advice. For educational purposes only.
          </p>
          <div className="flex gap-4 text-gray-600 text-sm">
            <span>Indian + US Markets</span>
            <span>·</span>
            <span>Free Forever</span>
          </div>
        </div>
      </footer>
    </div>
  )
}