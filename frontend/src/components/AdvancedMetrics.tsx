import { useState, useEffect, memo } from 'react'
import axios from 'axios'
import { Activity } from 'lucide-react'
import { MetricCardSkeleton } from './ui/Skeleton'

interface AdvancedData {
  var_95: number; var_99: number; cvar_95: number; alpha: number
  regime: {
    regime: string; label: string; color: string
    trend_pct: number; volatility_pct: number
  }
  factor_exposure: { momentum: number; value: number; growth: number; defensive: number }
  interpretation: { var: string; cvar: string; alpha: string }
}

interface Props {
  holdings: any[]
  riskMetrics: any
  onLoad?: (data: any) => void
  preloadedData?: any
}

const MetricBox = memo(function MetricBox({
  label, value, sub, color,
}: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="card p-4 space-y-1.5">
      <p className="text-gray-500 text-xs uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
      <p className="text-gray-600 text-xs leading-relaxed">{sub}</p>
    </div>
  )
})

const FactorBar = memo(function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400 text-xs w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div
          className="h-2 rounded-full bg-blue-500"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="text-gray-400 text-xs w-10 text-right tabular-nums">{value}%</span>
    </div>
  )
})

const AdvancedMetrics = memo(function AdvancedMetrics({
  holdings, riskMetrics, onLoad, preloadedData
}: Props) {
  const [data,    setData]    = useState<AdvancedData | null>(preloadedData ?? null)
  const [loading, setLoading] = useState(!preloadedData)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    if (preloadedData) {
      setData(preloadedData)
      setLoading(false)
      onLoad?.(preloadedData)
      return
    }

    if (!holdings?.length || !riskMetrics) return
    let cancelled = false
    setLoading(true)
    setError(null)

    axios.post('http://localhost:8000/api/analytics/advanced', {
      holdings,
      risk_metrics: riskMetrics,
    })
      .then(res => {
        if (!cancelled) {
          setData(res.data)
          onLoad?.(res.data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not compute advanced metrics')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [holdings, riskMetrics, preloadedData, onLoad])

  if (loading) return (
    <div className="space-y-5">
      <div className="card p-5 h-24 skeleton" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <MetricCardSkeleton key={i} />)}
      </div>
    </div>
  )

  if (error) return (
    <div className="card p-4 text-red-400 text-sm">⚠️ {error}</div>
  )

  if (!data) return null

  const regimeColors: Record<string, string> = {
    bull: 'text-green-400', bear: 'text-red-400',
    sideways: 'text-yellow-400', unknown: 'text-gray-400',
  }
  const regimeBg: Record<string, string> = {
    bull: 'bg-green-950/30 border-green-800/40',
    bear: 'bg-red-950/30 border-red-800/40',
    sideways: 'bg-yellow-950/30 border-yellow-800/40',
    unknown: 'bg-gray-900 border-gray-800',
  }

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Regime banner */}
      <div className={`border rounded-2xl p-5 flex items-center justify-between
        ${regimeBg[data.regime.regime] ?? 'bg-gray-900 border-gray-800'}`}>
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Market Regime</p>
          <p className={`text-2xl font-bold ${regimeColors[data.regime.regime] ?? 'text-gray-400'}`}>
            {data.regime.label}
          </p>
          <p className="text-gray-500 text-xs mt-1">
            30-day trend: {data.regime.trend_pct > 0 ? '+' : ''}{data.regime.trend_pct}%
            · Volatility: {data.regime.volatility_pct}%
          </p>
        </div>
        <div className={`text-5xl opacity-15 ${regimeColors[data.regime.regime]}`}>
          {data.regime.regime === 'bull' ? '↑' : data.regime.regime === 'bear' ? '↓' : '→'}
        </div>
      </div>

      {/* Metrics */}
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
          sub="Worst-case at 99% confidence"
          color="text-red-500"
        />
        <MetricBox
          label="Alpha vs Nifty"
          value={`${data.alpha > 0 ? '+' : ''}${data.alpha.toFixed(2)}%`}
          sub={data.interpretation.alpha}
          color={data.alpha >= 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      {/* Factor exposure */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={15} className="text-blue-400" />
          <h3 className="text-white font-semibold text-sm">Factor Exposure</h3>
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
})

export default AdvancedMetrics