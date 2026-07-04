/**
 * components/PortfolioScoreCard.tsx — Complete file.
 * Fixed: all numeric fields now null-safe via safeNum() before .toFixed()/math.
 */
import { Shield, TrendingUp, PieChart, Zap } from 'lucide-react'

interface ScoreBreakdown {
  diversification_score?: number | null
  momentum_score?:        number | null
  risk_score?:             number | null
  quality_score?:          number | null
}
interface PortfolioScore {
  total_score?: number | null
  grade?:       string | null
  grade_color?: string | null
  breakdown?:   ScoreBreakdown | null
}
interface Props {
  insights:  { portfolio_score?: PortfolioScore | null; [key: string]: any } | null
  className?: string
}

function safeNum(v: unknown, fallback = 0): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

const GRADE_CONFIG: Record<string, { bg: string; border: string; text: string; label: string }> = {
  'A+': { bg: 'bg-green-950/40',  border: 'border-green-700/60',  text: 'text-green-300',  label: 'Excellent' },
  A:    { bg: 'bg-green-950/30',  border: 'border-green-800/50',  text: 'text-green-400',  label: 'Strong' },
  B:    { bg: 'bg-blue-950/30',   border: 'border-blue-800/50',   text: 'text-blue-400',   label: 'Good' },
  C:    { bg: 'bg-yellow-950/30', border: 'border-yellow-800/50', text: 'text-yellow-400', label: 'Moderate' },
  D:    { bg: 'bg-orange-950/30', border: 'border-orange-800/50', text: 'text-orange-400', label: 'Needs Work' },
  F:    { bg: 'bg-red-950/30',    border: 'border-red-800/50',    text: 'text-red-400',    label: 'Poor' },
}

function MiniBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex-1 bg-gray-800/60 rounded-full h-1.5 overflow-hidden">
      <div className={`h-full ${color} rounded-full transition-all duration-700`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  )
}

export default function PortfolioScoreCard({ insights, className = '' }: Props) {
  const ps = insights?.portfolio_score
  if (!ps) return null

  const rawGrade = (ps.grade ?? 'B').toString()
  const grade    = (rawGrade.replace('text-', '').split('-')[0] || 'B').toUpperCase()
  const config   = GRADE_CONFIG[grade] ?? GRADE_CONFIG['B']
  const score    = Math.round(safeNum(ps.total_score))
  const bd       = ps.breakdown ?? {}

  const subScores = [
    { label: 'Diversification', value: safeNum(bd.diversification_score) * 100, icon: <PieChart size={11} />,   color: 'bg-blue-500' },
    { label: 'Momentum',        value: safeNum(bd.momentum_score) * 100,         icon: <TrendingUp size={11} />, color: 'bg-green-500' },
    { label: 'Risk Quality',    value: safeNum(bd.risk_score) * 100,             icon: <Shield size={11} />,     color: 'bg-purple-500' },
  ].filter(s => s.value > 0)

  return (
    <div className={`border rounded-2xl p-5 ${config.bg} ${config.border} ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap size={15} className={config.text} />
          <span className="text-white font-semibold text-sm">Portfolio Health</span>
        </div>
        <span className="text-gray-500 text-xs">AI Score</span>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black border ${config.bg} ${config.border}`}>
          <span className={config.text}>{grade}</span>
        </div>
        <div>
          <p className={`text-4xl font-black tabular-nums ${config.text}`}>{score}</p>
          <p className="text-gray-500 text-xs">out of 100 · {config.label}</p>
        </div>
      </div>

      {subScores.length > 0 && (
        <div className="space-y-2">
          {subScores.map(s => (
            <div key={s.label} className="flex items-center gap-2">
              <span className="text-gray-500">{s.icon}</span>
              <span className="text-gray-500 text-xs w-24 shrink-0">{s.label}</span>
              <MiniBar value={s.value} color={s.color} />
              <span className="text-gray-600 text-xs w-7 text-right tabular-nums">{Math.round(s.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
