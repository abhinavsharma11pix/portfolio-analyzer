import { useState, useEffect } from 'react'
import axios from 'axios'
import { ShieldAlert, TrendingDown, Activity, Scale } from 'lucide-react'

interface Holding {
  symbol: string
  quantity: number
  avg_buy_price: number
}

interface RiskData {
  sharpe_ratio: number
  sortino_ratio: number
  annualized_volatility_pct: number
  max_drawdown_pct: number
  beta: number
  stock_volatilities: Record<string, number>
  interpretation: {
    sharpe: string
    volatility: string
    drawdown: string
    beta: string
  }
}

interface Props {
  holdings: Holding[]
  onRiskLoad?: (data: any) => void
}

// Safe formatter — never crashes on undefined/NaN
const fmt = (val?: number, digits = 2): string => {
  return typeof val === 'number' && !isNaN(val) ? val.toFixed(digits) : '0.00'
}

function MetricCard({ icon, label, value, subtitle, color }: {
  icon: React.ReactNode
  label: string
  value: string
  subtitle: string
  color: string
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className={color}>{icon}</span>
        <span className="text-gray-400 text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold mb-1 ${color}`}>{value}</p>
      <p className="text-gray-500 text-xs">{subtitle}</p>
    </div>
  )
}

function getRiskColor(sharpe: number) {
  if (sharpe > 1) return 'text-green-400'
  if (sharpe > 0) return 'text-yellow-400'
  return 'text-red-400'
}

export default function RiskMetrics({ holdings , onRiskLoad}: Props) {
  const [riskData, setRiskData] = useState<RiskData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!holdings || holdings.length === 0) return

    const fetchRisk = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.post('http://localhost:8000/api/portfolio/risk', { holdings })
        if (res.data?.error) {
          setError(res.data.error)
          setRiskData(null)
        } else {
          setRiskData(res.data)
          onRiskLoad?.(res.data)
        }
      } catch {
        setError('Could not calculate risk metrics. Make sure backend is running.')
      } finally {
        setLoading(false)
      }
    }

    fetchRisk()
  }, [holdings, onRiskLoad])

  if (loading) return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
      <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
      <p className="text-gray-400 text-sm">Fetching 1 year of market data...</p>
      <p className="text-gray-600 text-xs mt-1">This takes ~15 seconds</p>
    </div>
  )

  if (error) return (
    <div className="bg-gray-900 border border-red-800 rounded-2xl p-6 text-red-400 text-sm">
      ⚠️ {error}
    </div>
  )

  if (!riskData) return null

  const sharpeColor = getRiskColor(riskData.sharpe_ratio ?? 0)

  return (
    <div className="space-y-6">
      {/* 4 main metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<Scale size={18} />}
          label="Sharpe Ratio"
          value={fmt(riskData.sharpe_ratio)}
          subtitle={riskData.interpretation?.sharpe || ''}
          color={sharpeColor}
        />
        <MetricCard
          icon={<Activity size={18} />}
          label="Volatility (Annual)"
          value={`${fmt(riskData.annualized_volatility_pct, 1)}%`}
          subtitle={riskData.interpretation?.volatility || ''}
          color={(riskData.annualized_volatility_pct ?? 0) > 25 ? 'text-red-400' : 'text-yellow-400'}
        />
        <MetricCard
          icon={<TrendingDown size={18} />}
          label="Max Drawdown"
          value={`${fmt(riskData.max_drawdown_pct, 1)}%`}
          subtitle={riskData.interpretation?.drawdown || ''}
          color="text-red-400"
        />
        <MetricCard
          icon={<ShieldAlert size={18} />}
          label="Beta (vs Nifty)"
          value={fmt(riskData.beta)}
          subtitle={riskData.interpretation?.beta || ''}
          color={(riskData.beta ?? 1) > 1.2 ? 'text-red-400' : 'text-blue-400'}
        />
      </div>

      {/* Sortino + Stock Volatilities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h4 className="text-white font-medium mb-1">Sortino Ratio</h4>
          <p className="text-3xl font-bold text-purple-400 mb-2">
            {fmt(riskData.sortino_ratio)}
          </p>
          <p className="text-gray-500 text-xs">
            Like Sharpe but only penalizes downside risk. Higher is better.
          </p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h4 className="text-white font-medium mb-4">Stock Volatilities</h4>
          <div className="space-y-3">
            {Object.entries(riskData.stock_volatilities || {})
              .sort((a, b) => b[1] - a[1])
              .map(([symbol, vol]) => (
                <div key={symbol} className="flex items-center gap-3">
                  <span className="text-blue-400 text-sm w-28 shrink-0">{symbol}</span>
                  <div className="flex-1 bg-gray-800 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        vol > 40 ? 'bg-red-500' : vol > 25 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(vol, 100)}%` }}
                    />
                  </div>
                  <span className="text-gray-400 text-sm w-12 text-right">{vol}%</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}