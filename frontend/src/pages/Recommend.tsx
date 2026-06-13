/**
 * AI Investment Advisor — Recommend.tsx
 * Full 6-step wizard + results with whole-share display
 * Whole shares only: "3 shares × Rs.1,160 = Rs.3,480"
 */
import {
  useState, useCallback, memo,
} from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Sparkles, AlertTriangle, CheckCircle, Info,
  BarChart3, Shield, Zap, Target, ArrowRight,
  RefreshCw, DollarSign, PieChart,
  Clock, Briefcase, ChevronDown, ChevronUp,
  ChevronLeft,
} from 'lucide-react'

const API = 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────

interface StockRec {
  symbol:             string
  name:               string
  sector:             string
  allocation_pct:     number
  allocation_amount:  number
  shares_to_buy?:     number
  price_per_share?:   number
  total_cost?:        number
  share_summary?:     string
  role:               string
  why:                string
  risk_contribution:  string
  momentum_score:     number
  sharpe_estimate:    number
  volatility:         number
  composite_score:    number
  momentum_1y:        number
  max_drawdown:       number
  beta:               number
}

interface RecommendationResult {
  profile: {
    category:          string
    confidence:        number
    explanation:       string
    equity_pct:        number
    volatility_target: number
  }
  stocks:                StockRec[]
  total_amount:          number
  total_invested?:       number
  uninvested_cash?:      number
  expected_return:       number
  expected_volatility:   number
  portfolio_score:       number
  diversification_score: number
  weighted_sharpe:       number
  weighted_beta:         number
  ai_commentary:         string
  sector_allocation:     { sector: string; weight_pct: number }[]
  risk_warnings:         string[]
  strengths:             string[]
  data_note:             string
  score_breakdown?:      Record<string, number>
  warnings?:             string[]
  n_sectors?:            number   // fix: add missing field
}

// ── Constants ─────────────────────────────────────────────────

const PRESETS = [10_000, 50_000, 1_00_000, 5_00_000, 10_00_000]

const MARKETS = [
  { value: 'india', label: 'India (NSE)',      flag: '🇮🇳' },
  { value: 'us',    label: 'US (NYSE/NASDAQ)', flag: '🇺🇸' },
  { value: 'both',  label: 'Global Mix',       flag: '🌏' },
]

const HORIZONS = [
  { value: 'short',  label: 'Short',  desc: '< 1 year',  icon: <Zap size={16} /> },
  { value: 'medium', label: 'Medium', desc: '1–3 years', icon: <Clock size={16} /> },
  { value: 'long',   label: 'Long',   desc: '3+ years',  icon: <Target size={16} /> },
]

const GOALS = [
  { value: 'wealth_creation', label: 'Wealth Creation', icon: '💰' },
  { value: 'passive_growth',  label: 'Passive Growth',  icon: '📈' },
  { value: 'high_growth',     label: 'High Growth',     icon: '🚀' },
  { value: 'retirement',      label: 'Retirement',      icon: '🏖️' },
  { value: 'dividend_income', label: 'Dividend Income', icon: '💵' },
  { value: 'low_risk',        label: 'Low Risk',        icon: '🛡️' },
]

const SECTORS = [
  'Technology', 'Banking', 'Finance', 'Healthcare',
  'Energy', 'FMCG', 'Auto', 'Infra', 'IT',
  'Pharma', 'Consumer', 'Realty',
]

const STOCK_COUNTS = [5, 6, 7, 8, 10]

const ROLE_BADGE: Record<string, string> = {
  growth:    'bg-green-900/30 text-green-400',
  stability: 'bg-blue-900/30 text-blue-400',
  recovery:  'bg-orange-900/30 text-orange-400',
  balanced:  'bg-purple-900/30 text-purple-400',
}

const PROFILE_COLOR: Record<string, string> = {
  conservative: 'text-blue-400',
  moderate:     'text-green-400',
  aggressive:   'text-orange-400',
  high_growth:  'text-red-400',
}

// ── Helpers ───────────────────────────────────────────────────

function fmtInr(v: number): string {
  if (v >= 1_00_00_000) return `Rs.${(v / 1_00_00_000).toFixed(2)} Cr`
  if (v >= 1_00_000)    return `Rs.${(v / 1_00_000).toFixed(2)}L`
  return `Rs.${v.toLocaleString('en-IN')}`
}

function ScoreBar({ value, max = 100, color = 'bg-blue-500' }: {
  value: number; max?: number; color?: string
}) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(100, (value / max) * 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 tabular-nums w-8 text-right">{value}</span>
    </div>
  )
}

