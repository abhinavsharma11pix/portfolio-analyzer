import { useState, useEffect } from 'react'
import axios from 'axios'
import { Brain, AlertTriangle, CheckCircle, TrendingDown, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react'
import React from 'react'

/* -------------------- TYPES -------------------- */

interface Decision {
  action: string
  symbol: string | null
  priority: number
  priority_label: string
  color: string
  title: string
  what: string
  why: string
  metric_triggered: string
  metric_value: any
  threshold: any
  impact_score: number
  confidence: number
  tags: string[]
  suggested_amount: string | null
}

interface DecisionResponse {
  explanation: string
  portfolio_score: {
    total_score: number
    grade: string
    grade_label: string
  }
  total_decisions: number
  decisions: {
    critical: Decision[]
    high: Decision[]
    medium: Decision[]
    low: Decision[]
  }
  summary: {
    critical_count: number
    high_count: number
    action_required: boolean
  }
}

interface Props {
  holdings: any[]
  riskMetrics: any
  advancedMetrics: any
  summary: any
}

/* -------------------- HELPERS -------------------- */

const ACTION_ICONS: Record<string, React.ReactNode> = {
  EXIT:      <TrendingDown size={14} className="text-red-400" />,
  REDUCE:    <TrendingDown size={14} className="text-orange-400" />,
  TRIM:      <TrendingDown size={14} className="text-yellow-400" />,
  ADD:       <TrendingUp   size={14} className="text-green-400" />,
  REBALANCE: <Brain        size={14} className="text-blue-400"  />,
  MONITOR:   <AlertTriangle size={14} className="text-gray-400" />,
}

const PRIORITY_STYLES: Record<number, string> = {
  1: "border-red-700 bg-red-950/30",
  2: "border-orange-700 bg-orange-950/20",
  3: "border-yellow-700 bg-yellow-950/10",
  4: "border-gray-700 bg-gray-900/30",
}

const PRIORITY_BADGE: Record<number, string> = {
  1: "bg-red-900/60 text-red-300",
  2: "bg-orange-900/60 text-orange-300",
  3: "bg-yellow-900/60 text-yellow-300",
  4: "bg-gray-800 text-gray-400",
}

/* -------------------- DECISION CARD -------------------- */

function DecisionCard({ d }: { d: Decision }) {
  const [expanded, setExpanded] = useState(d.priority === 1)

  return (
    <div className={`border rounded-xl overflow-hidden ${PRIORITY_STYLES[d.priority]}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 px-4 py-4 text-left hover:bg-white/5 transition-colors"
      >
        {/* Action icon */}
        <div className="mt-0.5 shrink-0">
          {ACTION_ICONS[d.action] || <AlertTriangle size={14} />}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_BADGE[d.priority]}`}>
              {d.priority_label}
            </span>
            <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
              {d.action}
            </span>
            {d.symbol && (
              <span className="text-xs text-blue-400 font-semibold">
                {d.symbol}
              </span>
            )}
            <span className="text-xs text-gray-600 ml-auto">
              Impact: {d.impact_score.toFixed(0)}/100
            </span>
          </div>
          <p className="text-white font-medium text-sm">{d.title}</p>
        </div>

        {/* Expand icon */}
        <div className="shrink-0 mt-1">
          {expanded
            ? <ChevronUp  size={14} className="text-gray-500" />
            : <ChevronDown size={14} className="text-gray-500" />
          }
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-3">

          {/* What to do */}
          <div className="flex items-start gap-2">
            <CheckCircle size={13} className="text-blue-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">Action</p>
              <p className="text-white text-sm">{d.what}</p>
              {d.suggested_amount && (
                <p className="text-blue-400 text-xs mt-1 font-medium">
                  💡 {d.suggested_amount}
                </p>
              )}
            </div>
          </div>

          {/* Why */}
          <div className="flex items-start gap-2">
            <Brain size={13} className="text-purple-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">Why</p>
              <p className="text-gray-300 text-sm leading-relaxed">{d.why}</p>
            </div>
          </div>

          {/* Metric that triggered */}
          <div className="flex items-center gap-4 pt-1 border-t border-white/5">
            <div>
              <p className="text-gray-600 text-xs">Triggered by</p>
              <p className="text-gray-400 text-xs font-mono">
                {d.metric_triggered}: {String(d.metric_value)}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-xs">Threshold</p>
              <p className="text-gray-400 text-xs font-mono">
                {String(d.threshold)}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-xs">Confidence</p>
              <p className="text-gray-400 text-xs">
                {(d.confidence * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Tags */}
          {d.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {d.tags.map(tag => (
                <span
                  key={tag}
                  className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* -------------------- MAIN COMPONENT -------------------- */

export default function TodayDashboard({
  holdings, riskMetrics, advancedMetrics, summary
}: Props) {
  const [data, setData]       = useState<DecisionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!holdings?.length || !riskMetrics) return

    const fetchDecisions = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.post(
          'http://localhost:8000/api/portfolio/decisions',
          {
            holdings,
            risk_metrics:     riskMetrics,
            advanced_metrics: advancedMetrics || {},
            predictions:      {},
            summary:          summary || {},
          }
        )
        setData(res.data)
      } catch {
        setError('Could not generate decisions')
      } finally {
        setLoading(false)
      }
    }

    fetchDecisions()
  }, [holdings, riskMetrics, advancedMetrics, summary])

  if (loading) return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
      <Brain size={28} className="text-blue-400 mx-auto mb-3 animate-pulse" />
      <p className="text-gray-300 font-medium">Generating decisions...</p>
      <p className="text-gray-500 text-sm mt-1">
        Analyzing across 9 risk dimensions
      </p>
    </div>
  )

  if (error) return (
    <div className="bg-gray-900 border border-red-800 rounded-2xl p-4 text-red-400 text-sm">
      ⚠️ {error}
    </div>
  )

  if (!data) return null

  const { decisions, summary: sum, explanation, portfolio_score } = data

  const scoreColor =
    portfolio_score.total_score >= 70 ? 'text-green-400' :
    portfolio_score.total_score >= 50 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="space-y-6">

      {/* ── Hero: What To Do Today ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Score */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col items-center justify-center text-center">
          <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">
            Portfolio Health
          </p>
          <p className={`text-6xl font-black mb-1 ${scoreColor}`}>
            {portfolio_score.grade}
          </p>
          <p className={`text-xl font-bold mb-2 ${scoreColor}`}>
            {portfolio_score.total_score.toFixed(0)}/100
          </p>
          <p className="text-gray-500 text-sm">{portfolio_score.grade_label}</p>

          {/* Action summary pills */}
          <div className="flex gap-2 mt-4 flex-wrap justify-center">
            {sum.critical_count > 0 && (
              <span className="text-xs bg-red-900/50 text-red-400 px-3 py-1 rounded-full">
                {sum.critical_count} Critical
              </span>
            )}
            {data.decisions.high.length > 0 && (
              <span className="text-xs bg-orange-900/50 text-orange-400 px-3 py-1 rounded-full">
                {data.decisions.high.length} High
              </span>
            )}
            {data.decisions.medium.length > 0 && (
              <span className="text-xs bg-yellow-900/50 text-yellow-400 px-3 py-1 rounded-full">
                {data.decisions.medium.length} Medium
              </span>
            )}
          </div>
        </div>

        {/* AI Explanation */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={18} className="text-blue-400" />
            <h3 className="text-white font-semibold">
              What Should I Do Today?
            </h3>
            <span className="ml-auto text-xs bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded-full">
              AI Decision Engine
            </span>
          </div>
          <p className="text-gray-300 leading-relaxed text-sm">
            {explanation}
          </p>

          {!sum.action_required && (
            <div className="mt-4 flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle size={16} />
              <span>No urgent actions required — portfolio is stable</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Decision Lists ── */}
      {data.total_decisions > 0 && (
        <div className="space-y-4">

          {/* Critical */}
          {decisions.critical.length > 0 && (
            <div>
              <h3 className="text-red-400 font-semibold text-sm uppercase tracking-wide mb-3 flex items-center gap-2">
                <AlertTriangle size={14} />
                Critical — Act Today ({decisions.critical.length})
              </h3>
              <div className="space-y-2">
                {decisions.critical.map((d, i) => (
                  <DecisionCard key={i} d={d} />
                ))}
              </div>
            </div>
          )}

          {/* High */}
          {decisions.high.length > 0 && (
            <div>
              <h3 className="text-orange-400 font-semibold text-sm uppercase tracking-wide mb-3 flex items-center gap-2">
                <AlertTriangle size={14} />
                High Priority — Act This Week ({decisions.high.length})
              </h3>
              <div className="space-y-2">
                {decisions.high.map((d, i) => (
                  <DecisionCard key={i} d={d} />
                ))}
              </div>
            </div>
          )}

          {/* Medium */}
          {decisions.medium.length > 0 && (
            <div>
              <h3 className="text-yellow-400 font-semibold text-sm uppercase tracking-wide mb-3">
                Medium Priority — This Month ({decisions.medium.length})
              </h3>
              <div className="space-y-2">
                {decisions.medium.map((d, i) => (
                  <DecisionCard key={i} d={d} />
                ))}
              </div>
            </div>
          )}

          {/* Low */}
          {decisions.low.length > 0 && (
            <div>
              <h3 className="text-gray-500 font-semibold text-sm uppercase tracking-wide mb-3">
                Monitor ({decisions.low.length})
              </h3>
              <div className="space-y-2">
                {decisions.low.map((d, i) => (
                  <DecisionCard key={i} d={d} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  )
}