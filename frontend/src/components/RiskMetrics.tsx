import { useState, useEffect, memo } from 'react'
import axios from 'axios'
import {
  TrendingDown, Activity, Scale, ShieldAlert
} from 'lucide-react'
import { RiskMetricsSkeleton } from './ui/Skeleton'
import Tooltip from './ui/Tooltip'

/* ── Types ── */
interface RiskData {
  sharpe_ratio: number
  sortino_ratio?: number
  annualized_return_pct: number
  annualized_volatility_pct: number
  max_drawdown_pct: number
  beta: number
  top_sector?: string
  top_sector_weight_pct?: number
  sector_breakdown: { sector: string; weight_pct: number }[]
  total_holdings: number
  total_invested: number
  interpretation: {
    sharpe: string
    volatility: string
    drawdown: string
    beta: string
  }
}

interface Props {
  holdings: any[]
  onRiskLoad: (data: any) => void
  preloadedData?: any
}

/* ── Metric card ── */
const MetricCard = memo(function MetricCard({
  icon, label, value, subtitle, color, tooltip,
}: {
  icon: React.ReactNode; label: string; value: string
  subtitle: string; color: string; tooltip?: string
}) {
  return (
    <div className="card p-5 space-y-1.5">
      <div className="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wide">
        <span className={color}>{icon}</span>
        <Tooltip content={tooltip || label} showIcon={!!tooltip}>
          <span>{label}</span>
        </Tooltip>
      </div>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
      <p className="text-gray-500 text-xs leading-relaxed">{subtitle}</p>
    </div>
  )
})

/* ── Sector bar ── */
const SectorBar = memo(function SectorBar({
  sector, weight_pct
}: { sector: string; weight_pct: number }) {
  const danger = weight_pct >= 55
  const warn   = weight_pct >= 40
  const color  = danger ? 'bg-red-500' : warn ? 'bg-yellow-500' : 'bg-blue-500'
  const text   = danger ? 'text-red-400' : warn ? 'text-yellow-400' : 'text-gray-300'

  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400 text-xs w-28 shrink-0 truncate">{sector}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(weight_pct, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-medium tabular-nums w-10 text-right ${text}`}>
        {weight_pct.toFixed(1)}%
      </span>
    </div>
  )
})

