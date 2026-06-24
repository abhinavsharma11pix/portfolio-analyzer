/**
 * components/PortfolioScoreCard.tsx — Complete file. (NEW — Day 2)
 * Headline portfolio health score from /api/portfolio/insights.
 * Shows grade (A–F), score, and 3 sub-scores.
 *
 * Usage in Dashboard.tsx:
 *   import PortfolioScoreCard from './components/PortfolioScoreCard'
 *   <PortfolioScoreCard insights={insightsData} />
 *   (insightsData is the response from POST /api/portfolio/insights)
 */
import { Shield, TrendingUp, PieChart, Zap } from 'lucide-react'

interface ScoreBreakdown {
  diversification_score?: number
  momentum_score?:        number
  risk_score?:            number
  quality_score?:         number
}

interface PortfolioScore {
  total_score:       number
  grade:             string
  grade_color:       string
  breakdown?:        ScoreBreakdown
}

interface Props {
  insights:  { portfolio_score?: PortfolioScore; [key: string]: any } | null
  className?: string
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
      <div
        className={`h-full ${color} rounded-full transition-all duration-700`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}

export default function PortfolioScoreCard({ insights, className = '' }: Props) {
  if (!insights?.portfolio_score) return null

  const ps     = insights.portfolio_score
  const grade  = ps.grade?.replace('text-', '').split('-')[0]?.toUpperCase() ?? 'B'
  const config = GRADE_CONFIG[grade] ?? GRADE_CONFIG['B']
  const score  = Math.round(ps.total_score ?? 0)
  const bd     = ps.breakdown ?? {}

  const subScores = [
    { label: 'Diversification', value: (bd.diversification_score ?? 0) * 100, icon: <PieChart size={11} />,   color: 'bg-blue-500' },
    { label: 'Momentum',        value: (bd.momentum_score ?? 0) * 100,         icon: <TrendingUp size={11} />, color: 'bg-green-500' },
    { label: 'Risk Quality',    value: (bd.risk_score ?? 0) * 100,             icon: <Shield size={11} />,     color: 'bg-purple-500' },
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
              <span className="text-gray-600 text-xs w-7 text-right tabular-nums">
                {Math.round(s.value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
