import { useState, useEffect } from 'react'
import axios from 'axios'
import { Brain,  CheckCircle } from 'lucide-react'

interface Insight {
  type: string
  severity: 'high' | 'medium' | 'low'
  icon: string
  title: string
  message: string
  action: string
}

interface PortfolioScore {
  total_score: number
  grade: string
  grade_color: string
  grade_label: string
  breakdown: {
    diversification: number
    risk_adjusted_return: number
    volatility: number
    profitability: number
  }
}

interface InsightsData {
  portfolio_score: PortfolioScore
  llm_summary: string
  insights: Insight[]
  correlated_groups: any[]
}

interface Props {
  holdings: any[]
  riskMetrics: any
  summary: any
}

const severityStyles = {
  high: 'border-red-800/50 bg-red-950/20',
  medium: 'border-yellow-800/50 bg-yellow-950/20',
  low: 'border-green-800/50 bg-green-950/20'
}

const severityBadge = {
  high: 'bg-red-900/50 text-red-400',
  medium: 'bg-yellow-900/50 text-yellow-400',
  low: 'bg-green-900/50 text-green-400'
}

export default function AIInsights({ holdings, riskMetrics, summary }: Props) {
  const [data, setData] = useState<InsightsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!holdings?.length || !riskMetrics) return

    const fetch = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.post('http://localhost:8000/api/portfolio/insights', {
          holdings,
          risk_metrics: riskMetrics,
          summary
        })
        setData(res.data)
      } catch {
        setError('Could not generate insights. Make sure backend is running.')
      } finally {
        setLoading(false)
      }
    }

    fetch()
  }, [holdings, riskMetrics, summary])

  if (loading) return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
      <Brain size={32} className="text-blue-400 mx-auto mb-3 animate-pulse" />
      <p className="text-gray-300 font-medium">Generating AI insights...</p>
      <p className="text-gray-500 text-sm mt-1">Analyzing your portfolio across 8 dimensions</p>
    </div>
  )

  if (error) return (
    <div className="bg-gray-900 border border-red-800 rounded-2xl p-6 text-red-400 text-sm">⚠️ {error}</div>
  )

  if (!data) return null

  const { portfolio_score, llm_summary, insights, correlated_groups } = data
  const scoreColor =
    portfolio_score.total_score >= 70 ? 'text-green-400' :
    portfolio_score.total_score >= 50 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="space-y-6">
      {/* Score Card + LLM Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Portfolio Score */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col items-center justify-center">
          <p className="text-gray-400 text-sm mb-2">Portfolio Health Score</p>
          <p className={`text-7xl font-black mb-1 ${scoreColor}`}>
            {portfolio_score.grade}
          </p>
          <p className={`text-2xl font-bold mb-3 ${scoreColor}`}>
            {portfolio_score.total_score}/100
          </p>
          <p className="text-gray-400 text-sm">{portfolio_score.grade_label}</p>

          {/* Score breakdown */}
          <div className="w-full mt-4 space-y-2">
            {Object.entries(portfolio_score.breakdown).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-gray-500 text-xs w-32 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-blue-500"
                    style={{ width: `${(val / 25) * 100}%` }}
                  />
                </div>
                <span className="text-gray-400 text-xs w-8 text-right">
                  {val}/25
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* LLM Summary */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={20} className="text-blue-400" />
            <h3 className="text-white font-semibold">AI Portfolio Summary</h3>
            <span className="text-xs bg-blue-900/50 text-blue-400 px-2 py-0.5 rounded-full ml-auto">
              Powered by Groq LLaMA
            </span>
          </div>
          <p className="text-gray-300 leading-relaxed text-sm">{llm_summary}</p>

          {/* Correlated groups warning */}
          {correlated_groups.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <p className="text-yellow-400 text-sm font-medium mb-2">
                🔗 Correlated Holdings Detected
              </p>
              {correlated_groups.map((g, i) => (
                <p key={i} className="text-gray-400 text-xs">{g.message}</p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Insights List */}
      <div>
        <h3 className="text-white font-semibold text-lg mb-4">
          💡 Actionable Insights ({insights.length})
        </h3>
        <div className="space-y-3">
          {insights.map((insight, i) => (
            <div
              key={i}
              className={`border rounded-xl p-5 transition-all ${severityStyles[insight.severity]}`}
            >
              <div className="flex items-start gap-4">
                <span className="text-2xl">{insight.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-white font-medium">{insight.title}</h4>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${severityBadge[insight.severity]}`}>
                      {insight.severity}
                    </span>
                  </div>
                  <p className="text-gray-300 text-sm mb-2">{insight.message}</p>
                  <div className="flex items-start gap-2">
                    <CheckCircle size={14} className="text-blue-400 mt-0.5 shrink-0" />
                    <p className="text-blue-400 text-xs">{insight.action}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}