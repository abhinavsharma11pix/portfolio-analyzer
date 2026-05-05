import { useState, useEffect } from 'react'
import axios from 'axios'
import { Activity } from 'lucide-react'

interface AdvancedData {
  var_95: number
  var_99: number
  cvar_95: number
  alpha: number
  regime: {
    regime: string
    label: string
    color: string
    trend_pct: number
    volatility_pct: number
  }
  factor_exposure: {
    momentum: number
    value: number
    growth: number
    defensive: number
  }
  interpretation: {
    var: string
    cvar: string
    alpha: string
  }
}

interface Props {
  holdings: any[]
  riskMetrics: any
}

function MetricBox({ label, value, sub, color }: {
  label: string
  value: string
  sub: string
  color: string
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-xs mb-2 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mb-1 ${color}`}>{value}</p>
      <p className="text-gray-500 text-xs leading-relaxed">{sub}</p>
    </div>
  )
}

function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400 text-xs w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="text-gray-400 text-xs w-10 text-right">{value}%</span>
    </div>
  )
}

export default function AdvancedMetrics({ holdings, riskMetrics }: Props) {
  const [data, setData]       = useState<AdvancedData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!holdings?.length || !riskMetrics) return

    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.post(
          'http://localhost:8000/api/analytics/advanced',
          { holdings, risk_metrics: riskMetrics }
        )
        setData(res.data)
      } catch {
        setError('Could not compute advanced metrics')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [holdings, riskMetrics])

  if (loading) return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
      <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
      <p className="text-gray-400 text-sm">Computing advanced risk metrics...</p>
    </div>
  )

  if (error) return (
    <div className="bg-gray-900 border border-red-800 rounded-2xl p-4 text-red-400 text-sm">
      ⚠️ {error}
    </div>
  )

  if (!data) return null

  const regimeColors: Record<string, string> = {
    bull:     'text-green-400',
    bear:     'text-red-400',
    sideways: 'text-yellow-400',
    unknown:  'text-gray-400',
  }

  const regimeBorder: Record<string, string> = {
    bull:     'bg-green-950/30 border-green-800',
    bear:     'bg-red-950/30 border-red-800',
    sideways: 'bg-yellow-950/30 border-yellow-800',
    unknown:  'bg-gray-900 border-gray-800',
  }

  return (
    <div className="space-y-6">

      {/* Regime Banner */}
      <div className={`border rounded-2xl p-5 flex items-center justify-between
        ${regimeBorder[data.regime.regime] || 'bg-gray-900 border-gray-800'}`}
      >
        <div>
          <p className="text-gray-400 text-xs mb-1 uppercase tracking-wide">
            Market Regime
          </p>
          <p className={`text-2xl font-bold ${regimeColors[data.regime.regime] || 'text-gray-400'}`}>
            {data.regime.label}
          </p>
          <p className="text-gray-500 text-xs mt-1">
            30-day trend: {data.regime.trend_pct > 0 ? '+' : ''}
            {data.regime.trend_pct}% · Volatility: {data.regime.volatility_pct}%
          </p>
        </div>
        <div className={`text-6xl opacity-20 ${regimeColors[data.regime.regime]}`}>
          {data.regime.regime === 'bull' ? '↑' :
           data.regime.regime === 'bear' ? '↓' : '→'}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricBox
          label="VaR 95%"
          value={`${data.var_95.toFixed(2)}%`}
          sub={data.interpretation.var}
          color="text-orange-400"
        />
        <MetricBox
          label="CVaR 95%"
          value={`${data.cvar_95.toFixed(2)}%`}
          sub={data.interpretation.cvar}
          color="text-red-400"
        />
        <MetricBox
          label="VaR 99%"
          value={`${data.var_99.toFixed(2)}%`}
          sub="Worst-case daily loss at 99% confidence"
          color="text-red-500"
        />
        <MetricBox
          label="Alpha vs Nifty"
          value={`${data.alpha > 0 ? '+' : ''}${data.alpha.toFixed(2)}%`}
          sub={data.interpretation.alpha}
          color={data.alpha >= 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      {/* Factor Exposure */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={16} className="text-blue-400" />
          <h3 className="text-white font-semibold">Factor Exposure</h3>
        </div>
        <div className="space-y-3">
          <FactorBar label="Momentum"  value={data.factor_exposure.momentum} />
          <FactorBar label="Growth"    value={data.factor_exposure.growth} />
          <FactorBar label="Value"     value={data.factor_exposure.value} />
          <FactorBar label="Defensive" value={data.factor_exposure.defensive} />
        </div>
      </div>

    </div>
  )
}