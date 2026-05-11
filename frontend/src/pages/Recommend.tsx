import { useState, useCallback, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  ArrowRight, ArrowLeft, Brain, Shield,
  CheckCircle, AlertTriangle, ChevronRight
} from 'lucide-react'

/* ── Types ── */
interface StockRec {
  symbol: string; name: string; sector: string
  allocation_pct: number; allocation_amount: number
  role: string; why: string; risk_contribution: string
  momentum_score: number; sharpe_estimate: number
}
interface RecommendationResult {
  profile: {
    category: string; confidence: number; explanation: string
    equity_pct: number; etf_pct: number; volatility_target: number
  }
  stocks: StockRec[]
  total_amount: number; expected_volatility: number
  diversification_score: number; portfolio_score: number
  ai_commentary: string
  sector_allocation: { sector: string; weight_pct: number }[]
  risk_warnings: string[]; strengths: string[]
}

/* ── Step config ── */
const STEPS = ['Capital', 'Market', 'Horizon', 'Goal', 'Sectors', 'Result']

const GOALS = [
  { value: 'wealth_creation',  label: 'Wealth Creation',     icon: '📈', desc: 'Grow capital over time' },
  { value: 'passive_growth',   label: 'Passive Growth',      icon: '🌱', desc: 'Steady, low-effort returns' },
  { value: 'retirement',       label: 'Retirement',          icon: '🏖️', desc: 'Long-term capital safety' },
  { value: 'high_growth',      label: 'High Growth',         icon: '🚀', desc: 'Maximum upside potential' },
  { value: 'dividend_income',  label: 'Dividend Income',     icon: '💰', desc: 'Regular income from portfolio' },
  { value: 'low_risk',         label: 'Capital Protection',  icon: '🛡️', desc: 'Minimize downside risk' },
  { value: 'learning',         label: 'Learning Mode',       icon: '🎓', desc: 'Explore investing with small amounts' },
]

const HORIZONS = [
  { value: 'short',  label: 'Short Term',  sub: '< 1 year',   icon: '⚡', color: 'border-yellow-700/60 bg-yellow-950/20 hover:border-yellow-600' },
  { value: 'medium', label: 'Medium Term', sub: '1–3 years',  icon: '📅', color: 'border-blue-700/60 bg-blue-950/20 hover:border-blue-600' },
  { value: 'long',   label: 'Long Term',   sub: '3+ years',   icon: '🏔️', color: 'border-green-700/60 bg-green-950/20 hover:border-green-600' },
]

const MARKETS = [
  { value: 'india', label: 'India',         flag: '🇮🇳', sub: 'NSE / BSE stocks', color: 'border-orange-700/60 bg-orange-950/20 hover:border-orange-600' },
  { value: 'us',    label: 'United States', flag: '🇺🇸', sub: 'NYSE / NASDAQ',    color: 'border-blue-700/60 bg-blue-950/20 hover:border-blue-600' },
]

const SECTORS = [
  'Technology','Banking','Healthcare','FMCG','Energy',
  'Finance','Auto','Infra','Consumer','Pharma',
]

const PROFILE_COLORS: Record<string, string> = {
  conservative: 'text-green-400 bg-green-950/30 border-green-800',
  moderate:     'text-blue-400 bg-blue-950/30 border-blue-800',
  aggressive:   'text-orange-400 bg-orange-950/30 border-orange-800',
  high_growth:  'text-red-400 bg-red-950/30 border-red-800',
}

const ROLE_BADGE: Record<string, string> = {
  growth:    'bg-blue-900/40 text-blue-400',
  stability: 'bg-green-900/40 text-green-400',
  dividend:  'bg-yellow-900/40 text-yellow-400',
  balanced:  'bg-purple-900/40 text-purple-400',
  hedge:     'bg-gray-800 text-gray-400',
}

