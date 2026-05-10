import React, { useState, useEffect, memo } from 'react'
import axios from 'axios'
import {
  Brain, AlertTriangle, CheckCircle,
  TrendingDown, TrendingUp, ChevronDown, ChevronUp
} from 'lucide-react'
import { TodayDashboardSkeleton } from './ui/Skeleton'

/* ── Types ── */
interface Decision {
  action: string; symbol: string | null; priority: number
  priority_label: string; color: string; title: string
  what: string; why: string; metric_triggered: string
  metric_value: any; threshold: any; impact_score: number
  confidence: number; tags: string[]; suggested_amount: string | null
}
interface DecisionResponse {
  explanation: string
  portfolio_score: { total_score: number; grade: string; grade_label: string }
  total_decisions: number
  decisions: { critical: Decision[]; high: Decision[]; medium: Decision[]; low: Decision[] }
  summary: { critical_count: number; high_count: number; action_required: boolean }
}
interface Props {
  holdings: any[]; riskMetrics: any; advancedMetrics: any; summary: any
}

/* ── Helpers ── */
const ACTION_ICONS: Record<string, React.ReactNode> = {
  EXIT:      <TrendingDown size={14} className="text-red-400" />,
  REDUCE:    <TrendingDown size={14} className="text-orange-400" />,
  TRIM:      <TrendingDown size={14} className="text-yellow-400" />,
  ADD:       <TrendingUp   size={14} className="text-green-400" />,
  REBALANCE: <Brain        size={14} className="text-blue-400" />,
  MONITOR:   <AlertTriangle size={14} className="text-gray-400" />,
}

const PRIORITY_BORDER: Record<number, string> = {
  1: 'border-red-800/60    bg-red-950/20',
  2: 'border-orange-800/60 bg-orange-950/10',
  3: 'border-yellow-800/60 bg-yellow-950/10',
  4: 'border-gray-700/60   bg-gray-900/20',
}
const PRIORITY_BADGE: Record<number, string> = {
  1: 'bg-red-900/60 text-red-300',
  2: 'bg-orange-900/60 text-orange-300',
  3: 'bg-yellow-900/60 text-yellow-300',
  4: 'bg-gray-800 text-gray-400',
}

