import { useState, useMemo, useCallback, memo, lazy, Suspense, useEffect } from 'react'
import { Link} from 'react-router-dom'
import { TrendingUp, TrendingDown, FileText, Save } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import Navbar            from '../components/Navbar'
import UploadPortfolio   from '../components/UploadPortfolio'
import SummaryCards      from '../components/SummaryCards'
import SectorChart       from '../components/SectorChart'
import HoldingsChart     from '../components/HoldingsChart'
import PriceAlertBanner  from '../components/PriceAlertBanner'
import LivePriceTicker   from '../components/LivePriceTicker'
import Section           from '../components/ui/Section'
import SavePortfolioModal from '../components/SavePortfolioModal'
import {
  MetricCardSkeleton,
  ChartSkeleton,
  TodayDashboardSkeleton,
  RiskMetricsSkeleton,
} from '../components/ui/Skeleton'
import { useWebSocket }  from '../hooks/useWebSocket'
import { portfolioApi }  from '../services/api'
// import { useAuth }       from '../context/AuthContext'

// Stage 2 — lazy
const RiskMetrics       = lazy(() => import('../components/RiskMetrics'))
const AdvancedMetrics   = lazy(() => import('../components/AdvancedMetrics'))
const BenchmarkChart    = lazy(() => import('../components/BenchmarkChart'))
const ScenarioSimulator = lazy(() => import('../components/ScenarioSimulator'))
const PredictionChart   = lazy(() => import('../components/PredictionChart'))

// Stage 3 — AI last
const TodayDashboard = lazy(() => import('../components/TodayDashboard'))
const AIInsights     = lazy(() => import('../components/AIInsights'))

/* ── Types ── */
interface Holding {
  symbol: string; quantity: number; avg_buy_price: number
  sector?: string; current_price: number | null; currency: string
  invested_value: number; current_value: number | null
  pnl: number | null; pnl_pct: number | null
}
interface PortfolioData {
  total_holdings: number; holdings: Holding[]
  summary: any; source?: string; validation?: any
}

function fmt(v: number | null | undefined, prefix = '₹') {
  if (v == null) return '—'
  return `${prefix}${v.toLocaleString('en-IN')}`
}

