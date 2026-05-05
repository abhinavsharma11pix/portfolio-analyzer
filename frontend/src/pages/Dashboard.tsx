import { useState, useMemo } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import UploadPortfolio from '../components/UploadPortfolio'
import SummaryCards from '../components/SummaryCards'
import SectorChart from '../components/SectorChart'
import HoldingsChart from '../components/HoldingsChart'
import RiskMetrics from '../components/RiskMetrics'
import AIInsights from '../components/AIInsights'
import PredictionChart from '../components/PredictionChart'
import MarketStatusBar from '../components/MarketStatusBar'
import PriceAlertBanner from '../components/PriceAlertBanner'
import LivePriceTicker from '../components/LivePriceTicker'
import { useWebSocket } from '../hooks/useWebSocket'
import AdvancedMetrics from '../components/AdvancedMetrics'
import BenchmarkChart from '../components/BenchmarkChart'
import ScenarioSimulator from '../components/ScenarioSimulator'

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

function fmt(val: number | null | undefined, prefix = '₹') {
  if (val === null || val === undefined) return '—'
  return `${prefix}${val.toLocaleString()}`
}

export default function Dashboard() {
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null)
  const [riskMetrics, setRiskMetrics]     = useState<any>(null)

  const baselines = useMemo(() => {
    const map: Record<string, number> = {}
    portfolioData?.holdings.forEach(h => {
      if (h.current_price) map[h.symbol] = h.current_price
    })
    return map
  }, [portfolioData])

  const symbols = useMemo(
    () => portfolioData?.holdings.map(h => h.symbol) || [],
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
  } = useWebSocket({
    symbols,
    baselines,
    enabled: !!portfolioData,
  })

  const enrichedHoldings = useMemo(() => {
    if (!portfolioData) return []
    return portfolioData.holdings.map(h => {
      const livePrice = livePrices[h.symbol] ?? h.current_price
      if (!livePrice) return h
      const invested = h.invested_value
      const current  = livePrice * h.quantity
      const pnl      = current - invested
      const pnl_pct  = (pnl / invested) * 100
      return {
        ...h,
        current_price: livePrice,
        current_value: Math.round(current * 100) / 100,
        pnl:           Math.round(pnl * 100) / 100,
        pnl_pct:       Math.round(pnl_pct * 100) / 100,
      }
    })
  }, [portfolioData, livePrices])

  const handleReset = () => {
    setPortfolioData(null)
    setRiskMetrics(null)
  }

  return (
    <div className="min-h-screen bg-gray-950">

      {/* Market Status Bar */}
      <MarketStatusBar
        connected={connected}
        lastUpdated={lastUpdated}
        nextRefresh={nextRefresh}
      />

      {/* Price Alert Banners */}
      <PriceAlertBanner alerts={alerts} onDismiss={dismissAlert} />

      <div className="max-w-7xl mx-auto px-6 py-12">

        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">
              Your Dashboard
            </h1>
            <p className="text-gray-400">
              {portfolioData
                ? `${portfolioData.total_holdings} holdings · ${
                    connected ? '🟢 Live prices' : '🔴 Reconnecting'
                  }`
                : 'Upload your portfolio to get started'
              }
            </p>
          </div>
          {portfolioData && (
            <button
              onClick={handleReset}
              className="text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-4 py-2 rounded-lg transition-colors"
            >
              ↑ Upload New File
            </button>
          )}
        </div>

        {/* Upload State */}
        {!portfolioData ? (
          <UploadPortfolio onUploadSuccess={setPortfolioData} />
        ) : (
          <div className="space-y-10">

            {/* 1. Summary Cards */}
            <section>
              <SummaryCards summary={portfolioData.summary} />
            </section>

            {/* 2. Charts */}
            <section>
              <h2 className="text-xl font-semibold text-white mb-4">
                📈 Portfolio Overview
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SectorChart holdings={enrichedHoldings} />
                <HoldingsChart holdings={enrichedHoldings} />
              </div>
            </section>

            {/* 3. Risk Analysis */}
            <section>
              <h2 className="text-xl font-semibold text-white mb-4">
                📊 Risk Analysis
              </h2>
              <RiskMetrics
                holdings={enrichedHoldings}
                onRiskLoad={setRiskMetrics}
              />
            </section>

            {/* 4. AI Insights */}
            {riskMetrics && (
              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  🧠 AI Insights
                </h2>
                <AIInsights
                  holdings={enrichedHoldings}
                  riskMetrics={riskMetrics}
                  summary={portfolioData.summary}
                />
              </section>
            )}
            {/* Advanced Analytics */}
            {riskMetrics && (
              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  🔬 Advanced Analytics
                </h2>
                <AdvancedMetrics
                  holdings={enrichedHoldings}
                  riskMetrics={riskMetrics}
                />
              </section>
            )}

            {/* Benchmark Comparison */}
            {riskMetrics && (
              <section>
                <BenchmarkChart holdings={enrichedHoldings} />
              </section>
            )}

            {/* Crash Simulator */}
            {portfolioData && (
              <section>
                <ScenarioSimulator holdings={enrichedHoldings} />
              </section>
            )}

            {/* 5. Predictions */}
            <section>
              <h2 className="text-xl font-semibold text-white mb-2">
                🔮 30-Day Predictions
              </h2>
              <p className="text-gray-500 text-sm mb-4">
                Click any stock to expand AI forecast
              </p>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 space-y-2">
                {enrichedHoldings.map((h, i) => (
                  <PredictionChart
                    key={i}
                    symbol={h.symbol}
                    currency={h.currency}
                  />
                ))}
              </div>
            </section>

            {/* 6. Holdings Table */}
            <section>
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-white">
                    Holdings — {portfolioData.total_holdings} stocks
                  </h2>
                  <div className="flex items-center gap-3">
                    {staleSymbols.length > 0 && (
                      <span className="text-xs text-yellow-500">
                        ⚠️ {staleSymbols.length} stale price(s)
                      </span>
                    )}
                    <div className={`flex items-center gap-1.5 text-xs ${
                      connected ? 'text-green-400' : 'text-gray-500'
                    }`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        connected
                          ? 'bg-green-400 animate-pulse'
                          : 'bg-gray-600'
                      }`} />
                      {connected ? 'Live' : 'Offline'}
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800">
                        {[
                          'Symbol', 'Sector', 'Currency', 'Qty',
                          'Avg Price', 'Live Price', 'Invested',
                          'Current Value', 'P&L', 'Return'
                        ].map(h => (
                          <th
                            key={h}
                            className="text-left text-gray-400 font-medium py-3 pr-4 whitespace-nowrap text-xs uppercase tracking-wide"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>

                    <tbody>
                      {enrichedHoldings.map((h, i) => {
                        const isProfit = (h.pnl ?? 0) >= 0
                        const prefix   = h.currency === 'USD' ? '$' : '₹'
                        const isStale  = staleSymbols.includes(h.symbol)

                        return (
                          <tr
                            key={i}
                            className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors group"
                          >
                            <td className="py-3 pr-4 font-semibold text-blue-400 group-hover:text-blue-300">
                              {h.symbol}
                            </td>
                            <td className="py-3 pr-4 text-gray-300">
                              {h.sector || '—'}
                            </td>
                            <td className="py-3 pr-4">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                h.currency === 'USD'
                                  ? 'bg-green-900/50 text-green-400'
                                  : 'bg-blue-900/50 text-blue-400'
                              }`}>
                                {h.currency}
                              </span>
                            </td>
                            <td className="py-3 pr-4 text-gray-300">
                              {h.quantity}
                            </td>
                            <td className="py-3 pr-4 text-gray-400">
                              {fmt(h.avg_buy_price, prefix)}
                            </td>
                            <td className="py-3 pr-4">
                              <LivePriceTicker
                                price={h.current_price}
                                currency={h.currency}
                                stale={isStale}
                              />
                            </td>
                            <td className="py-3 pr-4 text-gray-300">
                              {fmt(h.invested_value, prefix)}
                            </td>
                            <td className="py-3 pr-4 text-gray-300">
                              {h.current_value
                                ? fmt(h.current_value, prefix)
                                : '—'
                              }
                            </td>
                            <td className={`py-3 pr-4 font-medium ${
                              isProfit ? 'text-green-400' : 'text-red-400'
                            }`}>
                              <span className="flex items-center gap-1">
                                {isProfit
                                  ? <TrendingUp size={13} />
                                  : <TrendingDown size={13} />
                                }
                                {h.pnl !== null
                                  ? fmt(h.pnl, prefix)
                                  : '—'
                                }
                              </span>
                            </td>
                            <td className={`py-3 font-medium ${
                              isProfit ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {h.pnl_pct !== null ? (
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  isProfit
                                    ? 'bg-green-900/30'
                                    : 'bg-red-900/30'
                                }`}>
                                  {isProfit ? '+' : ''}{h.pnl_pct.toFixed(2)}%
                                </span>
                              ) : '—'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>

                    {/* Totals Footer */}
                    <tfoot>
                      <tr className="border-t-2 border-gray-700">
                        <td
                          colSpan={7}
                          className="py-3 text-gray-400 text-xs font-medium uppercase tracking-wide"
                        >
                          Total ({portfolioData.total_holdings} stocks)
                        </td>
                        <td className="py-3 pr-4 text-white font-semibold text-sm">
                          {portfolioData.summary?.inr?.total_current_value > 0 && (
                            <div>₹{portfolioData.summary.inr.total_current_value.toLocaleString()}</div>
                          )}
                          {portfolioData.summary?.usd?.total_current_value > 0 && (
                            <div>${portfolioData.summary.usd.total_current_value.toLocaleString()}</div>
                          )}
                        </td>
                        <td className="py-3 pr-4 font-semibold text-sm">
                          {portfolioData.summary?.inr && (
                            <div className={portfolioData.summary.inr.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                              ₹{portfolioData.summary.inr.total_pnl.toLocaleString()}
                            </div>
                          )}
                          {portfolioData.summary?.usd && (
                            <div className={portfolioData.summary.usd.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                              ${portfolioData.summary.usd.total_pnl.toLocaleString()}
                            </div>
                          )}
                        </td>
                        <td className="py-3 font-semibold text-sm">
                          {portfolioData.summary?.inr?.total_invested > 0 && (
                            <div className={portfolioData.summary.inr.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                              {portfolioData.summary.inr.total_pnl_pct >= 0 ? '+' : ''}
                              {portfolioData.summary.inr.total_pnl_pct}%
                            </div>
                          )}
                          {portfolioData.summary?.usd?.total_invested > 0 && (
                            <div className={portfolioData.summary.usd.total_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
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
            </section>

          </div>
        )}
      </div>
    </div>
  )
}