/* ── Main ── */
const RiskMetrics = memo(function RiskMetrics({ holdings, onRiskLoad, preloadedData }: Props) {
  const [riskData, setRiskData] = useState<RiskData | null>(preloadedData ?? null)
  const [loading,  setLoading]  = useState(!preloadedData)
  const [error,    setError]    = useState<string | null>(null)

  useEffect(() => {
    // If preloaded data arrives (from React Query), use it
    if (preloadedData) {
      setRiskData(preloadedData)
      setLoading(false)
      onRiskLoad(preloadedData)
      return
    }

    if (!holdings?.length) return
    let cancelled = false
    setLoading(true)
    setError(null)

    axios.post('http://localhost:8000/api/portfolio/risk', { holdings })
      .then(res => {
        if (!cancelled) {
          setRiskData(res.data)
          onRiskLoad(res.data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Risk calculation failed. Backend may still be loading.')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [holdings, preloadedData, onRiskLoad])

  if (loading) return <RiskMetricsSkeleton />

  if (error) return (
    <div className="card p-6 text-red-400 text-sm">⚠️ {error}</div>
  )

  if (!riskData) return <RiskMetricsSkeleton />

  const sharpeColor =
    riskData.sharpe_ratio >= 1   ? 'text-green-400' :
    riskData.sharpe_ratio >= 0   ? 'text-yellow-400' :
    'text-red-400'

  const fmt = (v: number | null | undefined, dec = 2) =>
    v != null ? v.toFixed(dec) : '—'

  return (
    <div className="space-y-5 animate-fade-in">

      {/* 4 metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<Scale size={16} />}
          label="Sharpe Ratio"
          value={fmt(riskData.sharpe_ratio)}
          subtitle={riskData.interpretation?.sharpe || ''}
          color={sharpeColor}
          tooltip="Return earned per unit of risk. >1 is good, >2 is excellent, <0 means risk is not rewarded."
        />
        <MetricCard
          icon={<Activity size={16} />}
          label="Volatility (Annual)"
          value={`${fmt(riskData.annualized_volatility_pct)}%`}
          subtitle={riskData.interpretation?.volatility || ''}
          color={riskData.annualized_volatility_pct > 25 ? 'text-red-400' : 'text-yellow-400'}
          tooltip="How much your portfolio value swings annually. <15% is stable, >30% is high risk."
        />
        <MetricCard
          icon={<TrendingDown size={16} />}
          label="Max Drawdown"
          value={`${fmt(riskData.max_drawdown_pct)}%`}
          subtitle={riskData.interpretation?.drawdown || ''}
          color="text-red-400"
          tooltip="The largest peak-to-trough decline. -25% means you once lost 25% from the peak."
        />
        <MetricCard
          icon={<ShieldAlert size={16} />}
          label="Beta (vs Nifty)"
          value={fmt(riskData.beta)}
          subtitle={riskData.interpretation?.beta || ''}
          color={riskData.beta > 1.2 ? 'text-red-400' : 'text-blue-400'}
          tooltip="How much your portfolio moves vs Nifty 50. Beta 1.2 = your portfolio moves 1.2x the market."
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Sector concentration */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold text-sm">Sector Concentration</h3>
            {riskData.top_sector && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                (riskData.top_sector_weight_pct ?? 0) >= 55
                  ? 'bg-red-900/50 text-red-400'
                  : (riskData.top_sector_weight_pct ?? 0) >= 40
                  ? 'bg-yellow-900/50 text-yellow-400'
                  : 'bg-gray-800 text-gray-400'
              }`}>
                Top: {riskData.top_sector} {riskData.top_sector_weight_pct?.toFixed(1)}%
              </span>
            )}
          </div>
          <div className="space-y-2.5">
            {riskData.sector_breakdown?.slice(0, 8).map(s => (
              <SectorBar key={s.sector} sector={s.sector} weight_pct={s.weight_pct} />
            ))}
          </div>
        </div>

        {/* Quick stats */}
        <div className="card p-5">
          <h3 className="text-white font-semibold text-sm mb-4">Portfolio Statistics</h3>
          <div className="space-y-3">
            {[
              {
                label: 'Annual Return',
                value: `${riskData.annualized_return_pct >= 0 ? '+' : ''}${fmt(riskData.annualized_return_pct)}%`,
                color: riskData.annualized_return_pct >= 0 ? 'text-green-400' : 'text-red-400',
              },
              {
                label: 'Sortino Ratio',
                value: fmt(riskData.sortino_ratio ?? null),
                color: (riskData.sortino_ratio ?? 0) >= 1 ? 'text-green-400' : 'text-yellow-400',
              },
              {
                label: 'Total Holdings',
                value: String(riskData.total_holdings),
                color: 'text-white',
              },
              {
                label: 'Total Invested',
                value: `₹${(riskData.total_invested || 0).toLocaleString('en-IN')}`,
                color: 'text-white',
              },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between py-1 border-b border-white/[0.04]">
                <span className="text-gray-500 text-sm">{row.label}</span>
                <span className={`text-sm font-semibold tabular-nums ${row.color}`}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Risk gauge */}
          <div className="mt-4 pt-3 border-t border-white/[0.04]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-xs">Overall Risk Level</span>
              <span className={`text-xs font-semibold ${
                riskData.annualized_volatility_pct > 30 ? 'text-red-400' :
                riskData.annualized_volatility_pct > 20 ? 'text-yellow-400' :
                'text-green-400'
              }`}>
                {riskData.annualized_volatility_pct > 30 ? 'High' :
                 riskData.annualized_volatility_pct > 20 ? 'Medium' : 'Low'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  riskData.annualized_volatility_pct > 30 ? 'bg-red-500' :
                  riskData.annualized_volatility_pct > 20 ? 'bg-yellow-500' :
                  'bg-green-500'
                }`}
                style={{ width: `${Math.min(riskData.annualized_volatility_pct * 2, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
})

export default RiskMetrics