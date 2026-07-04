/**
 * components/BenchmarkChart.tsx — Complete file.
 * Fixed TS2322: Tooltip formatter receives ValueType (number|string|undefined),
 * not just number. All formatter callbacks now accept `unknown`.
 */
import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { apiClient } from '../services/api'

interface BenchmarkPoint { date: string; portfolio: number; benchmark: number }

interface BenchmarkResult {
  portfolio_return?:  number | null
  benchmark_return?:  number | null
  alpha?:             number | null
  beta?:              number | null
  correlation?:       number | null
  tracking_error?:    number | null
  information_ratio?: number | null
  chart_data?:        BenchmarkPoint[]
  benchmark_name?:    string
}

interface Props { holdings: any[]; className?: string }

const BENCHMARKS = [
  { value: '^NSEI',  label: 'NIFTY 50', flag: '🇮🇳' },
  { value: '^BSESN', label: 'SENSEX',   flag: '🇮🇳' },
  { value: '^GSPC',  label: 'S&P 500',  flag: '🇺🇸' },
  { value: '^IXIC',  label: 'NASDAQ',   flag: '🇺🇸' },
]

function safeNum(v: unknown, fallback = 0): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function fmtPct(v: unknown, fallback = 0): string {
  const n = safeNum(v, fallback)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

function fmtNum(v: unknown, digits = 2, fallback = 0): string {
  return safeNum(v, fallback).toFixed(digits)
}

function MetricCard({ label, value, sub, positive }: {
  label: string; value: string; sub?: string; positive?: boolean
}) {
  return (
    <div className="bg-gray-800/40 rounded-xl p-3">
      <p className="text-gray-500 text-xs mb-1">{label}</p>
      <p className={`text-base font-bold tabular-nums ${
        positive === undefined ? 'text-white' : positive ? 'text-green-400' : 'text-red-400'
      }`}>{value}</p>
      {sub && <p className="text-gray-600 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

export default function BenchmarkChart({ holdings, className = '' }: Props) {
  const [data,      setData]      = useState<BenchmarkResult | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [benchmark, setBenchmark] = useState('^NSEI')

  useEffect(() => {
    if (!holdings || holdings.length === 0) return
    let cancelled = false
    const run = async () => {
      setLoading(true); setError(null)
      try {
        const res = await apiClient.post('/api/analytics/benchmark', { holdings, benchmark })
        if (!cancelled) setData(res.data ?? null)
      } catch (e: any) {
        if (!cancelled) setError(e.response?.data?.detail || 'Benchmark comparison failed')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [holdings, benchmark])

  const alpha           = safeNum(data?.alpha)
  const beta            = safeNum(data?.beta, 1)
  const portfolioReturn = safeNum(data?.portfolio_return)
  const benchmarkReturn = safeNum(data?.benchmark_return)
  const correlation     = safeNum(data?.correlation)
  const infoRatio       = safeNum(data?.information_ratio)
  const chartData       = Array.isArray(data?.chart_data) ? data!.chart_data! : []
  const isOutperforming = alpha > 0
  const benchmarkLabel  = BENCHMARKS.find(b => b.value === benchmark)?.label ?? benchmark
  const hasChart        = chartData.length > 0

  return (
    <div className={`card p-5 ${className}`}>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-blue-400" />
          <h3 className="text-white font-semibold text-sm">vs Benchmark</h3>
          {data && !loading && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
              isOutperforming ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
            }`}>
              {isOutperforming ? '↑ Outperforming' : '↓ Underperforming'}
            </span>
          )}
        </div>
        <div className="flex gap-1 flex-wrap">
          {BENCHMARKS.map(b => (
            <button key={b.value} onClick={() => setBenchmark(b.value)}
              className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
                benchmark === b.value ? 'bg-blue-600 text-white' : 'bg-gray-800/60 text-gray-400 hover:text-white'
              }`}>
              {b.flag} {b.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && !loading && (
        <div className="h-32 flex items-center justify-center text-red-400 text-sm">{error}</div>
      )}

      {data && !loading && !error && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
            <MetricCard label="Your Return"          value={fmtPct(portfolioReturn)} positive={portfolioReturn >= 0} />
            <MetricCard label={`${benchmarkLabel}`}  value={fmtPct(benchmarkReturn)} positive={benchmarkReturn >= 0} />
            <MetricCard label="Alpha"                value={fmtPct(alpha)} sub="Return above benchmark" positive={alpha >= 0} />
            <MetricCard label="Beta"                 value={fmtNum(beta, 2, 1)}
              sub={beta > 1 ? 'More volatile' : beta < 1 ? 'Less volatile' : 'Matches market'} />
          </div>

          {hasChart ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickFormatter={(v: unknown) => String(v).slice(5)}
                  axisLine={{ stroke: '#374151' }}
                />
                <YAxis
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  axisLine={{ stroke: '#374151' }}
                  tickFormatter={(v: unknown) => {
                    const n = safeNum(v)
                    return `${n >= 0 ? '+' : ''}${n.toFixed(0)}%`
                  }}
                  domain={['auto', 'auto']}
                  width={52}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827', border: '1px solid #374151',
                    borderRadius: '8px', color: '#fff', fontSize: '12px',
                  }}
                  formatter={(value: unknown, name: unknown): [string, string] => [
                    fmtPct(value),
                    name === 'portfolio' ? 'Your Portfolio' : benchmarkLabel,
                  ]}
                />
                <Legend
                  formatter={(v: unknown) => (
                    <span className="text-gray-300 text-xs">
                      {v === 'portfolio' ? 'Your Portfolio' : benchmarkLabel}
                    </span>
                  )}
                />
                <ReferenceLine y={0} stroke="#374151" />
                <Line dataKey="portfolio" stroke="#3b82f6" strokeWidth={2} dot={false} name="portfolio" />
                <Line dataKey="benchmark" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="benchmark" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-32 flex items-center justify-center text-gray-600 text-sm">
              Chart data unavailable
            </div>
          )}

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.04] flex-wrap gap-2">
            <div className="flex items-center gap-2">
              {isOutperforming
                ? <TrendingUp size={13} className="text-green-400" />
                : <TrendingDown size={13} className="text-red-400" />}
              <span className={`text-xs ${isOutperforming ? 'text-green-400' : 'text-red-400'}`}>
                {Math.abs(alpha).toFixed(1)}% {isOutperforming ? 'above' : 'below'} {benchmarkLabel}
              </span>
            </div>
            <div className="flex gap-3 text-xs text-gray-600">
              <span>Correlation: {(correlation * 100).toFixed(0)}%</span>
              <span>Info Ratio: {infoRatio.toFixed(2)}</span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
