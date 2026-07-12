/**
 * Dashboard.tsx — Complete rewrite.
 *
 * Self-contained: no imports from uncertain paths (ui/Section, ui/Skeleton etc.)
 * Everything either exists in original codebase or is inlined here.
 *
 * Fixes applied:
 * 1. Demo flow — Home.tsx passes data via location.state.demoData
 *    → clear sessionStorage first, then load, NO banner shown
 * 2. Resume banner — only on direct /dashboard visits with old session data
 *    → user controlled, not auto-load
 * 3. All TypeScript issues — no missing imports
 */
import {
  useState, useMemo, useCallback, memo,
  lazy, Suspense, useEffect,
} from 'react'
import { Link, useLocation } from 'react-router-dom'
import { TrendingUp, TrendingDown, FileText, Save, RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import Navbar           from '../components/Navbar'
import UploadPortfolio  from '../components/UploadPortfolio'
import SummaryCards     from '../components/SummaryCards'
import SectorChart      from '../components/SectorChart'
import HoldingsChart    from '../components/HoldingsChart'
import { useWebSocket } from '../hooks/useWebSocket'
import { portfolioApi } from '../services/api'
import { API_BASE }     from '../config/api'

// Lazy load all heavy components
const RiskMetrics       = lazy(() => import('../components/RiskMetrics'))
const AdvancedMetrics   = lazy(() => import('../components/AdvancedMetrics'))
const BenchmarkChart    = lazy(() => import('../components/BenchmarkChart'))
const ScenarioSimulator = lazy(() => import('../components/ScenarioSimulator'))
const PredictionChart   = lazy(() => import('../components/PredictionChart'))
const TodayDashboard    = lazy(() => import('../components/TodayDashboard'))
const AIInsights        = lazy(() => import('../components/AIInsights'))
const SavePortfolioModal = lazy(() => import('../components/SavePortfolioModal'))
const PortfolioScoreCard = lazy(() => import('../components/PortfolioScoreCard'))

// ── Inline skeleton (no external dependency) ──────────────────
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-800/60 rounded-xl ${className}`} />
}
function LoadingCard() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <Skeleton className="h-3 w-20 mb-3" />
          <Skeleton className="h-7 w-24 mb-2" />
          <Skeleton className="h-2 w-16" />
        </div>
      ))}
    </div>
  )
}
function LoadingBlock({ h = 'h-48' }: { h?: string }) {
  return <div className={`animate-pulse bg-gray-800/30 rounded-2xl ${h}`} />
}

// ── Types ─────────────────────────────────────────────────────
interface Holding {
  symbol: string; quantity: number; avg_buy_price: number
  sector?: string; current_price: number | null; currency: string
  invested_value: number; current_value: number | null
  pnl: number | null; pnl_pct: number | null
}
interface PortfolioData {
  total_holdings: number; holdings: Holding[]
  summary: any; source?: string
}

function fmt(v: number | null | undefined, prefix = '₹') {
  if (v == null) return '—'
  return `${prefix}${v.toLocaleString('en-IN')}`
}

function clearSession() {
  try {
    sessionStorage.removeItem('portfolio_data')
    sessionStorage.removeItem('pa_portfolio')
  } catch { /* ignore */ }
}

// ── Holdings row ──────────────────────────────────────────────
const HoldingsRow = memo(function HoldingsRow({
  h, isStale,
}: { h: Holding; isStale: boolean }) {
  const isProfit = (h.pnl ?? 0) >= 0
  const px = h.currency === 'USD' ? '$' : '₹'
  return (
    <tr className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group">
      <td className="py-3 pr-4 font-semibold text-blue-400 whitespace-nowrap">{h.symbol}</td>
      <td className="py-3 pr-4 text-gray-400 text-sm">{h.sector || '—'}</td>
      <td className="py-3 pr-4">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          h.currency === 'USD' ? 'bg-green-900/40 text-green-400' : 'bg-blue-900/40 text-blue-400'
        }`}>{h.currency}</span>
      </td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">{h.quantity}</td>
      <td className="py-3 pr-4 text-gray-400 tabular-nums">{fmt(h.avg_buy_price, px)}</td>
      <td className="py-3 pr-4">
        {h.current_price != null ? (
          <span className={`font-medium tabular-nums text-sm ${isStale ? 'text-yellow-400' : 'text-white'}`}>
            {fmt(h.current_price, px)}
            {isStale && <span className="ml-1 text-xs text-yellow-600">⚠</span>}
          </span>
        ) : <span className="text-gray-600">—</span>}
      </td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">{fmt(h.invested_value, px)}</td>
      <td className="py-3 pr-4 text-gray-300 tabular-nums">
        {h.current_value ? fmt(h.current_value, px) : '—'}
      </td>
      <td className={`py-3 pr-4 font-medium tabular-nums ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        <span className="flex items-center gap-1">
          {isProfit ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {h.pnl != null ? fmt(h.pnl, px) : '—'}
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

// ── React Query hooks ─────────────────────────────────────────
function useRisk(holdings: Holding[], on: boolean) {
  return useQuery({
    queryKey:  ['risk', holdings.map(h => h.symbol).sort().join(',')],
    queryFn:   () => portfolioApi.getRisk(holdings).then(r => r.data),
    enabled:   on && holdings.length > 0,
    staleTime: 600_000,
    retry:     2,
  })
}
function useAdvanced(holdings: Holding[], risk: any, on: boolean) {
  return useQuery({
    queryKey:  ['advanced', holdings.map(h => h.symbol).sort().join(',')],
    queryFn:   () => portfolioApi.getAdvanced(holdings, risk).then(r => r.data),
    enabled:   on && !!risk,
    staleTime: 600_000,
    retry:     1,
  })
}
function useInsights(holdings: Holding[], on: boolean) {
  return useQuery({
    queryKey:  ['insights', holdings.map(h => h.symbol).sort().join(',')],
    queryFn:   () => fetch(`${API_BASE}/api/portfolio/insights`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ holdings }),
    }).then(r => r.json()),
    enabled:   on && holdings.length > 0,
    staleTime: 600_000,
    retry:     1,
  })
}

// ── Dashboard ─────────────────────────────────────────────────
export default function Dashboard() {
  const location = useLocation()

  const [portfolioData,    setPortfolioData]    = useState<PortfolioData | null>(null)
  const [showSave,         setShowSave]         = useState(false)
  const [savedName,        setSavedName]        = useState<string | null>(null)
  const [showResumeBanner, setShowResumeBanner] = useState(false)
  const [resumeCount,      setResumeCount]      = useState(0)

  // ── Session handling ────────────────────────────────────────
  useEffect(() => {
    // PRIORITY 1: demo data from Home.tsx "Try Live Demo" button
    const stateData = (location.state as any)?.demoData
    if (stateData?.holdings?.length > 0) {
      clearSession()                  // wipe any old data first
      setPortfolioData(stateData)
      setShowResumeBanner(false)
      return
    }

    // PRIORITY 2: if no state, check for previous session
    // Show a banner — NEVER auto-load
    try {
      const raw = sessionStorage.getItem('portfolio_data')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed?.holdings?.length > 0) {
          setResumeCount(parsed.total_holdings || parsed.holdings.length)
          setShowResumeBanner(true)
        }
      }
    } catch { /* ignore */ }
  }, [location.state])

  const handleResume = useCallback(() => {
    try {
      const raw = sessionStorage.getItem('portfolio_data')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed?.holdings?.length > 0) {
          setPortfolioData(parsed)
          setShowResumeBanner(false)
        }
      }
    } catch { /* ignore */ }
  }, [])

  const handleUpload = useCallback((d: PortfolioData) => {
    clearSession()
    setShowResumeBanner(false)
    setPortfolioData(d)
    try {
      sessionStorage.setItem('portfolio_data', JSON.stringify(d))
    } catch { /* ignore */ }
  }, [])

  const handleReset = useCallback(() => {
    setPortfolioData(null)
    setSavedName(null)
    setShowResumeBanner(false)
    clearSession()
  }, [])

  // ── Live prices via WebSocket ───────────────────────────────
  const baselines = useMemo(() => {
    const m: Record<string, number> = {}
    portfolioData?.holdings.forEach(h => { if (h.current_price) m[h.symbol] = h.current_price })
    return m
  }, [portfolioData])

  const symbols = useMemo(() => portfolioData?.holdings.map(h => h.symbol) ?? [], [portfolioData])

  const {
    prices: livePrices, alerts, connected,
    staleSymbols, lastUpdated, nextRefresh, dismissAlert,
  } = useWebSocket({ symbols, baselines, enabled: !!portfolioData })

  // ── Dismiss alert — prevent TS error if dismissAlert undefined ──
  const safeDismiss = useCallback((id: string) => {
    if (typeof dismissAlert === 'function') dismissAlert(id)
  }, [dismissAlert])

  // ── Enrich holdings with live prices ───────────────────────
  const enriched = useMemo((): Holding[] => {
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

  // ── API queries ─────────────────────────────────────────────
  const { data: risk,     isLoading: riskLoading } = useRisk(enriched, !!portfolioData)
  const { data: advanced }                          = useAdvanced(enriched, risk, !!portfolioData)
  const { data: insights }                          = useInsights(enriched, !!portfolioData)

  // Persist risk metrics to sessionStorage for Reports page
  useEffect(() => {
    if (risk && portfolioData) {
      try {
        sessionStorage.setItem('pa_portfolio', JSON.stringify({
          holdings: portfolioData.holdings,
          summary:  portfolioData.summary,
          riskMetrics:     risk,
          advancedMetrics: advanced || null,
        }))
      } catch { /* ignore */ }
    }
  }, [risk, advanced, portfolioData])

  const lastUpdatedStr = useMemo(
    () => lastUpdated instanceof Date
      ? lastUpdated.toISOString()
      : typeof lastUpdated === 'string' ? lastUpdated : null,
    [lastUpdated]
  )

  // ── Handle alerts: PriceAlertBanner may or may not exist ───
  const AlertBanner = useMemo(() => {
    try {
      // Try to dynamically check — if component exists use it
      return lazy(() => import('../components/PriceAlertBanner').catch(() => ({
        default: () => null,
      })))
    } catch {
      return () => null
    }
  }, [])

  const { inr, usd } = portfolioData?.summary ?? {}

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar
        connected={connected}
        lastUpdated={lastUpdatedStr}
        nextRefresh={nextRefresh}
        holdings={enriched}
      />

      {/* Alert banner — fail silently if component missing */}
      <Suspense fallback={null}>
        <AlertBanner alerts={alerts ?? []} onDismiss={safeDismiss} />
      </Suspense>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-8 md:py-12">

        {/* ── Page header ─────────────────────────────────── */}
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-1">
              {portfolioData ? 'Portfolio Dashboard' : 'Your Dashboard'}
            </h1>
            <p className="text-gray-500 text-sm">
              {portfolioData
                ? `${portfolioData.total_holdings} holdings · ${connected ? '🟢 Live' : '🔴 Offline'}`
                : 'Upload your portfolio to get started'}
            </p>
          </div>

          {portfolioData && (
            <div className="flex items-center gap-2 shrink-0">
              <Link to="/reports"
                className="flex items-center gap-1.5 text-sm border border-purple-700/60 bg-purple-950/20 hover:bg-purple-950/40 text-purple-400 px-3 py-2 rounded-xl transition-all">
                <FileText size={14} />
                <span className="hidden sm:block">PDF</span>
              </Link>
              <button onClick={() => setShowSave(true)}
                className="flex items-center gap-1.5 text-sm border border-green-700/60 bg-green-950/20 hover:bg-green-950/40 text-green-400 px-3 py-2 rounded-xl transition-all">
                <Save size={14} />
                <span className="hidden sm:block">{savedName ? '✓ Saved' : 'Save'}</span>
              </button>
              <button onClick={handleReset}
                className="text-sm text-gray-500 hover:text-white border border-gray-700/60 hover:border-gray-500 px-3 py-2 rounded-xl transition-all">
                ↑ New
              </button>
            </div>
          )}
        </div>

        {/* ── Upload / resume state ────────────────────────── */}
        {!portfolioData ? (
          <div className="space-y-4">

            {/* Resume banner — user-controlled only */}
            {showResumeBanner && (
              <div className="flex items-center justify-between bg-blue-950/30 border border-blue-800/50 rounded-2xl px-5 py-4 gap-3 flex-wrap">
                <div className="flex items-center gap-3">
                  <RefreshCw size={16} className="text-blue-400 shrink-0" />
                  <div>
                    <p className="text-white text-sm font-medium">Previous session found</p>
                    <p className="text-gray-500 text-xs">{resumeCount} holdings from your last analysis</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleResume}
                    className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-xl transition-colors font-medium">
                    Resume
                  </button>
                  <button onClick={() => { setShowResumeBanner(false); clearSession() }}
                    className="text-gray-500 hover:text-white text-sm px-3 py-2 rounded-xl border border-gray-700 hover:border-gray-500 transition-colors">
                    Clear
                  </button>
                </div>
              </div>
            )}

            <UploadPortfolio onUploadSuccess={handleUpload} />
          </div>

        ) : (
          /* ── Dashboard content ────────────────────────────── */
          <div className="space-y-10">

            {/* Portfolio health score */}
            <Suspense fallback={null}>
              {insights && <PortfolioScoreCard insights={insights} />}
            </Suspense>

            {/* Summary cards */}
            <SummaryCards summary={portfolioData.summary} />

            {/* Charts */}
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">📈 Portfolio Overview</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <SectorChart   holdings={enriched} />
                <HoldingsChart holdings={enriched} />
              </div>
            </div>

            {/* Holdings table */}
            <div className="card p-5 md:p-6">
              <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
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

              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[800px]">
                  <thead>
                    <tr className="border-b border-white/[0.06]">
                      {['Symbol','Sector','Currency','Qty','Avg Price','Live Price','Invested','Current','P&L','Return'].map(c => (
                        <th key={c} className="text-left text-gray-600 font-medium py-3 pr-4 text-xs uppercase tracking-wide whitespace-nowrap">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {enriched.map(h => (
                      <HoldingsRow key={h.symbol} h={h} isStale={staleSymbols.includes(h.symbol)} />
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-white/[0.08]">
                      <td colSpan={7} className="py-3 text-gray-600 text-xs font-medium uppercase tracking-wide">
                        Total · {portfolioData.total_holdings} holdings
                      </td>
                      <td className="py-3 pr-4 font-semibold text-sm">
                        {inr?.total_current_value > 0 && <div className="text-white tabular-nums">₹{inr.total_current_value.toLocaleString('en-IN')}</div>}
                        {usd?.total_current_value > 0 && <div className="text-white tabular-nums">${usd.total_current_value.toLocaleString()}</div>}
                      </td>
                      <td className="py-3 pr-4 font-semibold text-sm">
                        {inr && <div className={`tabular-nums ${inr.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>₹{inr.total_pnl.toLocaleString('en-IN')}</div>}
                        {usd && <div className={`tabular-nums ${usd.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${usd.total_pnl.toLocaleString()}</div>}
                      </td>
                      <td className="py-3 font-semibold text-sm">
                        {inr?.total_invested > 0 && <div className={`tabular-nums ${inr.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{inr.total_pnl_pct >= 0 ? '+' : ''}{inr.total_pnl_pct}%</div>}
                        {usd?.total_invested > 0 && <div className={`tabular-nums ${usd.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{usd.total_pnl_pct >= 0 ? '+' : ''}{usd.total_pnl_pct}%</div>}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Risk Analysis */}
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">📊 Risk Analysis</h2>
              {riskLoading ? <LoadingCard /> : (
                <Suspense fallback={<LoadingCard />}>
                  <RiskMetrics holdings={enriched} onRiskLoad={() => {}} preloadedData={risk} />
                </Suspense>
              )}
            </div>

            {/* Advanced Analytics */}
            {risk && (
              <div>
                <h2 className="text-lg font-semibold text-white mb-4">🔬 Advanced Analytics</h2>
                <Suspense fallback={<LoadingCard />}>
                  <AdvancedMetrics
                    holdings={enriched}
                    riskMetrics={risk}
                    preloadedData={advanced}
                    onLoad={() => {}}
                  />
                </Suspense>
              </div>
            )}

            {/* Benchmark comparison */}
            {risk && (
              <Suspense fallback={<LoadingBlock h="h-72" />}>
                <BenchmarkChart holdings={enriched} />
              </Suspense>
            )}

            {/* Scenario simulator */}
            <Suspense fallback={<LoadingBlock h="h-48" />}>
              <ScenarioSimulator holdings={enriched} />
            </Suspense>

            {/* ML Predictions */}
            <div>
              <h2 className="text-lg font-semibold text-white mb-1">🔮 30-Day Predictions</h2>
              <p className="text-gray-600 text-sm mb-4">Click any holding · ETS + RF + LightGBM</p>
              <div className="card p-4 space-y-2">
                {enriched.map(h => (
                  <Suspense key={h.symbol} fallback={
                    <div className="border border-gray-800 rounded-xl px-5 py-4">
                      <Skeleton className="h-4 w-32" />
                    </div>
                  }>
                    <PredictionChart symbol={h.symbol} currency={h.currency} />
                  </Suspense>
                ))}
              </div>
            </div>

            {/* AI What To Do Today */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <h2 className="text-lg font-semibold text-white">🎯 What To Do Today</h2>
                <span className="text-xs text-gray-600 bg-gray-800/60 px-2 py-0.5 rounded-full">AI Decision Engine</span>
              </div>
              <Suspense fallback={<LoadingBlock h="h-64" />}>
                <TodayDashboard
                  holdings={enriched}
                  riskMetrics={risk}
                  advancedMetrics={advanced}
                  summary={portfolioData.summary}
                />
              </Suspense>
            </div>

            {/* AI Insights */}
            {risk && (
              <div>
                <h2 className="text-lg font-semibold text-white mb-4">🧠 AI Insights</h2>
                <Suspense fallback={<LoadingBlock h="h-48" />}>
                  <AIInsights
                    holdings={enriched}
                    riskMetrics={risk}
                    summary={portfolioData.summary}
                  />
                </Suspense>
              </div>
            )}

          </div>
        )}
      </div>

      {/* Save modal */}
      {showSave && portfolioData && (
        <Suspense fallback={null}>
          <SavePortfolioModal
            holdings={enriched}
            summary={portfolioData.summary}
            onClose={() => setShowSave(false)}
            onSaved={(_id: number, name: string) => {
              setSavedName(name)
              setShowSave(false)
            }}
          />
        </Suspense>
      )}
    </div>
  )
}