/* ── Progress bar ── */
function Progress({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.slice(0, -1).map((s, i) => (
        <div key={s} className="flex items-center gap-2 flex-1">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all shrink-0 ${
            i < step  ? 'bg-blue-600 text-white' :
            i === step ? 'bg-blue-600/30 border-2 border-blue-500 text-blue-400' :
            'bg-gray-800 text-gray-600'
          }`}>
            {i < step ? '✓' : i + 1}
          </div>
          <span className={`text-xs hidden sm:block ${
            i === step ? 'text-white' : i < step ? 'text-blue-400' : 'text-gray-600'
          }`}>{s}</span>
          {i < STEPS.length - 2 && (
            <div className={`flex-1 h-px ${i < step ? 'bg-blue-600' : 'bg-gray-800'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

/* ── Amount formatter ── */
function fmtAmount(n: number, market: string): string {
  const prefix = market === 'us' ? '$' : '₹'
  if (n >= 10000000) return `${prefix}${(n / 10000000).toFixed(1)}Cr`
  if (n >= 100000)   return `${prefix}${(n / 100000).toFixed(1)}L`
  if (n >= 1000)     return `${prefix}${(n / 1000).toFixed(1)}K`
  return `${prefix}${n.toLocaleString()}`
}

/* ── Main page ── */
export default function Recommend() {
  const navigate = useNavigate()

  const [step,         setStep]         = useState(0)
  const [loading,      setLoading]      = useState(false)
  const [result,       setResult]       = useState<RecommendationResult | null>(null)
  const [error,        setError]        = useState<string | null>(null)
  const [expandedStock, setExpandedStock] = useState<string | null>(null)

  const [form, setForm] = useState({
    amount:            100000,
    market:            'india',
    horizon:           '',
    goal:              '',
    preferred_sectors: [] as string[],
  })

  const updateForm = useCallback((key: string, value: any) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }, [])

  const toggleSector = useCallback((s: string) => {
    setForm(prev => ({
      ...prev,
      preferred_sectors: prev.preferred_sectors.includes(s)
        ? prev.preferred_sectors.filter(x => x !== s)
        : [...prev.preferred_sectors, s],
    }))
  }, [])

  const generate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post(
        'http://localhost:8000/api/recommendation/generate',
        form,
        { timeout: 60000 }
      )
      setResult(res.data)
      setStep(5)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to generate recommendation. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const canNext = () => {
    if (step === 0) return form.amount > 0
    if (step === 1) return !!form.market
    if (step === 2) return !!form.horizon
    if (step === 3) return !!form.goal
    return true
  }

  const next = () => {
    if (step === 4) { generate(); return }
    setStep(s => s + 1)
  }
  const back = () => setStep(s => Math.max(0, s - 1))

  if (step === 5 && result) {
    return (
      <ResultScreen
        result={result}
        amount={form.amount}
        market={form.market}
        onReset={() => { setStep(0); setResult(null) }}
        expandedStock={expandedStock}
        setExpandedStock={setExpandedStock}
        onDashboard={() => navigate('/dashboard')}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-2xl mx-auto px-4 py-12">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-blue-600/10 border border-blue-600/20 text-blue-400 text-sm px-4 py-1.5 rounded-full mb-4">
            <Brain size={14} />
            AI Investment Advisor
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Build Your Portfolio</h1>
          <p className="text-gray-400 text-sm">
            Answer a few questions — our AI creates a personalized investment strategy
          </p>
        </div>

        <Progress step={step} />

        <div className="card p-6 md:p-8">

          {/* Step 0: Amount */}
          {step === 0 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">💰 How much do you want to invest?</h2>
              <p className="text-gray-500 text-sm mb-6">Enter the total amount you'd like to deploy</p>
              <div className="relative mb-4">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-semibold">
                  {form.market === 'us' ? '$' : '₹'}
                </span>
                <input
                  type="number"
                  value={form.amount}
                  onChange={e => updateForm('amount', Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white pl-8 pr-4 py-4 rounded-xl text-xl font-semibold tabular-nums outline-none transition-colors"
                  placeholder="100000"
                  min="1000"
                />
              </div>
              <p className="text-blue-400 font-medium">{fmtAmount(form.amount, form.market)}</p>
              <div className="flex flex-wrap gap-2 mt-4">
                {[10000, 50000, 100000, 500000, 1000000].map(amt => (
                  <button
                    key={amt}
                    onClick={() => updateForm('amount', amt)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      form.amount === amt
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {fmtAmount(amt, form.market)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Market */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">🌍 Which market?</h2>
              <p className="text-gray-500 text-sm mb-6">Select your preferred investment geography</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {MARKETS.map(m => (
                  <button
                    key={m.value}
                    onClick={() => updateForm('market', m.value)}
                    className={`border rounded-2xl p-5 text-left transition-all ${m.color} ${
                      form.market === m.value ? 'ring-2 ring-blue-500' : ''
                    }`}
                  >
                    <div className="text-3xl mb-2">{m.flag}</div>
                    <p className="text-white font-semibold">{m.label}</p>
                    <p className="text-gray-400 text-sm mt-0.5">{m.sub}</p>
                    {form.market === m.value && (
                      <div className="mt-2 flex items-center gap-1 text-blue-400 text-xs">
                        <CheckCircle size={12} /> Selected
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Horizon */}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">⏱️ Investment Timeline</h2>
              <p className="text-gray-500 text-sm mb-6">How long can you keep this money invested?</p>
              <div className="space-y-3">
                {HORIZONS.map(h => (
                  <button
                    key={h.value}
                    onClick={() => updateForm('horizon', h.value)}
                    className={`w-full border rounded-2xl p-4 text-left transition-all ${h.color} ${
                      form.horizon === h.value ? 'ring-2 ring-blue-500' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xl mr-2">{h.icon}</span>
                        <span className="text-white font-semibold">{h.label}</span>
                        <span className="text-gray-400 text-sm ml-2">{h.sub}</span>
                      </div>
                      {form.horizon === h.value && (
                        <CheckCircle size={18} className="text-blue-400" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Goal */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">🎯 Investment Goal</h2>
              <p className="text-gray-500 text-sm mb-6">What do you want to achieve with this portfolio?</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {GOALS.map(g => (
                  <button
                    key={g.value}
                    onClick={() => updateForm('goal', g.value)}
                    className={`border rounded-xl p-4 text-left transition-all ${
                      form.goal === g.value
                        ? 'border-blue-600 bg-blue-950/30 ring-2 ring-blue-500'
                        : 'border-gray-700/60 bg-gray-900/40 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl shrink-0">{g.icon}</span>
                      <div>
                        <p className="text-white font-medium text-sm">{g.label}</p>
                        <p className="text-gray-500 text-xs mt-0.5">{g.desc}</p>
                      </div>
                      {form.goal === g.value && (
                        <CheckCircle size={14} className="text-blue-400 ml-auto shrink-0 mt-0.5" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Sectors */}
          {step === 4 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-1">🏭 Sector Preferences</h2>
              <p className="text-gray-500 text-sm mb-1">Optional — skip to let AI decide</p>
              <p className="text-gray-600 text-xs mb-5">
                Select sectors you're interested in (AI will balance automatically)
              </p>
              <div className="flex flex-wrap gap-2">
                {SECTORS.map(s => (
                  <button
                    key={s}
                    onClick={() => toggleSector(s)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all border ${
                      form.preferred_sectors.includes(s)
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'border-gray-700 bg-gray-800/60 text-gray-300 hover:border-gray-500'
                    }`}
                  >
                    {s}
                    {form.preferred_sectors.includes(s) && <span className="ml-1">✓</span>}
                  </button>
                ))}
              </div>
              {form.preferred_sectors.length > 0 && (
                <p className="text-blue-400 text-sm mt-4">
                  {form.preferred_sectors.length} sector(s) selected
                </p>
              )}

              {/* Summary */}
              <div className="mt-6 bg-gray-800/40 border border-gray-700/60 rounded-xl p-4">
                <p className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-3">
                  Portfolio Summary
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-gray-600 text-xs">Amount</p>
                    <p className="text-white font-semibold">{fmtAmount(form.amount, form.market)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 text-xs">Market</p>
                    <p className="text-white font-semibold capitalize">{form.market}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 text-xs">Horizon</p>
                    <p className="text-white font-semibold capitalize">{form.horizon}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 text-xs">Goal</p>
                    <p className="text-white font-semibold capitalize">
                      {form.goal.replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 flex items-start gap-2 text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-xl px-4 py-3">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            <button
              onClick={back}
              disabled={step === 0}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors disabled:opacity-30"
            >
              <ArrowLeft size={16} /> Back
            </button>
            <button
              onClick={next}
              disabled={!canNext() || loading}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-blue-600/20"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : step === 4 ? (
                <><Brain size={16} /> Generate Portfolio</>
              ) : (
                <>Continue <ArrowRight size={16} /></>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Result Screen ── */
const ResultScreen = memo(function ResultScreen({
  result, amount, market, onReset, expandedStock, setExpandedStock, onDashboard,
}: {
  result: RecommendationResult; amount: number; market: string
  onReset: () => void; expandedStock: string | null
  setExpandedStock: (s: string | null) => void
  onDashboard: () => void
}) {
  const prefix  = market === 'us' ? '$' : '₹'
  const profile = result.profile
  const profileStyle = PROFILE_COLORS[profile.category] ?? 'text-gray-400 bg-gray-900 border-gray-700'

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-4xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-1">Your AI Portfolio</h1>
            <p className="text-gray-500 text-sm">
              {result.stocks.length} stocks ·{' '}
              {prefix}{amount.toLocaleString('en-IN')} total investment
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onReset}
              className="text-sm text-gray-400 hover:text-white border border-gray-700 px-4 py-2 rounded-xl transition-colors"
            >
              ← Rebuild
            </button>
            <button
              onClick={onDashboard}
              className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl transition-colors"
            >
              Dashboard
            </button>
          </div>
        </div>

        {/* Score row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Portfolio Score</p>
            <p className={`text-3xl font-black ${
              result.portfolio_score >= 70 ? 'text-green-400' :
              result.portfolio_score >= 50 ? 'text-yellow-400' : 'text-red-400'
            }`}>{result.portfolio_score}</p>
            <p className="text-gray-600 text-xs">/100</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Diversification</p>
            <p className={`text-3xl font-black ${
              result.diversification_score >= 70 ? 'text-blue-400' : 'text-yellow-400'
            }`}>{result.diversification_score}</p>
            <p className="text-gray-600 text-xs">/100</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Est. Volatility</p>
            <p className={`text-3xl font-black ${
              result.expected_volatility > 28 ? 'text-red-400' :
              result.expected_volatility > 18 ? 'text-yellow-400' : 'text-green-400'
            }`}>{result.expected_volatility}%</p>
            <p className="text-gray-600 text-xs">annual</p>
          </div>
          <div className={`card p-4 text-center border ${profileStyle}`}>
            <p className="text-xs uppercase tracking-wide mb-1 opacity-70">Risk Profile</p>
            <p className="text-lg font-bold capitalize">
              {profile.category.replace('_', ' ')}
            </p>
            <p className="text-xs opacity-60">
              {Math.round(profile.confidence * 100)}% confidence
            </p>
          </div>
        </div>

        {/* Profile explanation */}
        <div className={`border rounded-2xl p-5 mb-6 ${profileStyle}`}>
          <div className="flex items-center gap-2 mb-2">
            <Shield size={16} />
            <span className="font-semibold text-sm">
              Risk Profile: {profile.category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </span>
          </div>
          <p className="text-sm opacity-80 leading-relaxed">{profile.explanation}</p>
        </div>

        {/* AI Commentary */}
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={16} className="text-blue-400" />
            <h3 className="text-white font-semibold text-sm">AI Commentary</h3>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{result.ai_commentary}</p>
        </div>

        {/* Strengths + Warnings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {result.strengths.length > 0 && (
            <div className="card p-4 border-green-800/40 bg-green-950/10">
              <h3 className="text-green-400 font-semibold text-sm mb-3 flex items-center gap-2">
                <CheckCircle size={14} /> Strengths
              </h3>
              <div className="space-y-2">
                {result.strengths.map((s, i) => (
                  <p key={i} className="text-gray-300 text-xs flex gap-2">
                    <span className="text-green-500 shrink-0">✓</span> {s}
                  </p>
                ))}
              </div>
            </div>
          )}
          {result.risk_warnings.length > 0 && (
            <div className="card p-4 border-yellow-800/40 bg-yellow-950/10">
              <h3 className="text-yellow-400 font-semibold text-sm mb-3 flex items-center gap-2">
                <AlertTriangle size={14} /> Risk Warnings
              </h3>
              <div className="space-y-2">
                {result.risk_warnings.map((w, i) => (
                  <p key={i} className="text-gray-300 text-xs flex gap-2">
                    <span className="text-yellow-500 shrink-0">⚠</span> {w}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sector allocation */}
        <div className="card p-5 mb-6">
          <h3 className="text-white font-semibold text-sm mb-4">Sector Allocation</h3>
          <div className="space-y-2.5">
            {result.sector_allocation.map(s => (
              <div key={s.sector} className="flex items-center gap-3">
                <span className="text-gray-400 text-xs w-28 shrink-0">{s.sector}</span>
                <div className="flex-1 bg-gray-800 rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-blue-500"
                    style={{ width: `${s.weight_pct}%` }}
                  />
                </div>
                <span className="text-gray-400 text-xs tabular-nums w-10 text-right">
                  {s.weight_pct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Stock recommendations */}
        <div className="space-y-3">
          <h3 className="text-white font-semibold text-lg mb-4">
            Recommended Stocks ({result.stocks.length})
          </h3>
          {result.stocks.map((stock, i) => (
            <div key={stock.symbol} className="card overflow-hidden">
              <button
                onClick={() => setExpandedStock(expandedStock === stock.symbol ? null : stock.symbol)}
                className="w-full flex items-center gap-4 p-4 hover:bg-white/[0.02] transition-colors text-left"
              >
                <div className="w-7 h-7 rounded-full bg-blue-600/20 flex items-center justify-center text-blue-400 text-xs font-bold shrink-0">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold text-sm">{stock.symbol}</span>
                    <span className="text-gray-500 text-xs truncate">{stock.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${ROLE_BADGE[stock.role] ?? 'bg-gray-800 text-gray-400'}`}>
                      {stock.role}
                    </span>
                    <span className="text-xs text-gray-600">{stock.sector}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-white font-bold tabular-nums">
                    {prefix}{stock.allocation_amount.toLocaleString('en-IN')}
                  </p>
                  <p className="text-gray-500 text-xs tabular-nums">{stock.allocation_pct}%</p>
                </div>
                <ChevronRight size={14} className={`text-gray-500 transition-transform shrink-0 ${
                  expandedStock === stock.symbol ? 'rotate-90' : ''
                }`} />
              </button>

              {expandedStock === stock.symbol && (
                <div className="border-t border-white/[0.04] px-4 pb-4 pt-3 space-y-3 animate-fade-in">
                  <p className="text-gray-300 text-sm leading-relaxed">{stock.why}</p>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-gray-800/40 rounded-lg p-3">
                      <p className="text-gray-600 text-xs mb-1">Risk Contribution</p>
                      <p className={`text-sm font-semibold ${
                        stock.risk_contribution === 'Low'    ? 'text-green-400' :
                        stock.risk_contribution === 'Medium' ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>{stock.risk_contribution}</p>
                    </div>
                    <div className="bg-gray-800/40 rounded-lg p-3">
                      <p className="text-gray-600 text-xs mb-1">Momentum</p>
                      <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
                        <div
                          className="h-1.5 rounded-full bg-blue-500"
                          style={{ width: `${stock.momentum_score * 100}%` }}
                        />
                      </div>
                      <p className="text-gray-400 text-xs mt-1">
                        {(stock.momentum_score * 100).toFixed(0)}/100
                      </p>
                    </div>
                    <div className="bg-gray-800/40 rounded-lg p-3">
                      <p className="text-gray-600 text-xs mb-1">Est. Sharpe</p>
                      <p className={`text-sm font-semibold tabular-nums ${
                        stock.sharpe_estimate > 1 ? 'text-green-400' : 'text-yellow-400'
                      }`}>
                        {stock.sharpe_estimate.toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Disclaimer */}
        <p className="text-gray-700 text-xs text-center mt-8">
          AI-generated analysis for educational purposes only. Not financial advice.
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  )
})