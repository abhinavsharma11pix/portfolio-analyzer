import {
  useState, useMemo, useCallback, memo
} from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

import Navbar            from '../components/Navbar'
import UploadPortfolio   from '../components/UploadPortfolio'
import SummaryCards      from '../components/SummaryCards'
import SectorChart       from '../components/SectorChart'
import HoldingsChart     from '../components/HoldingsChart'
import RiskMetrics       from '../components/RiskMetrics'
import AIInsights        from '../components/AIInsights'
import PredictionChart   from '../components/PredictionChart'
import PriceAlertBanner  from '../components/PriceAlertBanner'
import LivePriceTicker   from '../components/LivePriceTicker'
import AdvancedMetrics   from '../components/AdvancedMetrics'
import BenchmarkChart    from '../components/BenchmarkChart'
import ScenarioSimulator from '../components/ScenarioSimulator'
import TodayDashboard    from '../components/TodayDashboard'
import Section           from '../components/ui/Section'
import { useWebSocket }  from '../hooks/useWebSocket'

/* ── Types ── */
interface Holding {
  symbol: string
  quantity: number
  avg_buy_price: number
  sector?: string
  current_price: number | null
  currency: string
  invested_value: number
  current_value: number | null
  pnl: number | null
  pnl_pct: number | null
  confidence?: number
}

interface PortfolioData {
  message: string
  total_holdings: number
  holdings: Holding[]
  summary: any
  source?: string
  validation?: any
}

/* ── Helper ── */
function fmt(val: number | null | undefined, prefix = '₹') {
  if (val == null) return '—'
  return `${prefix}${val.toLocaleString()}`
}

/* ── Holdings Row — memoized to prevent table rerenders ── */
const HoldingsRow = memo(function HoldingsRow({
  h, isStale,
}: { h: Holding; isStale: boolean }) {
  const isProfit = (h.pnl ?? 0) >= 0
  const prefix   = h.currency === 'USD' ? '$' : '₹'

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
      <td className="py-3 pr-4 font-semibold text-blue-400">{h.symbol}</td>
      <td className="py-3 pr-4 text-gray-300">{h.sector || '—'}</td>
      <td className="py-3 pr-4">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          h.currency === 'USD'
            ? 'bg-green-900/50 text-green-400'
            : 'bg-blue-900/50 text-blue-400'
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
      <td className={`py-3 pr-4 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        <span className="flex items-center gap-1 tabular-nums">
          {isProfit ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {h.pnl !== null ? fmt(h.pnl, prefix) : '—'}
        </span>
      </td>
      <td className={`py-3 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        {h.pnl_pct !== null ? (
          <span className={`px-2 py-0.5 rounded text-xs tabular-nums ${
            isProfit ? 'bg-green-900/30' : 'bg-red-900/30'
          }`}>
            {isProfit ? '+' : ''}{h.pnl_pct.toFixed(2)}%
          </span>
        ) : '—'}
      </td>
    </tr>
  )
})