// ── Step components ───────────────────────────────────────────

// fix: removed unused `total` prop
function StepIndicator({ current }: { current: number }) {
  const labels = ['Capital', 'Market', 'Horizon', 'Goal', 'Sectors', 'Stocks']
  return (
    <div className="flex items-center justify-center gap-1 mb-8 flex-wrap">
      {labels.map((lbl, i) => {
        const step   = i + 1
        const active = step === current
        const done   = step < current
        return (
          <div key={lbl} className="flex items-center">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' :
              done   ? 'bg-green-900/40 text-green-400' :
                       'bg-gray-800/60 text-gray-600'
            }`}>
              {done ? <CheckCircle size={11} /> : (
                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  active ? 'bg-white/20' : 'bg-gray-700'
                }`}>{step}</span>
              )}
              {lbl}
            </div>
            {i < labels.length - 1 && (
              <div className={`w-4 h-px mx-0.5 ${done ? 'bg-green-700' : 'bg-gray-800'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function WizardCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-xl mx-auto">
      <div className="card p-6 shadow-2xl shadow-black/40">
        {children}
      </div>
    </div>
  )
}

function NavButtons({
  onBack, onNext, nextLabel = 'Continue →',
  nextDisabled = false, loading = false,
}: {
  onBack?: () => void; onNext: () => void
  nextLabel?: string; nextDisabled?: boolean; loading?: boolean
}) {
  return (
    <div className="flex items-center justify-between mt-6">
      {onBack ? (
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-gray-500 hover:text-white text-sm transition-colors">
          <ChevronLeft size={15} /> Back
        </button>
      ) : <div />}
      <button
        onClick={onNext}
        disabled={nextDisabled || loading}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-blue-600/20"
      >
        {loading ? (
          <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          Building portfolio...</>
        ) : nextLabel}
      </button>
    </div>
  )
}

// ── Step 1: Capital ───────────────────────────────────────────

const StepCapital = memo(function StepCapital({
  amount, setAmount, onNext,
}: { amount: string; setAmount: (v: string) => void; onNext: () => void }) {
  const num     = parseFloat(amount) || 0
  const isValid = num >= 5000
  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 bg-yellow-600/20 rounded-xl flex items-center justify-center">
          <DollarSign size={17} className="text-yellow-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Investment Amount</h2>
          <p className="text-gray-500 text-xs">How much would you like to invest?</p>
        </div>
      </div>

      <div className="relative mb-3">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-semibold">₹</div>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          className="w-full bg-gray-800/60 border border-gray-700 focus:border-blue-500 text-white pl-9 pr-4 py-3.5 rounded-xl text-xl font-bold outline-none transition-colors tabular-nums"
          placeholder="100000"
          min="5000"
        />
      </div>

      {num > 0 && (
        <p className="text-blue-400 text-sm font-medium mb-4 tabular-nums">{fmtInr(num)}</p>
      )}
      {num > 0 && num < 5000 && (
        <p className="text-red-400 text-xs mb-3">Minimum investment is Rs.5,000</p>
      )}

      <div className="flex flex-wrap gap-2 mb-2">
        {PRESETS.map(p => (
          <button
            key={p}
            onClick={() => setAmount(String(p))}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              num === p
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {fmtInr(p)}
          </button>
        ))}
      </div>

      <NavButtons onNext={onNext} nextDisabled={!isValid} />
    </WizardCard>
  )
})

// ── Step 2: Market ────────────────────────────────────────────

const StepMarket = memo(function StepMarket({
  market, setMarket, onBack, onNext,
}: { market: string; setMarket: (v: string) => void; onBack: () => void; onNext: () => void }) {
  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-blue-600/20 rounded-xl flex items-center justify-center">
          <BarChart3 size={17} className="text-blue-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Which market?</h2>
          <p className="text-gray-500 text-xs">Select where to invest</p>
        </div>
      </div>

      <div className="space-y-2 mb-2">
        {MARKETS.map(m => (
          <button
            key={m.value}
            onClick={() => setMarket(m.value)}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all text-left ${
              market === m.value
                ? 'border-blue-600 bg-blue-950/20'
                : 'border-gray-700/60 hover:border-gray-600 bg-gray-800/30'
            }`}
          >
            <span className="text-2xl">{m.flag}</span>
            <div>
              <p className="text-white font-medium text-sm">{m.label}</p>
              {m.value === 'india' && <p className="text-gray-500 text-xs">2300+ NSE stocks • INR</p>}
              {m.value === 'us'    && <p className="text-gray-500 text-xs">S&P 500 universe • USD</p>}
              {m.value === 'both'  && <p className="text-gray-500 text-xs">Diversified global exposure</p>}
            </div>
            {market === m.value && <CheckCircle size={16} className="text-blue-400 ml-auto" />}
          </button>
        ))}
      </div>

      <NavButtons onBack={onBack} onNext={onNext} nextDisabled={!market} />
    </WizardCard>
  )
})

