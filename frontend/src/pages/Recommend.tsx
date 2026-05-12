import { useState, useCallback, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  ArrowRight, ArrowLeft, Brain, Shield,
  CheckCircle, AlertTriangle, ChevronRight,
  Minus, Plus, TrendingUp, Activity
} from 'lucide-react'

/* ── Types ── */
interface StockRec {
  symbol: string; name: string; sector: string
  allocation_pct: number; allocation_amount: number
  role: string; why: string; risk_contribution: string
  momentum_score: number; sharpe_estimate: number
  volatility: number; composite_score: number
  momentum_1y: number; max_drawdown: number; beta: number
}
interface RecommendationResult {
  profile: {
    category: string; confidence: number; explanation: string
    equity_pct: number; etf_pct: number; volatility_target: number
  }
  stocks: StockRec[]
  total_amount: number; expected_return: number; expected_volatility: number
  diversification_score: number; portfolio_score: number
  weighted_sharpe: number; weighted_beta: number
  score_breakdown: Record<string, number>
  ai_commentary: string
  sector_allocation: { sector: string; weight_pct: number }[]
  risk_warnings: string[]; strengths: string[]
  data_note: string; sectors_used: string[]
}

const STEPS = ['Capital', 'Market', 'Horizon', 'Goal', 'Sectors', 'Stocks', 'Result']

const GOALS = [
  { value: 'wealth_creation', label: 'Wealth Creation',    icon: '📈', desc: 'Grow capital over time' },
  { value: 'passive_growth',  label: 'Passive Growth',     icon: '🌱', desc: 'Steady, low-effort returns' },
  { value: 'retirement',      label: 'Retirement',         icon: '🏖️', desc: 'Long-term capital safety' },
  { value: 'high_growth',     label: 'High Growth',        icon: '🚀', desc: 'Maximum upside potential' },
  { value: 'dividend_income', label: 'Dividend Income',    icon: '💰', desc: 'Regular income from portfolio' },
  { value: 'low_risk',        label: 'Capital Protection', icon: '🛡️', desc: 'Minimize downside risk' },
  { value: 'learning',        label: 'Learning Mode',      icon: '🎓', desc: 'Explore with small amounts' },
]

const HORIZONS = [
  { value: 'short',  label: 'Short Term',  sub: '< 1 year',   icon: '⚡', color: 'border-yellow-700/60 bg-yellow-950/20 hover:border-yellow-600' },
  { value: 'medium', label: 'Medium Term', sub: '1–3 years',  icon: '📅', color: 'border-blue-700/60 bg-blue-950/20 hover:border-blue-600' },
  { value: 'long',   label: 'Long Term',   sub: '3+ years',   icon: '🏔️', color: 'border-green-700/60 bg-green-950/20 hover:border-green-600' },
]

const MARKETS = [
  { value: 'india', label: 'India',         flag: '🇮🇳', sub: 'NSE / BSE — all listed stocks', color: 'border-orange-700/60 bg-orange-950/20 hover:border-orange-600' },
  { value: 'us',    label: 'United States', flag: '🇺🇸', sub: 'S&P 500 universe',              color: 'border-blue-700/60 bg-blue-950/20 hover:border-blue-600' },
]

const SECTORS_INDIA = ['Technology','Banking','Healthcare','FMCG','Energy','Finance','Auto','Infra','Consumer','Pharma','Defense','IT','Metals']
const SECTORS_US    = ['Technology','Finance','Healthcare','Consumer','Energy','Infra','Metals']

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
  recovery:  'bg-orange-900/40 text-orange-400',
}