/* ── Dashboard ── */
export default function Dashboard() {
  const [portfolioData,   setPortfolioData]   = useState<PortfolioData | null>(null)
  const [riskMetrics,     setRiskMetrics]     = useState<any>(null)
  const [advancedMetrics, setAdvancedMetrics] = useState<any>(null)

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
    prices: livePrices,
    alerts,
    connected,
    staleSymbols,
    lastUpdated,
    nextRefresh,
    dismissAlert,
  } = useWebSocket({ symbols, baselines, enabled: !!portfolioData })

  const enrichedHoldings = useMemo(() => {
    if (!portfolioData) return []
    return portfolioData.holdings.map(h => {
      const live = livePrices[h.symbol]
      if (live == null) return h
      const invested = h.invested_value
      const current  = live * h.quantity
      const pnl      = current - invested
      const pnl_pct  = invested > 0 ? (pnl / invested) * 100 : 0
      return {
        ...h,
        current_price: live,
        current_value: Math.round(current * 100) / 100,
        pnl:           Math.round(pnl     * 100) / 100,
        pnl_pct:       Math.round(pnl_pct * 100) / 100,
      }
    })
  }, [portfolioData, livePrices])

  const handleUploadSuccess = useCallback((data: PortfolioData) => {
    setPortfolioData(data)
    setRiskMetrics(null)
    setAdvancedMetrics(null)
  }, [])

  const handleReset        = useCallback(() => {
    setPortfolioData(null); setRiskMetrics(null); setAdvancedMetrics(null)
  }, [])
  const handleRiskLoad     = useCallback((d: any) => setRiskMetrics(d),     [])
  const handleAdvancedLoad = useCallback((d: any) => setAdvancedMetrics(d), [])

  return (
    <div className="min-h-screen bg-gray-950">

      <Navbar connected={connected} lastUpdated={lastUpdated} nextRefresh={nextRefresh} />
      <PriceAlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-10">

        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Your Dashboard</h1>
            <p className="text-gray-400 text-sm">
              {portfolioData
                ? `${portfolioData.total_holdings} holdings · ${connected ? '🟢 Live' : '🔴 Reconnecting'}`
                : 'Upload your portfolio to get started'
              }
            </p>
          </div>
          {portfolioData && (
            <button
              onClick={handleReset}
              className="text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-4 py-2 rounded-lg transition-colors shrink-0"
            >
              ↑ New File
            </button>
          )}
        </div>

        {/* Upload */}
        {!portfolioData ? (
          <UploadPortfolio onUploadSuccess={handleUploadSuccess} />
        ) : (
          <div className="space-y-10">

            <Section delay={0}>
              <SummaryCards summary={portfolioData.summary} />
            </Section>

            {riskMetrics && (
              <Section delay={50}>
                <h2 className="text-xl font-semibold text-white mb-4">🎯 What To Do Today</h2>
                <TodayDashboard
                  holdings={enrichedHoldings}
                  riskMetrics={riskMetrics}
                  advancedMetrics={advancedMetrics}
                  summary={portfolioData.summary}
                />
              </Section>
            )}

            <Section delay={100}>
              <h2 className="text-xl font-semibold text-white mb-4">📈 Portfolio Overview</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectorChart holdings={enrichedHoldings} />
                <HoldingsChart holdings={enrichedHoldings} />
              </div>
            </Section>

            <Section delay={150}>
              <h2 className="text-xl font-semibold text-white mb-4">📊 Risk Analysis</h2>
              <RiskMetrics holdings={enrichedHoldings} onRiskLoad={handleRiskLoad} />
            </Section>

            {riskMetrics && (
              <Section delay={0}>
                <h2 className="text-xl font-semibold text-white mb-4">🔬 Advanced Analytics</h2>
                <AdvancedMetrics
                  holdings={enrichedHoldings}
                  riskMetrics={riskMetrics}
                  onLoad={handleAdvancedLoad}
                />
              </Section>
            )}

            {riskMetrics && (
              <Section delay={0}>
                <BenchmarkChart holdings={enrichedHoldings} />
              </Section>
            )}

            {riskMetrics && (
              <Section delay={0}>
                <h2 className="text-xl font-semibold text-white mb-4">🧠 AI Insights</h2>
                <AIInsights
                  holdings={enrichedHoldings}
                  riskMetrics={riskMetrics}
                  summary={portfolioData.summary}
                />
              </Section>
            )}

            <Section delay={0}>
              <ScenarioSimulator holdings={enrichedHoldings} />
            </Section>

            <Section delay={0}>
              <h2 className="text-xl font-semibold text-white mb-2">🔮 30-Day Predictions</h2>
              <p className="text-gray-500 text-sm mb-4">
                Click any stock · ARIMA + RF + LightGBM ensemble
              </p>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 space-y-2">
                {enrichedHoldings.map(h => (
                  <PredictionChart key={h.symbol} symbol={h.symbol} currency={h.currency} />
                ))}
              </div>
            </Section>

            {/* Holdings Table */}
            <Section delay={0}>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-white">
                    Holdings — {portfolioData.total_holdings} stocks
                  </h2>
                  <div className="flex items-center gap-3">
                    {staleSymbols.length > 0 && (
                      <span className="text-xs text-yellow-500">⚠️ {staleSymbols.length} stale</span>
                    )}
                    <div className={`flex items-center gap-1.5 text-xs ${connected ? 'text-green-400' : 'text-gray-500'}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                      {connected ? 'Live' : 'Offline'}
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800">
                        {[
                          'Symbol','Sector','Currency','Qty',
                          'Avg Price','Live Price','Invested',
                          'Current Value','P&L','Return'
                        ].map(col => (
                          <th key={col} className="text-left text-gray-400 font-medium py-3 pr-4 whitespace-nowrap text-xs uppercase tracking-wide">
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
                      <tr className="border-t-2 border-gray-700">
                        <td colSpan={7} className="py-3 text-gray-400 text-xs font-medium uppercase tracking-wide">
                          Total ({portfolioData.total_holdings} stocks)
                        </td>
                        <td className="py-3 pr-4 font-semibold text-sm">
                          {portfolioData.summary?.inr?.total_current_value > 0 && (
                            <div className="text-white tabular-nums">
                              ₹{portfolioData.summary.inr.total_current_value.toLocaleString()}
                            </div>
                          )}
                          {portfolioData.summary?.usd?.total_current_value > 0 && (
                            <div className="text-white tabular-nums">
                              ${portfolioData.summary.usd.total_current_value.toLocaleString()}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4 font-semibold text-sm">
                          {portfolioData.summary?.inr && (
                            <div className={`tabular-nums ${portfolioData.summary.inr.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ₹{portfolioData.summary.inr.total_pnl.toLocaleString()}
                            </div>
                          )}
                          {portfolioData.summary?.usd && (
                            <div className={`tabular-nums ${portfolioData.summary.usd.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              ${portfolioData.summary.usd.total_pnl.toLocaleString()}
                            </div>
                          )}
                        </td>
                        <td className="py-3 font-semibold text-sm">
                          {portfolioData.summary?.inr?.total_invested > 0 && (
                            <div className={`tabular-nums ${portfolioData.summary.inr.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {portfolioData.summary.inr.total_pnl_pct >= 0 ? '+' : ''}
                              {portfolioData.summary.inr.total_pnl_pct}%
                            </div>
                          )}
                          {portfolioData.summary?.usd?.total_invested > 0 && (
                            <div className={`tabular-nums ${portfolioData.summary.usd.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {portfolioData.summary.usd.total_pnl_pct >= 0 ? '+' : ''}
                              {portfolioData.summary.usd.total_pnl_pct}%
                            </div>
                          )}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </Section>

          </div>
        )}
      </div>
    </div>
  )
}