/* ── Holdings row ── */
const HoldingsRow = memo(function HoldingsRow({
  h, isStale,
}: { h: Holding; isStale: boolean }) {
  const isProfit = (h.pnl ?? 0) >= 0
  const prefix   = h.currency === 'USD' ? '$' : '₹'
  return (
    <tr className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group">
      <td className="py-3 pr-4 font-semibold text-blue-400 group-hover:text-blue-300 whitespace-nowrap">
        {h.symbol}
      </td>
      <td className="py-3 pr-4 text-gray-400 text-sm">{h.sector || '—'}</td>
      <td className="py-3 pr-4">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          h.currency === 'USD' ? 'bg-green-900/40 text-green-400' : 'bg-blue-900/40 text-blue-400'
        }`}>{h.currency}</span>
      </td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">{h.quantity}</td>
      <td className="py-3 pr-4 text-gray-400 tabular-nums">{fmt(h.avg_buy_price, prefix)}</td>
      <td className="py-3 pr-4">
        <LivePriceTicker price={h.current_price} currency={h.currency} stale={isStale} />
      </td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">{fmt(h.invested_value, prefix)}</td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">
        {h.current_value ? fmt(h.current_value, prefix) : '—'}
      </td>
      <td className={`py-3 pr-4 font-medium tabular-nums ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        <span className="flex items-center gap-1">
          {isProfit ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {h.pnl != null ? fmt(h.pnl, prefix) : '—'}
        </span>
      </td>
      <td className={`py-3 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        {h.pnl_pct != null ? (
          <span className={`px-2 py-0.5 rounded text-xs tabular-nums ${
            isProfit ? 'bg-green-900/25' : 'bg-red-900/25'
          }`}>
            {isProfit ? '+' : ''}{h.pnl_pct.toFixed(2)}%
          </span>
        ) : '—'}
      </td>
    </tr>
  )
})

/* ── React Query hooks ── */
function useRiskMetrics(holdings: Holding[], enabled: boolean) {
  return useQuery({
    queryKey:  ['risk', holdings.map(h => h.symbol).sort().join(',')],
    queryFn:   () => portfolioApi.getRisk(holdings).then(r => r.data),
    enabled:   enabled && holdings.length > 0,
    staleTime: 10 * 60 * 1000,
  })
}

function useAdvancedMetrics(holdings: Holding[], riskMetrics: any, enabled: boolean) {
  return useQuery({
    queryKey:  ['advanced', holdings.map(h => h.symbol).sort().join(',')],
    queryFn:   () => portfolioApi.getAdvanced(holdings, riskMetrics).then(r => r.data),
    enabled:   enabled && !!riskMetrics,
    staleTime: 10 * 60 * 1000,
  })
}

/* ── Dashboard ── */
export default function Dashboard() {
  // const navigate         = useNavigate()
  // const { isLoggedIn }   = useAuth()

  const [portfolioData,  setPortfolioData]  = useState<PortfolioData | null>(null)
  const [showSave,       setShowSave]       = useState(false)
  const [savedPortfolio, setSavedPortfolio] = useState<{ id: number; name: string } | null>(null)

  /* ── Baselines for alert engine ── */
  const baselines = useMemo(() => {
    const map: Record<string, number> = {}
    portfolioData?.holdings.forEach(h => {
      if (h.current_price) map[h.symbol] = h.current_price
    })
    return map
  }, [portfolioData])

  const symbols = useMemo(
    () => portfolioData?.holdings.map(h => h.symbol) ?? [],
    [portfolioData]
  )

  const {
    prices: livePrices, alerts, connected,
    staleSymbols, lastUpdated, nextRefresh, dismissAlert,
  } = useWebSocket({ symbols, baselines, enabled: !!portfolioData })

  /* ── Enrich holdings with live prices ── */
  const enrichedHoldings = useMemo(() => {
    if (!portfolioData) return []
    return portfolioData.holdings.map(h => {
      const live = livePrices[h.symbol]
      if (live == null) return h
      const inv    = h.invested_value
      const cur    = live * h.quantity
      const pnl    = cur - inv
      const pnlPct = inv > 0 ? (pnl / inv) * 100 : 0
      return {
        ...h,
        current_price: live,
        current_value: Math.round(cur    * 100) / 100,
        pnl:           Math.round(pnl    * 100) / 100,
        pnl_pct:       Math.round(pnlPct * 100) / 100,
      }
    })
  }, [portfolioData, livePrices])

  /* ── React Query ── */
  const { data: riskMetrics,    isLoading: riskLoading }    = useRiskMetrics(enrichedHoldings, !!portfolioData)
  const { data: advancedMetrics }                            = useAdvancedMetrics(enrichedHoldings, riskMetrics, !!portfolioData)

  /* ── Persist to sessionStorage for Reports page ── */
  const handleUpload = useCallback((d: PortfolioData) => {
    setPortfolioData(d)
    try {
      sessionStorage.setItem('pa_portfolio', JSON.stringify({
        holdings:        d.holdings,
        summary:         d.summary,
        riskMetrics:     null,
        advancedMetrics: null,
      }))
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (riskMetrics && portfolioData) {
      try {
        const existing = JSON.parse(sessionStorage.getItem('pa_portfolio') || '{}')
        sessionStorage.setItem('pa_portfolio', JSON.stringify({
          ...existing,
          riskMetrics,
          advancedMetrics: advancedMetrics || null,
        }))
      } catch { /* ignore */ }
    }
  }, [riskMetrics, advancedMetrics, portfolioData])

  const handleReset = useCallback(() => {
    setPortfolioData(null)
    setSavedPortfolio(null)
    sessionStorage.removeItem('pa_portfolio')
  }, [])

  /* ── FIX: convert Date → string for Navbar ── */
  const lastUpdatedStr = useMemo(
    () => lastUpdated instanceof Date
      ? lastUpdated.toISOString()
      : typeof lastUpdated === 'string'
      ? lastUpdated
      : null,
    [lastUpdated]
  )

  const { inr, usd } = portfolioData?.summary ?? {}

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar
        connected={connected}
        lastUpdated={lastUpdatedStr}
        nextRefresh={nextRefresh}
        holdings={enrichedHoldings}
      />
      <PriceAlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-8 md:py-12">

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-1">
              {portfolioData ? 'Portfolio Dashboard' : 'Your Dashboard'}
            </h1>
            <p className="text-gray-500 text-sm">
              {portfolioData
                ? `${portfolioData.total_holdings} holdings · ${connected ? '🟢 Live' : '🔴 Offline'}`
                : 'Upload your portfolio to get started'
              }
            </p>
          </div>

          {portfolioData && (
            <div className="flex items-center gap-2 shrink-0">
              {/* PDF Report */}
              <Link
                to="/reports"
                className="flex items-center gap-1.5 text-sm border border-purple-700/60 bg-purple-950/20 hover:bg-purple-950/40 text-purple-400 px-3 py-2 rounded-xl transition-all"
              >
                <FileText size={14} />
                <span className="hidden sm:block">PDF</span>
              </Link>

              {/* Save Portfolio */}
              <button
                onClick={() => setShowSave(true)}
                className="flex items-center gap-1.5 text-sm border border-green-700/60 bg-green-950/20 hover:bg-green-950/40 text-green-400 px-3 py-2 rounded-xl transition-all"
              >
                <Save size={14} />
                <span className="hidden sm:block">
                  {savedPortfolio ? `Saved` : 'Save'}
                </span>
              </button>

              {/* Reset */}
              <button
                onClick={handleReset}
                className="text-sm text-gray-500 hover:text-white border border-gray-700/60 hover:border-gray-500 px-3 py-2 rounded-xl transition-all"
              >
                ↑ New
              </button>
            </div>
          )}
        </div>

        {!portfolioData ? (
          <UploadPortfolio onUploadSuccess={handleUpload} />
        ) : (
          <div className="space-y-8 md:space-y-10">

            {/* ━━ STAGE 1: IMMEDIATE ━━ */}

            <Section delay={0}>
              <SummaryCards summary={portfolioData.summary} />
            </Section>

            <Section delay={80}>
              <h2 className="text-lg font-semibold text-white mb-4">📈 Portfolio Overview</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <SectorChart   holdings={enrichedHoldings} />
                <HoldingsChart holdings={enrichedHoldings} />
              </div>
            </Section>

            {/* Holdings table */}
            <Section delay={120}>
              <div className="card p-5 md:p-6">
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-lg font-semibold text-white">
                    Holdings
                    <span className="ml-2 text-sm font-normal text-gray-500">
                      {portfolioData.total_holdings} stocks
                    </span>
                  </h2>
                  <div className="flex items-center gap-3">
                    {staleSymbols.length > 0 && (
                      <span className="text-xs text-yellow-600">⚠ {staleSymbols.length} stale</span>
                    )}
                    <div className={`flex items-center gap-1.5 text-xs ${connected ? 'text-green-400' : 'text-gray-600'}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-gray-700'}`} />
                      {connected ? 'Live' : 'Offline'}
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto -mx-5 md:-mx-6 px-5 md:px-6">
                  <table className="w-full text-sm min-w-[800px]">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        {['Symbol','Sector','Currency','Qty','Avg Price','Live Price','Invested','Current','P&L','Return'].map(col => (
                          <th key={col} className="text-left text-gray-600 font-medium py-3 pr-4 text-xs uppercase tracking-wide whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {enrichedHoldings.map(h => (
                        <HoldingsRow
                          key={h.symbol}
                          h={h}
                          isStale={staleSymbols.includes(h.symbol)}
                        />
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-white/[0.08]">
                        <td colSpan={7} className="py-3 text-gray-600 text-xs font-medium uppercase tracking-wide">
                          Total · {portfolioData.total_holdings} holdings
                        </td>
                        <td className="py-3 pr-4 font-semibold text-sm">
                          {inr?.total_current_value > 0 && (
                            <div className="text-white tabular-nums">
                              ₹{inr.total_current_value.toLocaleString('en-IN')}
                            </div>
                          )}
                          {usd?.total_current_value > 0 && (
                            <div className="text-white tabular-nums">
                              ${usd.total_current_value.toLocaleString()}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4 font-semibold text-sm">
                          {inr && (
                            <div className={`tabular-nums ${inr.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ₹{inr.total_pnl.toLocaleString('en-IN')}
                            </div>
                          )}
                          {usd && (
                            <div className={`tabular-nums ${usd.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ${usd.total_pnl.toLocaleString()}
                            </div>
                          )}
                        </td>
                        <td className="py-3 font-semibold text-sm">
                          {inr?.total_invested > 0 && (
                            <div className={`tabular-nums ${inr.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {inr.total_pnl_pct >= 0 ? '+' : ''}{inr.total_pnl_pct}%
                            </div>
                          )}
                          {usd?.total_invested > 0 && (
                            <div className={`tabular-nums ${usd.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {usd.total_pnl_pct >= 0 ? '+' : ''}{usd.total_pnl_pct}%
                            </div>
                          )}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </Section>

            {/* ━━ STAGE 2: ANALYTICS ━━ */}

            <Section delay={0}>
              <h2 className="text-lg font-semibold text-white mb-4">📊 Risk Analysis</h2>
              {riskLoading ? (
                <RiskMetricsSkeleton />
              ) : (
                <Suspense fallback={<RiskMetricsSkeleton />}>
                  <RiskMetrics
                    holdings={enrichedHoldings}
                    onRiskLoad={() => {}}
                    preloadedData={riskMetrics}
                  />
                </Suspense>
              )}
            </Section>

            {riskMetrics && (
              <Section delay={0}>
                <h2 className="text-lg font-semibold text-white mb-4">🔬 Advanced Analytics</h2>
                <Suspense fallback={
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => <MetricCardSkeleton key={i} />)}
                  </div>
                }>
                  <AdvancedMetrics
                    holdings={enrichedHoldings}
                    riskMetrics={riskMetrics}
                    preloadedData={advancedMetrics}
                    onLoad={() => {}}
                  />
                </Suspense>
              </Section>
            )}

            {riskMetrics && (
              <Section delay={0}>
                <Suspense fallback={<ChartSkeleton />}>
                  <BenchmarkChart holdings={enrichedHoldings} />
                </Suspense>
              </Section>
            )}

            <Section delay={0}>
              <Suspense fallback={<div className="card p-6 h-32 skeleton" />}>
                <ScenarioSimulator holdings={enrichedHoldings} />
              </Suspense>
            </Section>

            {/* ━━ PREDICTIONS ━━ */}

            <Section delay={0}>
              <h2 className="text-lg font-semibold text-white mb-1">🔮 30-Day Predictions</h2>
              <p className="text-gray-600 text-sm mb-4">
                Click any holding · ARIMA + RF + LightGBM
              </p>
              <div className="card p-4 space-y-2">
                {enrichedHoldings.map(h => (
                  <Suspense
                    key={h.symbol}
                    fallback={
                      <div className="border border-gray-800 rounded-xl px-5 py-4">
                        <div className="skeleton h-4 w-32" />
                      </div>
                    }
                  >
                    <PredictionChart symbol={h.symbol} currency={h.currency} />
                  </Suspense>
                ))}
              </div>
            </Section>

            {/* ━━ STAGE 3: AI — NEVER BLOCKS ━━ */}

            <Section delay={0} minHeight={260}>
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-lg font-semibold text-white">🎯 What To Do Today</h2>
                  <span className="text-xs text-gray-600 bg-gray-800/60 px-2 py-0.5 rounded-full">
                    AI Decision Engine
                  </span>
                </div>
                <Suspense fallback={<TodayDashboardSkeleton />}>
                  <TodayDashboard
                    holdings={enrichedHoldings}
                    riskMetrics={riskMetrics}
                    advancedMetrics={advancedMetrics}
                    summary={portfolioData.summary}
                  />
                </Suspense>
              </div>
            </Section>

            {riskMetrics && (
              <Section delay={0}>
                <h2 className="text-lg font-semibold text-white mb-4">🧠 AI Insights</h2>
                <Suspense fallback={<div className="card p-8 skeleton h-48" />}>
                  <AIInsights
                    holdings={enrichedHoldings}
                    riskMetrics={riskMetrics}
                    summary={portfolioData.summary}
                  />
                </Suspense>
              </Section>
            )}

          </div>
        )}
      </div>

      {/* Save Portfolio Modal */}
      {showSave && portfolioData && (
        <SavePortfolioModal
          holdings={enrichedHoldings}
          summary={portfolioData.summary}
          onClose={() => setShowSave(false)}
          onSaved={(id, name) => setSavedPortfolio({ id, name })}
        />
      )}
    </div>
  )
}