function Progress({ step }: { step: number }) {
  const visible = STEPS.slice(0, -1)
  return (
    <div className="flex items-center gap-1.5 mb-8 overflow-x-auto pb-1">
      {visible.map((s, i) => (
        <div key={s} className="flex items-center gap-1.5 shrink-0">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
            i < step  ? 'bg-blue-600 text-white' :
            i === step ? 'bg-blue-600/30 border-2 border-blue-500 text-blue-400' :
            'bg-gray-800 text-gray-600'
          }`}>
            {i < step ? '✓' : i + 1}
          </div>
          <span className={`text-xs hidden md:block ${
            i === step ? 'text-white' : i < step ? 'text-blue-400' : 'text-gray-600'
          }`}>{s}</span>
          {i < visible.length - 1 && (
            <div className={`w-4 h-px ${i < step ? 'bg-blue-600' : 'bg-gray-800'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function fmtAmount(n: number, market: string): string {
  const p = market === 'us' ? '$' : '₹'
  if (n >= 10000000) return `${p}${(n/10000000).toFixed(1)}Cr`
  if (n >= 100000)   return `${p}${(n/100000).toFixed(1)}L`
  if (n >= 1000)     return `${p}${(n/1000).toFixed(1)}K`
  return `${p}${n.toLocaleString()}`
}

export default function Recommend() {
  const navigate = useNavigate()
  const [step,          setStep]          = useState(0)
  const [loading,       setLoading]       = useState(false)
  const [result,        setResult]        = useState<RecommendationResult | null>(null)
  const [error,         setError]         = useState<string | null>(null)
  const [expandedStock, setExpandedStock] = useState<string | null>(null)

  const [form, setForm] = useState({
    amount:            100000,
    market:            'india',
    horizon:           '',
    goal:              '',
    preferred_sectors: [] as string[],
    n_stocks_min:      5,
    n_stocks_max:      10,
  })

  const update = useCallback((k: string, v: any) => setForm(p => ({ ...p, [k]: v })), [])

  const toggleSector = useCallback((s: string) => {
    setForm(p => ({
      ...p,
      preferred_sectors: p.preferred_sectors.includes(s)
        ? p.preferred_sectors.filter(x => x !== s)
        : [...p.preferred_sectors, s],
    }))
  }, [])

  const generate = async () => {
    setLoading(true); setError(null)
    try {
      const res = await axios.post('http://localhost:8000/api/recommendation/generate', form, { timeout: 120000 })
      setResult(res.data); setStep(6)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to generate. Please try again.')
    } finally {
      setLoading(false) }
  }

  const canNext = () => {
    if (step === 0) return form.amount >= 1000
    if (step === 1) return !!form.market
    if (step === 2) return !!form.horizon
    if (step === 3) return !!form.goal
    if (step === 5) return form.n_stocks_min <= form.n_stocks_max
    return true
  }

  const next = () => {
    if (step === 5) { generate(); return }
    setStep(s => s + 1)
  }

  if (step === 6 && result) {
    return <ResultScreen result={result} amount={form.amount} market={form.market}
      onReset={() => { setStep(0); setResult(null) }}
      onDashboard={() => navigate('/dashboard')}
      expandedStock={expandedStock} setExpandedStock={setExpandedStock} />
  }

  const sectors = form.market === 'us' ? SECTORS_US : SECTORS_INDIA

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-blue-600/10 border border-blue-600/20 text-blue-400 text-sm px-4 py-1.5 rounded-full mb-4">
            <Brain size={14} /> AI Investment Advisor
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Build Your Portfolio</h1>
          <p className="text-gray-400 text-sm">
            Powered by real market data · Scored on actual Sharpe, momentum & drawdown
          </p>
        </div>

        <Progress step={step} />

        <div className="card p-6 md:p-8">

          {/* Step 0: Amount */}
          {step === 0 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">💰 Investment Amount</h2>
              <p className="text-gray-500 text-sm mb-6">How much would you like to invest?</p>
              <div className="relative mb-3">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-semibold">
                  {form.market === 'us' ? '$' : '₹'}
                </span>
                <input type="number" value={form.amount}
                  onChange={e => update('amount', Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white pl-8 pr-4 py-4 rounded-xl text-xl font-semibold tabular-nums outline-none"
                  min="1000" />
              </div>
              <p className="text-blue-400 font-medium mb-4">{fmtAmount(form.amount, form.market)}</p>
              <div className="flex flex-wrap gap-2">
                {[10000,50000,100000,500000,1000000].map(a => (
                  <button key={a} onClick={() => update('amount', a)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      form.amount === a ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}>{fmtAmount(a, form.market)}</button>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Market */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">🌍 Market Selection</h2>
              <p className="text-gray-500 text-sm mb-6">
                We'll scan all listed stocks in your chosen market
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {MARKETS.map(m => (
                  <button key={m.value} onClick={() => update('market', m.value)}
                    className={`border rounded-2xl p-5 text-left transition-all ${m.color} ${form.market === m.value ? 'ring-2 ring-blue-500' : ''}`}>
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
              <h2 className="text-xl font-semibold text-white mb-2">⏱️ Investment Horizon</h2>
              <p className="text-gray-500 text-sm mb-6">How long do you plan to stay invested?</p>
              <div className="space-y-3">
                {HORIZONS.map(h => (
                  <button key={h.value} onClick={() => update('horizon', h.value)}
                    className={`w-full border rounded-2xl p-4 text-left transition-all ${h.color} ${form.horizon === h.value ? 'ring-2 ring-blue-500' : ''}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xl mr-2">{h.icon}</span>
                        <span className="text-white font-semibold">{h.label}</span>
                        <span className="text-gray-400 text-sm ml-2">{h.sub}</span>
                      </div>
                      {form.horizon === h.value && <CheckCircle size={18} className="text-blue-400" />}
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
              <p className="text-gray-500 text-sm mb-6">This determines your risk profile and stock selection criteria</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {GOALS.map(g => (
                  <button key={g.value} onClick={() => update('goal', g.value)}
                    className={`border rounded-xl p-4 text-left transition-all ${
                      form.goal === g.value
                        ? 'border-blue-600 bg-blue-950/30 ring-2 ring-blue-500'
                        : 'border-gray-700/60 bg-gray-900/40 hover:border-gray-600'
                    }`}>
                    <div className="flex items-start gap-3">
                      <span className="text-2xl shrink-0">{g.icon}</span>
                      <div>
                        <p className="text-white font-medium text-sm">{g.label}</p>
                        <p className="text-gray-500 text-xs mt-0.5">{g.desc}</p>
                      </div>
                      {form.goal === g.value && (
                        <CheckCircle size={14} className="text-blue-400 ml-auto shrink-0" />
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
              <h2 className="text-xl font-semibold text-white mb-1">🏭 Sector Focus</h2>
              <p className="text-gray-500 text-sm mb-1">Optional — skip to let AI scan all sectors</p>
              <div className="bg-blue-950/20 border border-blue-800/40 rounded-xl px-4 py-2.5 mb-4">
                <p className="text-blue-300 text-xs">
                  ✓ <strong>Strict mode:</strong> selecting sectors will restrict recommendations
                  to ONLY those sectors. Leave empty for full market scan.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {sectors.map(s => (
                  <button key={s} onClick={() => toggleSector(s)}
                    className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${
                      form.preferred_sectors.includes(s)
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'border-gray-700 bg-gray-800/60 text-gray-300 hover:border-gray-500'
                    }`}>
                    {s} {form.preferred_sectors.includes(s) && '✓'}
                  </button>
                ))}
              </div>
              {form.preferred_sectors.length > 0 ? (
                <p className="text-blue-400 text-sm mt-3">
                  Will scan <strong>{form.preferred_sectors.join(', ')}</strong> sector stocks only
                </p>
              ) : (
                <p className="text-gray-600 text-sm mt-3">
                  No sectors selected — will scan entire {form.market === 'india' ? 'NSE' : 'S&P 500'} universe
                </p>
              )}
            </div>
          )}

          {/* Step 5: Stock Count */}
          {step === 5 && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">📊 Number of Stocks</h2>
              <p className="text-gray-500 text-sm mb-6">
                Set min and max — AI will pick the optimal number within your range
              </p>

              <div className="grid grid-cols-2 gap-6 mb-6">
                {/* Min */}
                <div className="card p-4">
                  <p className="text-gray-400 text-xs uppercase tracking-wide mb-3">Minimum</p>
                  <div className="flex items-center gap-3">
                    <button onClick={() => update('n_stocks_min', Math.max(3, form.n_stocks_min - 1))}
                      className="w-8 h-8 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors">
                      <Minus size={14} className="text-gray-300" />
                    </button>
                    <span className="text-3xl font-bold text-white w-10 text-center tabular-nums">
                      {form.n_stocks_min}
                    </span>
                    <button onClick={() => update('n_stocks_min', Math.min(form.n_stocks_max, form.n_stocks_min + 1))}
                      className="w-8 h-8 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors">
                      <Plus size={14} className="text-gray-300" />
                    </button>
                  </div>
                  <p className="text-gray-600 text-xs mt-2">min 3</p>
                </div>

                {/* Max */}
                <div className="card p-4">
                  <p className="text-gray-400 text-xs uppercase tracking-wide mb-3">Maximum</p>
                  <div className="flex items-center gap-3">
                    <button onClick={() => update('n_stocks_max', Math.max(form.n_stocks_min, form.n_stocks_max - 1))}
                      className="w-8 h-8 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors">
                      <Minus size={14} className="text-gray-300" />
                    </button>
                    <span className="text-3xl font-bold text-white w-10 text-center tabular-nums">
                      {form.n_stocks_max}
                    </span>
                    <button onClick={() => update('n_stocks_max', Math.min(20, form.n_stocks_max + 1))}
                      className="w-8 h-8 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors">
                      <Plus size={14} className="text-gray-300" />
                    </button>
                  </div>
                  <p className="text-gray-600 text-xs mt-2">max 20</p>
                </div>
              </div>

              {/* Guidance */}
              <div className="space-y-2 text-sm">
                {[
                  { range: '3–5',  label: 'Concentrated',  desc: 'High conviction, higher risk per stock' },
                  { range: '6–10', label: 'Balanced',      desc: 'Good diversification, manageable tracking' },
                  { range: '11–15',label: 'Diversified',   desc: 'Lower single-stock risk' },
                  { range: '16–20',label: 'Broad basket',  desc: 'Near-index exposure' },
                ].map(g => {
                  const [lo, hi] = g.range.split('–').map(Number)
                  const active   = form.n_stocks_min >= lo && form.n_stocks_max <= hi + 1
                  return (
                    <div key={g.range} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${active ? 'bg-blue-950/30 border border-blue-800/40' : 'bg-gray-800/30'}`}>
                      <span className={`text-xs font-mono w-12 ${active ? 'text-blue-400' : 'text-gray-600'}`}>{g.range}</span>
                      <span className={`text-xs font-medium ${active ? 'text-white' : 'text-gray-500'}`}>{g.label}</span>
                      <span className={`text-xs ${active ? 'text-gray-400' : 'text-gray-700'}`}>{g.desc}</span>
                    </div>
                  )
                })}
              </div>

              {/* Full summary */}
              <div className="mt-6 bg-gray-800/40 border border-gray-700/60 rounded-xl p-4">
                <p className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-3">Final Summary</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  {[
                    { k: 'Amount',   v: fmtAmount(form.amount, form.market) },
                    { k: 'Market',   v: form.market === 'india' ? '🇮🇳 India' : '🇺🇸 US' },
                    { k: 'Horizon',  v: form.horizon },
                    { k: 'Goal',     v: form.goal.replace(/_/g, ' ') },
                    { k: 'Sectors',  v: form.preferred_sectors.length ? form.preferred_sectors.join(', ') : 'All sectors' },
                    { k: 'Stocks',   v: `${form.n_stocks_min}–${form.n_stocks_max}` },
                  ].map(r => (
                    <div key={r.k}>
                      <p className="text-gray-600 text-xs capitalize">{r.k}</p>
                      <p className="text-white font-medium text-xs capitalize truncate">{r.v}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 bg-yellow-950/20 border border-yellow-800/40 rounded-xl px-4 py-3">
                <p className="text-yellow-300 text-xs">
                  ⏱️ Generation takes 30–90 seconds — we scan real market data and score
                  each stock using Sharpe ratio, momentum, and drawdown analysis.
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-xl px-4 py-3">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" /> {error}
            </div>
          )}

          <div className="flex items-center justify-between mt-8">
            <button onClick={() => setStep(s => Math.max(0, s-1))} disabled={step === 0}
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors disabled:opacity-30">
              <ArrowLeft size={16} /> Back
            </button>
            <button onClick={next} disabled={!canNext() || loading}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-blue-600/20">
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Scanning market data...
                </>
              ) : step === 5 ? (
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
  result, amount, market, onReset, onDashboard, expandedStock, setExpandedStock,
}: {
  result: RecommendationResult; amount: number; market: string
  onReset: () => void; onDashboard: () => void
  expandedStock: string | null; setExpandedStock: (s: string | null) => void
}) {
  const prefix  = market === 'us' ? '$' : '₹'
  const profile = result.profile
  const ps      = result.portfolio_score
  const scoreColor = ps >= 70 ? 'text-green-400' : ps >= 55 ? 'text-yellow-400' : 'text-orange-400'

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-4xl mx-auto px-4 py-10">

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-1">Your AI Portfolio</h1>
            <p className="text-gray-500 text-sm">
              {result.stocks.length} stocks · {prefix}{amount.toLocaleString('en-IN')}
              {result.sectors_used?.length > 0 && (
                <span className="ml-2 text-gray-600">· {result.sectors_used.join(', ')}</span>
              )}
            </p>
            <p className="text-xs text-blue-400/70 mt-0.5">{result.data_note}</p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button onClick={onReset} className="text-sm text-gray-400 hover:text-white border border-gray-700 px-3 py-2 rounded-xl transition-colors">← Rebuild</button>
            <button onClick={onDashboard} className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-3 py-2 rounded-xl transition-colors">Dashboard</button>
          </div>
        </div>

        {/* Score cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Portfolio Score</p>
            <p className={`text-3xl font-black ${scoreColor}`}>{ps}</p>
            <p className="text-gray-600 text-xs">/100</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Sharpe Ratio</p>
            <p className={`text-3xl font-black tabular-nums ${result.weighted_sharpe > 0.8 ? 'text-green-400' : result.weighted_sharpe > 0.3 ? 'text-yellow-400' : 'text-red-400'}`}>
              {result.weighted_sharpe?.toFixed(2) ?? '—'}
            </p>
            <p className="text-gray-600 text-xs">weighted avg</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">1Y Avg Return</p>
            <p className={`text-3xl font-black tabular-nums ${(result.expected_return ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(result.expected_return ?? 0) >= 0 ? '+' : ''}{result.expected_return?.toFixed(1) ?? '0'}%
            </p>
            <p className="text-gray-600 text-xs">historical</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">Est. Volatility</p>
            <p className={`text-3xl font-black tabular-nums ${(result.expected_volatility ?? 0) > 30 ? 'text-red-400' : (result.expected_volatility ?? 0) > 20 ? 'text-yellow-400' : 'text-green-400'}`}>
              {result.expected_volatility?.toFixed(1) ?? '—'}%
            </p>
            <p className="text-gray-600 text-xs">annual</p>
          </div>
        </div>

        {/* Score breakdown */}
        {result.score_breakdown && Object.keys(result.score_breakdown).length > 0 && (
          <div className="card p-5 mb-5">
            <p className="text-white font-semibold text-sm mb-3">Score Breakdown (how {ps}/100 was computed)</p>
            <div className="space-y-2">
              {Object.entries(result.score_breakdown).map(([k, v]) => (
                <div key={k} className="flex items-center gap-3">
                  <span className="text-gray-400 text-xs w-40 shrink-0 capitalize">
                    {k.replace(/_/g, ' ')}
                  </span>
                  <div className="flex-1 bg-gray-800 rounded-full h-2">
                    <div className="h-2 rounded-full bg-blue-500" style={{ width: `${(v / 40) * 100}%` }} />
                  </div>
                  <span className="text-gray-400 text-xs tabular-nums w-14 text-right">
                    {v.toFixed(1)} pts
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Profile */}
        <div className={`border rounded-2xl p-5 mb-5 ${PROFILE_COLORS[profile.category] ?? 'text-gray-400 bg-gray-900 border-gray-700'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Shield size={15} />
            <span className="font-semibold text-sm">
              Risk Profile: {profile.category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              <span className="ml-2 opacity-60 text-xs font-normal">
                ({Math.round(profile.confidence * 100)}% confidence)
              </span>
            </span>
          </div>
          <p className="text-sm opacity-80 leading-relaxed">{profile.explanation}</p>
        </div>

        {/* AI Commentary */}
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={15} className="text-blue-400" />
            <h3 className="text-white font-semibold text-sm">AI Commentary</h3>
            <span className="ml-auto text-xs text-gray-600">Based on real 1-year market data</span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{result.ai_commentary}</p>
        </div>

        {/* Strengths + Warnings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {result.strengths.length > 0 && (
            <div className="card p-4 border-green-800/40 bg-green-950/10">
              <h3 className="text-green-400 font-semibold text-sm mb-3 flex items-center gap-2">
                <CheckCircle size={13} /> Verified Strengths
              </h3>
              {result.strengths.map((s, i) => (
                <p key={i} className="text-gray-300 text-xs flex gap-2 mb-1.5">
                  <span className="text-green-500 shrink-0">✓</span> {s}
                </p>
              ))}
            </div>
          )}
          {result.risk_warnings.length > 0 && (
            <div className="card p-4 border-yellow-800/40 bg-yellow-950/10">
              <h3 className="text-yellow-400 font-semibold text-sm mb-3 flex items-center gap-2">
                <AlertTriangle size={13} /> Risk Factors
              </h3>
              {result.risk_warnings.map((w, i) => (
                <p key={i} className="text-gray-300 text-xs flex gap-2 mb-1.5">
                  <span className="text-yellow-500 shrink-0">⚠</span> {w}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Sector allocation */}
        <div className="card p-5 mb-5">
          <h3 className="text-white font-semibold text-sm mb-4">Sector Allocation</h3>
          <div className="space-y-2.5">
            {result.sector_allocation.map(s => (
              <div key={s.sector} className="flex items-center gap-3">
                <span className="text-gray-400 text-xs w-28 shrink-0">{s.sector}</span>
                <div className="flex-1 bg-gray-800 rounded-full h-2">
                  <div className="h-2 rounded-full bg-blue-500" style={{ width: `${s.weight_pct}%` }} />
                </div>
                <span className="text-gray-400 text-xs tabular-nums w-10 text-right">
                  {s.weight_pct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Stocks */}
        <div>
          <h3 className="text-white font-semibold text-lg mb-4">
            Recommended Stocks ({result.stocks.length})
            <span className="ml-2 text-xs font-normal text-gray-500">
              sorted by composite score
            </span>
          </h3>
          <div className="space-y-2">
            {result.stocks.map((stock, i) => (
              <div key={stock.symbol} className="card overflow-hidden">
                <button
                  onClick={() => setExpandedStock(expandedStock === stock.symbol ? null : stock.symbol)}
                  className="w-full flex items-center gap-3 p-4 hover:bg-white/[0.02] transition-colors text-left"
                >
                  <div className="w-7 h-7 rounded-full bg-blue-600/20 flex items-center justify-center text-blue-400 text-xs font-bold shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-semibold text-sm">{stock.symbol}</span>
                      <span className="text-gray-500 text-xs truncate max-w-32">{stock.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${ROLE_BADGE[stock.role] ?? 'bg-gray-800 text-gray-400'}`}>
                        {stock.role}
                      </span>
                      <span className="text-xs text-gray-600 shrink-0">{stock.sector}</span>
                    </div>
                    {/* Mini metrics */}
                    <div className="flex gap-3 mt-1">
                      <span className={`text-xs tabular-nums ${stock.sharpe_estimate > 0.8 ? 'text-green-400' : stock.sharpe_estimate > 0.3 ? 'text-yellow-400' : 'text-gray-500'}`}>
                        Sh: {stock.sharpe_estimate.toFixed(2)}
                      </span>
                      <span className={`text-xs tabular-nums ${stock.momentum_1y >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        1Y: {stock.momentum_1y >= 0 ? '+' : ''}{stock.momentum_1y.toFixed(1)}%
                      </span>
                      <span className="text-xs text-gray-600 tabular-nums">
                        Vol: {stock.volatility.toFixed(1)}%
                      </span>
                      <span className="text-xs text-blue-400 tabular-nums">
                        Score: {stock.composite_score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-white font-bold tabular-nums text-sm">
                      {prefix}{stock.allocation_amount.toLocaleString('en-IN')}
                    </p>
                    <p className="text-gray-500 text-xs tabular-nums">{stock.allocation_pct}%</p>
                  </div>
                  <ChevronRight size={13} className={`text-gray-500 shrink-0 transition-transform ${expandedStock === stock.symbol ? 'rotate-90' : ''}`} />
                </button>

                {expandedStock === stock.symbol && (
                  <div className="border-t border-white/[0.04] px-4 pb-4 pt-3 space-y-3 animate-fade-in">
                    <p className="text-gray-300 text-sm leading-relaxed">{stock.why}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {[
                        { label: 'Sharpe Ratio',   value: stock.sharpe_estimate.toFixed(2), color: stock.sharpe_estimate > 0.8 ? 'text-green-400' : 'text-yellow-400' },
                        { label: '1Y Return',       value: `${stock.momentum_1y >= 0 ? '+' : ''}${stock.momentum_1y.toFixed(1)}%`, color: stock.momentum_1y >= 0 ? 'text-green-400' : 'text-red-400' },
                        { label: 'Max Drawdown',    value: `${stock.max_drawdown.toFixed(1)}%`, color: stock.max_drawdown > -20 ? 'text-green-400' : 'text-red-400' },
                        { label: 'Beta',            value: stock.beta.toFixed(2), color: 'text-blue-400' },
                        { label: 'Volatility',      value: `${stock.volatility.toFixed(1)}%`, color: stock.volatility < 20 ? 'text-green-400' : 'text-yellow-400' },
                        { label: 'Composite Score', value: `${stock.composite_score.toFixed(0)}/100`, color: 'text-blue-400' },
                        { label: 'Risk Level',      value: stock.risk_contribution, color: stock.risk_contribution === 'Low' ? 'text-green-400' : stock.risk_contribution === 'Medium' ? 'text-yellow-400' : 'text-red-400' },
                        { label: 'Sector',          value: stock.sector, color: 'text-gray-300' },
                      ].map(m => (
                        <div key={m.label} className="bg-gray-800/40 rounded-lg p-2.5">
                          <p className="text-gray-600 text-xs mb-0.5">{m.label}</p>
                          <p className={`text-sm font-semibold tabular-nums ${m.color}`}>{m.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <p className="text-gray-700 text-xs text-center mt-8">
          AI-generated using real market data for educational purposes only.
          Not financial advice. Past performance does not guarantee future results.
          Consult a SEBI-registered investment advisor before investing.
        </p>
      </div>
    </div>
  )
})