// ── Step 3: Horizon ───────────────────────────────────────────

const StepHorizon = memo(function StepHorizon({
  horizon, setHorizon, onBack, onNext,
}: { horizon: string; setHorizon: (v: string) => void; onBack: () => void; onNext: () => void }) {
  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-purple-600/20 rounded-xl flex items-center justify-center">
          <Clock size={17} className="text-purple-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Investment Horizon</h2>
          <p className="text-gray-500 text-xs">How long will you stay invested?</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-2">
        {HORIZONS.map(h => (
          <button
            key={h.value}
            onClick={() => setHorizon(h.value)}
            className={`flex flex-col items-center gap-2 py-4 px-2 rounded-xl border transition-all ${
              horizon === h.value
                ? 'border-purple-600 bg-purple-950/20'
                : 'border-gray-700/60 hover:border-gray-600 bg-gray-800/30'
            }`}
          >
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              horizon === h.value ? 'bg-purple-600/30 text-purple-400' : 'bg-gray-700 text-gray-400'
            }`}>
              {h.icon}
            </div>
            <div className="text-center">
              <p className={`font-semibold text-sm ${horizon === h.value ? 'text-white' : 'text-gray-400'}`}>
                {h.label}
              </p>
              <p className="text-gray-600 text-xs">{h.desc}</p>
            </div>
          </button>
        ))}
      </div>

      <NavButtons onBack={onBack} onNext={onNext} nextDisabled={!horizon} />
    </WizardCard>
  )
})

// ── Step 4: Goal ──────────────────────────────────────────────

const StepGoal = memo(function StepGoal({
  goal, setGoal, onBack, onNext,
}: { goal: string; setGoal: (v: string) => void; onBack: () => void; onNext: () => void }) {
  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-green-600/20 rounded-xl flex items-center justify-center">
          <Target size={17} className="text-green-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Investment Goal</h2>
          <p className="text-gray-500 text-xs">What are you investing for?</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        {GOALS.map(g => (
          <button
            key={g.value}
            onClick={() => setGoal(g.value)}
            className={`flex items-center gap-2.5 px-3.5 py-3 rounded-xl border transition-all text-left ${
              goal === g.value
                ? 'border-green-600 bg-green-950/20'
                : 'border-gray-700/60 hover:border-gray-600 bg-gray-800/30'
            }`}
          >
            <span className="text-xl">{g.icon}</span>
            <span className={`text-sm font-medium ${goal === g.value ? 'text-white' : 'text-gray-400'}`}>
              {g.label}
            </span>
          </button>
        ))}
      </div>

      <NavButtons onBack={onBack} onNext={onNext} nextDisabled={!goal} />
    </WizardCard>
  )
})

// ── Step 5: Sectors ───────────────────────────────────────────

const StepSectors = memo(function StepSectors({
  selected, setSelected, onBack, onNext,
}: {
  selected: string[]; setSelected: (v: string[]) => void
  onBack: () => void; onNext: () => void
}) {
  const toggle = (s: string) =>
    setSelected(
      selected.includes(s) ? selected.filter(x => x !== s) : [...selected, s]
    )

  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-orange-600/20 rounded-xl flex items-center justify-center">
          <PieChart size={17} className="text-orange-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Preferred Sectors</h2>
          <p className="text-gray-500 text-xs">Pick 2–5 sectors (optional — skip to use defaults)</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {SECTORS.map(s => (
          <button
            key={s}
            onClick={() => toggle(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
              selected.includes(s)
                ? 'bg-orange-600/20 border-orange-600/60 text-orange-300'
                : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-500'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {selected.length > 0 ? (
        <div className="flex items-center gap-2 text-xs text-green-400 mb-3">
          <CheckCircle size={12} />
          {selected.length} sector{selected.length > 1 ? 's' : ''} selected: {selected.join(', ')}
        </div>
      ) : (
        <p className="text-gray-600 text-xs mb-3">
          No sectors selected — AI will use smart defaults for your goal.
        </p>
      )}

      <NavButtons
        onBack={onBack}
        onNext={onNext}
        nextLabel={selected.length === 0 ? 'Skip & Continue →' : 'Continue →'}
      />
    </WizardCard>
  )
})

// ── Step 6: Stock Count ───────────────────────────────────────

const StepStockCount = memo(function StepStockCount({
  count, setCount, onBack, onGenerate, loading,
}: {
  count: number; setCount: (v: number) => void
  onBack: () => void; onGenerate: () => void; loading: boolean
}) {
  return (
    <WizardCard>
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-blue-600/20 rounded-xl flex items-center justify-center">
          <Briefcase size={17} className="text-blue-400" />
        </div>
        <div>
          <h2 className="text-white font-bold">Number of Stocks</h2>
          <p className="text-gray-500 text-xs">How many stocks in your portfolio?</p>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap mb-5">
        {STOCK_COUNTS.map(n => (
          <button
            key={n}
            onClick={() => setCount(n)}
            className={`flex-1 py-3 rounded-xl border font-bold text-lg transition-all ${
              count === n
                ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-600/20'
                : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-500'
            }`}
          >
            {n}
          </button>
        ))}
      </div>

      <div className="bg-gray-800/40 rounded-xl p-3 mb-5">
        <p className="text-gray-400 text-xs leading-relaxed">
          <span className="text-white font-semibold">India rule:</span> Only whole number shares.
          We allocate your capital optimally across {count} stocks and show you
          exactly how many shares to buy at today's prices.
          Uninvested cash is shown separately.
        </p>
      </div>

      <NavButtons
        onBack={onBack}
        onNext={onGenerate}
        nextLabel="Build My Portfolio →"
        loading={loading}
      />
    </WizardCard>
  )
})

// ── Loading screen ────────────────────────────────────────────

// fix: removed unused `amount` prop
function LoadingScreen() {
  return (
    <div className="max-w-xl mx-auto text-center py-16">
      <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
        <Sparkles size={28} className="text-blue-400 animate-pulse" />
      </div>
      <h2 className="text-white text-xl font-bold mb-2">Building Your Portfolio</h2>
      <p className="text-gray-500 text-sm mb-8">
        Scoring real market data · Enforcing whole-share rules · Optimising allocation
      </p>
      <div className="space-y-2 text-left max-w-xs mx-auto">
        {[
          'Fetching NSE universe (2300+ stocks)...',
          'Scoring by Sharpe, momentum, drawdown...',
          'Fetching live share prices...',
          'Calculating whole-share allocations...',
          'Optimising for your budget...',
        ].map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-xs text-gray-500">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
            {step}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Result screen ─────────────────────────────────────────────

function ResultScreen({
  result, amount, onReset,
}: { result: RecommendationResult; amount: number; onReset: () => void }) {
  const [expandedStock, setExpandedStock] = useState<string | null>(null)
  const [showBreakdown, setShowBreakdown] = useState(false)

  const isIndia = (result.stocks[0]?.symbol ?? '').endsWith('.NS') ||
                  (result.stocks[0]?.symbol ?? '').endsWith('.BO')
  const prefix  = isIndia ? 'Rs.' : '$'
  const locale  = isIndia ? 'en-IN' : 'en-US'

  const totalInvested  = result.total_invested
    ?? result.stocks.reduce((a, s) => a + (s.total_cost ?? s.allocation_amount), 0)
  const uninvestedCash = result.uninvested_cash ?? (amount - totalInvested)
  const investedPct    = amount > 0 ? Math.round((totalInvested / amount) * 100) : 0

  // fix: use n_sectors from result if available, else fall back to sector_allocation length
  const nSectors = result.n_sectors ?? result.sector_allocation.length

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles size={16} className="text-blue-400" />
            <span className="text-blue-400 text-sm font-medium">AI Portfolio Ready</span>
          </div>
          <h2 className="text-white text-2xl font-bold">Your Portfolio</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {result.stocks.length} stocks · {nSectors} sectors ·{' '}
            <span className={PROFILE_COLOR[result.profile.category] ?? 'text-gray-400'}>
              {result.profile.category} profile
            </span>
          </p>
        </div>
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-gray-500 hover:text-white text-sm border border-gray-700/60 px-3 py-1.5 rounded-xl transition-colors"
        >
          <RefreshCw size={13} /> Rebuild
        </button>
      </div>

      {/* Capital summary */}
      <div className="card p-5">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-gray-500 text-xs mb-1">Requested</p>
            <p className="text-white font-bold text-lg tabular-nums">
              {prefix}{amount.toLocaleString(locale)}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs mb-1">Investing in stocks</p>
            <p className="text-green-400 font-bold text-lg tabular-nums">
              {prefix}{Math.round(totalInvested).toLocaleString(locale)}
            </p>
            <div className="mt-1.5 bg-gray-800 rounded-full h-1 overflow-hidden w-full">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{ width: `${investedPct}%` }}
              />
            </div>
          </div>
          <div>
            <p className="text-gray-500 text-xs mb-1">Uninvested cash</p>
            <p className={`font-bold text-lg tabular-nums ${uninvestedCash > 0 ? 'text-yellow-400' : 'text-gray-500'}`}>
              {prefix}{Math.round(Math.max(0, uninvestedCash)).toLocaleString(locale)}
            </p>
            {uninvestedCash > 0 && (
              <p className="text-gray-600 text-xs mt-0.5">Add to next SIP</p>
            )}
          </div>
        </div>

        {uninvestedCash > 1 && (
          <div className="mt-4 bg-yellow-950/20 border border-yellow-800/30 rounded-xl px-3 py-2.5 flex items-start gap-2">
            <Info size={13} className="text-yellow-400 shrink-0 mt-0.5" />
            <p className="text-yellow-300/80 text-xs leading-relaxed">
              <strong>Why is there uninvested cash?</strong> In India, shares can only be purchased
              in whole numbers. After buying whole shares for each stock,{' '}
              {prefix}{Math.round(uninvestedCash).toLocaleString(locale)} remains.
              You can add this to your next SIP or invest in an additional stock.
            </p>
          </div>
        )}
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: 'Portfolio Score',
            value: `${result.portfolio_score}/100`,
            color: result.portfolio_score >= 70 ? 'text-green-400'
                 : result.portfolio_score >= 50 ? 'text-yellow-400' : 'text-red-400',
            sub: result.portfolio_score >= 70 ? 'Strong'
               : result.portfolio_score >= 50 ? 'Moderate' : 'Weak',
          },
          {
            label: 'Diversification',
            value: `${result.diversification_score}/100`,
            color: result.diversification_score >= 60 ? 'text-green-400' : 'text-yellow-400',
            sub:   `${result.sector_allocation.length} sectors`,
          },
          {
            label: 'Weighted Sharpe',
            value: result.weighted_sharpe.toFixed(2),
            color: result.weighted_sharpe > 1 ? 'text-green-400'
                 : result.weighted_sharpe > 0 ? 'text-yellow-400' : 'text-red-400',
            sub:   result.weighted_sharpe > 1 ? 'Excellent'
                 : result.weighted_sharpe > 0 ? 'Good' : 'Below avg',
          },
          {
            label: 'Expected Return',
            value: `${result.expected_return >= 0 ? '+' : ''}${result.expected_return.toFixed(1)}%`,
            color: result.expected_return >= 0 ? 'text-green-400' : 'text-red-400',
            sub:   '1Y historical avg',
          },
        ].map(card => (
          <div key={card.label} className="card p-4">
            <p className="text-gray-500 text-xs mb-1">{card.label}</p>
            <p className={`text-xl font-bold tabular-nums ${card.color}`}>{card.value}</p>
            <p className="text-gray-600 text-xs mt-0.5">{card.sub}</p>
          </div>
        ))}
      </div>

      {/* AI Commentary */}
      {result.ai_commentary && (
        <div className="card p-5 border-l-4 border-blue-600">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={14} className="text-blue-400" />
            <span className="text-blue-400 text-xs font-semibold uppercase tracking-wide">AI Analysis</span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{result.ai_commentary}</p>
        </div>
      )}

      {/* Strengths + Risk Warnings */}
      {(result.strengths?.length > 0 || result.risk_warnings?.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {result.strengths?.length > 0 && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle size={14} className="text-green-400" />
                <span className="text-green-400 text-xs font-semibold">Strengths</span>
              </div>
              <ul className="space-y-2">
                {result.strengths.slice(0, 3).map((s, i) => (
                  <li key={i} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                    <span className="text-green-600 mt-0.5 shrink-0">›</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.risk_warnings?.length > 0 && (
            <div className="card p-4 border-yellow-800/30">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={14} className="text-yellow-400" />
                <span className="text-yellow-400 text-xs font-semibold">Watch out</span>
              </div>
              <ul className="space-y-2">
                {result.risk_warnings.slice(0, 3).map((w, i) => (
                  <li key={i} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                    <span className="text-yellow-600 mt-0.5 shrink-0">›</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* fix: safe optional chaining on warnings */}
      {(result.warnings?.length ?? 0) > 0 && (
        <div className="bg-orange-950/20 border border-orange-800/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={13} className="text-orange-400" />
            <span className="text-orange-400 text-xs font-semibold">Stocks removed (unaffordable)</span>
          </div>
          {result.warnings?.map((w, i) => (
            <p key={i} className="text-gray-400 text-xs">{w}</p>
          ))}
        </div>
      )}

      {/* Stock list */}
      <div>
        <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
          Stock Allocation
          <span className="text-gray-600 text-sm font-normal">
            — {result.stocks.length} stocks, whole shares only
          </span>
        </h3>

        <div className="space-y-2">
          {result.stocks.map((stock, i) => {
            const isOpen = expandedStock === stock.symbol
            const cost   = stock.total_cost ?? stock.allocation_amount

            return (
              <div key={stock.symbol} className="card overflow-hidden">
                <button
                  onClick={() => setExpandedStock(isOpen ? null : stock.symbol)}
                  className="w-full flex items-center gap-3 p-4 hover:bg-white/[0.02] transition-colors text-left"
                >
                  <div className="w-6 h-6 rounded-full bg-gray-800 flex items-center justify-center text-gray-500 text-xs font-bold shrink-0">
                    {i + 1}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-bold text-sm">{stock.symbol}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize shrink-0 ${ROLE_BADGE[stock.role] ?? 'bg-gray-800 text-gray-400'}`}>
                        {stock.role}
                      </span>
                      <span className="text-gray-500 text-xs">{stock.sector}</span>
                    </div>

                    {stock.shares_to_buy && stock.price_per_share ? (
                      <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                        <span className="text-blue-400 text-xs font-bold tabular-nums">
                          {stock.shares_to_buy} share{stock.shares_to_buy > 1 ? 's' : ''}
                        </span>
                        <span className="text-gray-600 text-xs">×</span>
                        <span className="text-gray-400 text-xs tabular-nums">
                          {prefix}{stock.price_per_share.toLocaleString(locale)}
                        </span>
                        <span className="text-gray-600 text-xs">=</span>
                        <span className="text-green-400 text-xs font-bold tabular-nums">
                          {prefix}{cost.toLocaleString(locale)}
                        </span>
                      </div>
                    ) : (
                      <div className="flex gap-3 mt-1">
                        <span className={`text-xs tabular-nums ${stock.sharpe_estimate > 0.8 ? 'text-green-400' : 'text-yellow-400'}`}>
                          Sharpe {stock.sharpe_estimate.toFixed(2)}
                        </span>
                        <span className={`text-xs tabular-nums ${stock.momentum_1y >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {stock.momentum_1y >= 0 ? '+' : ''}{stock.momentum_1y.toFixed(1)}% 1Y
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="text-right shrink-0 mr-1">
                    <p className="text-white font-bold tabular-nums text-sm">
                      {prefix}{cost.toLocaleString(locale)}
                    </p>
                    <p className="text-gray-600 text-xs tabular-nums">{stock.allocation_pct}%</p>
                  </div>

                  {isOpen
                    ? <ChevronUp   size={13} className="text-gray-500 shrink-0" />
                    : <ChevronDown size={13} className="text-gray-500 shrink-0" />
                  }
                </button>

                {isOpen && (
                  <div className="border-t border-white/[0.04] px-4 pb-4 pt-3 space-y-4">

                    {stock.shares_to_buy && stock.price_per_share && (
                      <div className="bg-blue-950/20 border border-blue-800/30 rounded-xl p-4">
                        <p className="text-blue-400 text-xs font-bold uppercase tracking-wide mb-2">
                          Purchase Plan
                        </p>
                        <p className="text-white font-bold text-base">
                          Buy {stock.shares_to_buy} share{stock.shares_to_buy > 1 ? 's' : ''} of{' '}
                          {stock.symbol.replace('.NS', '').replace('.BO', '')}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-sm flex-wrap">
                          <span className="text-gray-400 tabular-nums">
                            {prefix}{stock.price_per_share.toLocaleString(locale)} / share
                          </span>
                          <span className="text-gray-600">×</span>
                          <span className="text-gray-400">{stock.shares_to_buy}</span>
                          <span className="text-gray-600">=</span>
                          <span className="text-green-400 font-bold tabular-nums">
                            {prefix}{cost.toLocaleString(locale)}
                          </span>
                        </div>
                      </div>
                    )}

                    <p className="text-gray-300 text-sm leading-relaxed">{stock.why}</p>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {[
                        { label: 'Sharpe Ratio',  value: stock.sharpe_estimate.toFixed(2),  color: stock.sharpe_estimate > 0.8 ? 'text-green-400' : stock.sharpe_estimate > 0.3 ? 'text-yellow-400' : 'text-red-400' },
                        { label: '1Y Return',      value: `${stock.momentum_1y >= 0 ? '+' : ''}${stock.momentum_1y.toFixed(1)}%`, color: stock.momentum_1y >= 0 ? 'text-green-400' : 'text-red-400' },
                        { label: 'Max Drawdown',   value: `${stock.max_drawdown.toFixed(1)}%`, color: stock.max_drawdown > -20 ? 'text-green-400' : 'text-red-400' },
                        { label: 'Volatility',     value: `${stock.volatility.toFixed(1)}%`,   color: stock.volatility < 18 ? 'text-green-400' : stock.volatility < 28 ? 'text-yellow-400' : 'text-red-400' },
                        { label: 'Beta',           value: stock.beta.toFixed(2),               color: 'text-blue-400' },
                        { label: 'Risk Level',     value: stock.risk_contribution,             color: stock.risk_contribution === 'Low' ? 'text-green-400' : stock.risk_contribution === 'Medium' ? 'text-yellow-400' : 'text-red-400' },
                        { label: 'Score',          value: `${stock.composite_score.toFixed(0)}/100`, color: 'text-blue-400' },
                        { label: 'Allocation',     value: `${stock.allocation_pct}%`,          color: 'text-gray-300' },
                      ].map(m => (
                        <div key={m.label} className="bg-gray-800/40 rounded-xl p-3">
                          <p className="text-gray-600 text-xs mb-1">{m.label}</p>
                          <p className={`font-bold text-sm tabular-nums ${m.color}`}>{m.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Uninvested cash callout */}
      {uninvestedCash > 100 && (
        <div className="card p-4 border-yellow-800/40 bg-yellow-950/10">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              <Info size={15} className="text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-yellow-400 font-semibold text-sm">
                  {prefix}{Math.round(uninvestedCash).toLocaleString(locale)} uninvested
                </p>
                <p className="text-gray-500 text-xs mt-0.5">
                  Cannot be invested in fractional shares.
                  Keep in savings account or add to your next SIP date.
                </p>
              </div>
            </div>
            <p className="text-yellow-400 font-bold tabular-nums shrink-0">
              {prefix}{Math.round(uninvestedCash).toLocaleString(locale)}
            </p>
          </div>
        </div>
      )}

      {/* Sector allocation */}
      <div className="card p-5">
        <h4 className="text-white font-semibold text-sm mb-4 flex items-center gap-2">
          <PieChart size={14} className="text-blue-400" />
          Sector Allocation
        </h4>
        <div className="space-y-2.5">
          {result.sector_allocation.map(s => (
            <div key={s.sector} className="flex items-center gap-3">
              <span className="text-gray-400 text-xs w-24 shrink-0">{s.sector}</span>
              <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${s.weight_pct}%` }}
                />
              </div>
              <span className="text-gray-500 text-xs w-10 text-right tabular-nums">
                {s.weight_pct.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Score breakdown */}
      {result.score_breakdown && Object.keys(result.score_breakdown).length > 0 && (
        <div className="card p-5">
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="flex items-center justify-between w-full text-left"
          >
            <h4 className="text-white font-semibold text-sm flex items-center gap-2">
              <BarChart3 size={14} className="text-purple-400" />
              Score Breakdown
            </h4>
            {showBreakdown
              ? <ChevronUp   size={14} className="text-gray-500" />
              : <ChevronDown size={14} className="text-gray-500" />
            }
          </button>

          {showBreakdown && (
            <div className="mt-4 space-y-3">
              {Object.entries(result.score_breakdown).map(([key, val]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-gray-500 tabular-nums">{val.toFixed(1)}</span>
                  </div>
                  <ScoreBar value={val} max={30} color="bg-purple-500" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Data note */}
      <div className="flex items-start gap-2 px-1">
        <Info size={12} className="text-gray-700 shrink-0 mt-0.5" />
        <p className="text-gray-700 text-xs">{result.data_note}</p>
      </div>

      {/* Profile explanation */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Shield size={14} className={PROFILE_COLOR[result.profile.category] ?? 'text-gray-400'} />
          <span className={`text-sm font-semibold capitalize ${PROFILE_COLOR[result.profile.category] ?? 'text-gray-400'}`}>
            {result.profile.category} Profile
          </span>
          <span className="text-gray-600 text-xs ml-auto tabular-nums">
            {Math.round(result.profile.confidence * 100)}% confidence
          </span>
        </div>
        <p className="text-gray-400 text-xs leading-relaxed">{result.profile.explanation}</p>
      </div>

      {/* CTAs */}
      <div className="flex gap-3">
        <button
          onClick={onReset}
          className="flex-1 flex items-center justify-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white py-3 rounded-xl text-sm font-medium transition-all"
        >
          <RefreshCw size={15} /> Rebuild Portfolio
        </button>
        <button
          onClick={() => { window.location.href = '/dashboard' }}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-blue-600/20"
        >
          Analyse My Holdings <ArrowRight size={15} />
        </button>
      </div>

    </div>
  )
}

// ── Main component ────────────────────────────────────────────

export default function Recommend() {
  const navigate = useNavigate()

  const [step,       setStep]       = useState(1)
  const [amount,     setAmount]     = useState('100000')
  const [market,     setMarket]     = useState('india')
  const [horizon,    setHorizon]    = useState('medium')
  const [goal,       setGoal]       = useState('wealth_creation')
  const [sectors,    setSectors]    = useState<string[]>([])
  const [stockCount, setStockCount] = useState(7)
  const [loading,    setLoading]    = useState(false)
  const [result,     setResult]     = useState<RecommendationResult | null>(null)
  const [error,      setError]      = useState<string | null>(null)

  const numAmount = parseFloat(amount) || 0

  const generate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post(
        `${API}/api/recommendation/generate`,
        {
          amount:            numAmount,
          goal,
          horizon,
          market,
          preferred_sectors: sectors,
          n_stocks_min:      stockCount - 1,
          n_stocks_max:      stockCount + 1,
        },
        { timeout: 120_000 }
      )
      if (res.data.error) {
        setError(res.data.error)
      } else {
        setResult(res.data)
      }
    } catch (e: any) {
      setError(
        e.response?.data?.detail ||
        e.message ||
        'Failed to generate recommendation. Try again.'
      )
    } finally {
      setLoading(false)
    }
  }, [numAmount, goal, horizon, market, sectors, stockCount])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setStep(1)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-4xl mx-auto px-4 py-8 md:py-12">

        {!result && !loading && (
          <div className="text-center mb-8">
            <button
              onClick={() => navigate('/')}
              className="text-gray-600 hover:text-gray-400 text-sm mb-4 block mx-auto"
            >
              ← Back
            </button>
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="w-10 h-10 bg-blue-600/20 border border-blue-700/40 rounded-2xl flex items-center justify-center">
                <Sparkles size={20} className="text-blue-400" />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">AI Investment Advisor</h1>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Build your portfolio · Powered by real market data · Scored on Sharpe, momentum &amp; drawdown ·{' '}
              <span className="text-blue-400">Whole shares only</span>
            </p>
          </div>
        )}

        {result ? (
          <ResultScreen result={result} amount={numAmount} onReset={reset} />
        ) : loading ? (
          <LoadingScreen />
        ) : (
          <>
            {/* fix: removed unused `total` prop */}
            <StepIndicator current={step} />

            {error && (
              <div className="max-w-xl mx-auto mb-4 flex items-start gap-2 bg-red-950/30 border border-red-800 text-red-400 text-sm px-4 py-3 rounded-xl">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {step === 1 && (
              <StepCapital amount={amount} setAmount={setAmount} onNext={() => setStep(2)} />
            )}
            {step === 2 && (
              <StepMarket market={market} setMarket={setMarket} onBack={() => setStep(1)} onNext={() => setStep(3)} />
            )}
            {step === 3 && (
              <StepHorizon horizon={horizon} setHorizon={setHorizon} onBack={() => setStep(2)} onNext={() => setStep(4)} />
            )}
            {step === 4 && (
              <StepGoal goal={goal} setGoal={setGoal} onBack={() => setStep(3)} onNext={() => setStep(5)} />
            )}
            {step === 5 && (
              <StepSectors selected={sectors} setSelected={setSectors} onBack={() => setStep(4)} onNext={() => setStep(6)} />
            )}
            {step === 6 && (
              <StepStockCount count={stockCount} setCount={setStockCount} onBack={() => setStep(5)} onGenerate={generate} loading={loading} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