/* ── Decision Card ── */
const DecisionCard = memo(function DecisionCard({
  d, defaultExpanded = false
}: { d: Decision; defaultExpanded?: boolean }) {
  const [open, setOpen] = useState(defaultExpanded)

  return (
    <div className={`border rounded-xl overflow-hidden transition-colors ${PRIORITY_BORDER[d.priority]}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className="mt-0.5 shrink-0">
          {ACTION_ICONS[d.action] ?? <AlertTriangle size={14} />}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_BADGE[d.priority]}`}>
              {d.priority_label}
            </span>
            <span className="text-xs bg-gray-800/80 text-gray-400 px-2 py-0.5 rounded-full">
              {d.action}
            </span>
            {d.symbol && (
              <span className="text-xs text-blue-400 font-semibold">{d.symbol}</span>
            )}
          </div>
          <p className="text-white text-sm font-medium leading-snug">{d.title}</p>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <span className="text-xs text-gray-600 hidden sm:block">
            {d.impact_score.toFixed(0)}/100
          </span>
          {open
            ? <ChevronUp size={14} className="text-gray-500" />
            : <ChevronDown size={14} className="text-gray-500" />
          }
        </div>
      </button>

      {open && (
        <div className="border-t border-white/5 px-4 pb-4 pt-3 space-y-3 animate-fade-in">
          <div className="flex gap-2">
            <CheckCircle size={13} className="text-blue-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Action</p>
              <p className="text-white text-sm">{d.what}</p>
              {d.suggested_amount && (
                <p className="text-blue-400 text-xs mt-1 font-medium">
                  💡 {d.suggested_amount}
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <Brain size={13} className="text-purple-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Why</p>
              <p className="text-gray-300 text-sm leading-relaxed">{d.why}</p>
            </div>
          </div>

          <div className="flex gap-6 pt-1 border-t border-white/5 text-xs">
            <div>
              <p className="text-gray-600">Triggered by</p>
              <p className="text-gray-400 font-mono mt-0.5">
                {d.metric_triggered}: {String(d.metric_value)}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Threshold</p>
              <p className="text-gray-400 font-mono mt-0.5">{String(d.threshold)}</p>
            </div>
            <div>
              <p className="text-gray-600">Confidence</p>
              <p className="text-gray-400 mt-0.5">{(d.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>

          {d.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {d.tags.map(t => (
                <span key={t} className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">
                  #{t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
})

function DecisionGroup({ label, decisions, defaultExpanded = false }: {
  label: string; decisions: Decision[]; defaultExpanded?: boolean
}) {
  if (!decisions.length) return null
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2 px-1">
        {label} ({decisions.length})
      </p>
      <div className="space-y-2">
        {decisions.map((d, i) => (
          <DecisionCard key={i} d={d} defaultExpanded={defaultExpanded && i === 0} />
        ))}
      </div>
    </div>
  )
}

/* ── Main ── */
const TodayDashboard = memo(function TodayDashboard({
  holdings, riskMetrics, advancedMetrics, summary
}: Props) {
  const [data,    setData]    = useState<DecisionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    if (!holdings?.length || !riskMetrics) return
    let cancelled = false

    setLoading(true)
    setError(null)

    axios.post('http://localhost:8000/api/portfolio/decisions', {
      holdings,
      risk_metrics:     riskMetrics,
      advanced_metrics: advancedMetrics ?? {},
      predictions:      {},
      summary:          summary ?? {},
    })
      .then(res => { if (!cancelled) { setData(res.data); setLoading(false) } })
      .catch(() => { if (!cancelled) { setError('Could not generate decisions'); setLoading(false) } })

    return () => { cancelled = true }
  }, [holdings, riskMetrics, advancedMetrics, summary])

  if (loading) return <TodayDashboardSkeleton />

  if (error) return (
    <div className="card p-6 text-red-400 text-sm">⚠️ {error}</div>
  )

  if (!data) return <TodayDashboardSkeleton />

  const { decisions, summary: sum, explanation, portfolio_score } = data

  const scoreColor =
    portfolio_score.total_score >= 70 ? 'text-green-400' :
    portfolio_score.total_score >= 50 ? 'text-yellow-400' : 'text-red-400'

  const scoreBg =
    portfolio_score.total_score >= 70 ? 'bg-green-950/30 border-green-800/40' :
    portfolio_score.total_score >= 50 ? 'bg-yellow-950/30 border-yellow-800/40' :
    'bg-red-950/30 border-red-800/40'

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Hero row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Score */}
        <div className={`border rounded-2xl p-6 flex flex-col items-center justify-center text-center ${scoreBg}`}>
          <p className="text-gray-400 text-xs uppercase tracking-widest mb-3">
            Portfolio Health
          </p>
          <p className={`text-6xl font-black leading-none mb-1 ${scoreColor}`}>
            {portfolio_score.grade}
          </p>
          <p className={`text-xl font-bold mb-1 ${scoreColor}`}>
            {portfolio_score.total_score.toFixed(0)}/100
          </p>
          <p className="text-gray-500 text-xs mb-4">{portfolio_score.grade_label}</p>
          <div className="flex gap-2 flex-wrap justify-center">
            {sum.critical_count > 0 && (
              <span className="text-xs bg-red-900/50 text-red-400 px-2.5 py-1 rounded-full">
                {sum.critical_count} Critical
              </span>
            )}
            {decisions.high.length > 0 && (
              <span className="text-xs bg-orange-900/50 text-orange-400 px-2.5 py-1 rounded-full">
                {decisions.high.length} High
              </span>
            )}
            {decisions.medium.length > 0 && (
              <span className="text-xs bg-yellow-900/50 text-yellow-400 px-2.5 py-1 rounded-full">
                {decisions.medium.length} Medium
              </span>
            )}
          </div>
        </div>

        {/* AI explanation */}
        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <Brain size={16} className="text-blue-400" />
            </div>
            <h3 className="text-white font-semibold">What Should I Do Today?</h3>
            <span className="ml-auto text-xs bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded-full shrink-0">
              AI Engine
            </span>
          </div>
          <p className="text-gray-300 text-sm leading-relaxed">{explanation}</p>
          {!sum.action_required && (
            <div className="mt-4 flex items-center gap-2 text-green-400 text-sm bg-green-950/20 border border-green-800/30 rounded-xl px-4 py-2.5">
              <CheckCircle size={15} />
              No urgent actions — portfolio is stable
            </div>
          )}
        </div>
      </div>

      {/* Decision lists */}
      {data.total_decisions > 0 && (
        <div className="space-y-5">
          <DecisionGroup label="🔴 Critical — Act Today"  decisions={decisions.critical} defaultExpanded />
          <DecisionGroup label="🟠 High — Act This Week"  decisions={decisions.high} />
          <DecisionGroup label="🟡 Medium — This Month"   decisions={decisions.medium} />
          <DecisionGroup label="🔵 Monitor"               decisions={decisions.low} />
        </div>
      )}
    </div>
  )
})

export default TodayDashboard