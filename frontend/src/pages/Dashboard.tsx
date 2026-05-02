import { useState } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import UploadPortfolio from '../components/UploadPortfolio'
import SummaryCards from '../components/SummaryCards'
import SectorChart from '../components/SectorChart'
import HoldingsChart from '../components/HoldingsChart'
import RiskMetrics from '../components/RiskMetrics'
import AIInsights from '../components/AIInsights'
import PredictionChart from '../components/PredictionChart'

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
}

interface PortfolioData {
  message: string
  total_holdings: number
  holdings: Holding[]
  summary: any
}

function fmt(val: number | null | undefined, prefix = '₹') {
  if (val === null || val === undefined) return '—'
  return `${prefix}${val.toLocaleString()}`
}

export default function Dashboard() {
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null)
  const [riskMetrics, setRiskMetrics] = useState<any>(null)

  const handleReset = () => {
    setPortfolioData(null)
    setRiskMetrics(null)
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-12">

      {/* Page Header */}
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Your Dashboard</h1>
          <p className="text-gray-400">
            {portfolioData
              ? `${portfolioData.total_holdings} holdings loaded — live prices active`
              : 'Upload your portfolio CSV or Excel to get started'}
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

          {/* ── 1. Summary Cards ──────────────────────────── */}
          <section>
            <SummaryCards summary={portfolioData.summary} />
          </section>

          {/* ── 2. Charts ─────────────────────────────────── */}
          <section>
            <h2 className="text-xl font-semibold text-white mb-4">📈 Portfolio Overview</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SectorChart holdings={portfolioData.holdings} />
              <HoldingsChart holdings={portfolioData.holdings} />
            </div>
          </section>

          {/* ── 3. Risk Analysis ──────────────────────────── */}
          <section>
            <h2 className="text-xl font-semibold text-white mb-4">📊 Risk Analysis</h2>
            <RiskMetrics
              holdings={portfolioData.holdings}
              onRiskLoad={setRiskMetrics}
            />
          </section>

          {/* ── 4. AI Insights ────────────────────────────── */}
          {riskMetrics && (
            <section>
              <h2 className="text-xl font-semibold text-white mb-4">🧠 AI Insights</h2>
              <AIInsights
                holdings={portfolioData.holdings}
                riskMetrics={riskMetrics}
                summary={portfolioData.summary}
              />
            </section>
          )}
          {/* ── 5. Price Predictions ──────────────────── */}
          <section>
            <h2 className="text-xl font-semibold text-white mb-2">
              🔮 30-Day Price Predictions
            </h2>
            <p className="text-gray-500 text-sm mb-4">
              Click any stock to generate an AI forecast · Ensemble model (Polynomial + EMA + Linear)
            </p>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 space-y-2">
              {portfolioData.holdings.map((h, i) => (
                <PredictionChart
                  key={i}
                  symbol={h.symbol}
                  currency={h.currency}
                />
              ))}
            </div>
          </section>

          {/* ── 5. Holdings Table ─────────────────────────── */}
          <section>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">
                  Holdings — {portfolioData.total_holdings} stocks
                </h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Prices delayed ~15 min</span>
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      {[
                        'Symbol', 'Sector', 'Currency', 'Qty',
                        'Avg Price', 'Current Price', 'Invested',
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
                    {portfolioData.holdings.map((h, i) => {
                      const isProfit = (h.pnl ?? 0) >= 0
                      const prefix = h.currency === 'USD' ? '$' : '₹'
                      return (
                        <tr
                          key={i}
                          className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors group"
                        >
                          {/* Symbol */}
                          <td className="py-3 pr-4 font-semibold text-blue-400 group-hover:text-blue-300">
                            {h.symbol}
                          </td>

                          {/* Sector */}
                          <td className="py-3 pr-4 text-gray-300">
                            {h.sector || '—'}
                          </td>

                          {/* Currency Badge */}
                          <td className="py-3 pr-4">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              h.currency === 'USD'
                                ? 'bg-green-900/50 text-green-400'
                                : 'bg-blue-900/50 text-blue-400'
                            }`}>
                              {h.currency}
                            </span>
                          </td>

                          {/* Qty */}
                          <td className="py-3 pr-4 text-gray-300">
                            {h.quantity}
                          </td>

                          {/* Avg Price */}
                          <td className="py-3 pr-4 text-gray-400">
                            {fmt(h.avg_buy_price, prefix)}
                          </td>

                          {/* Current Price */}
                          <td className="py-3 pr-4 text-white font-medium">
                            {h.current_price ? fmt(h.current_price, prefix) : (
                              <span className="text-gray-600">Unavailable</span>
                            )}
                          </td>

                          {/* Invested */}
                          <td className="py-3 pr-4 text-gray-300">
                            {fmt(h.invested_value, prefix)}
                          </td>

                          {/* Current Value */}
                          <td className="py-3 pr-4 text-gray-300">
                            {h.current_value ? fmt(h.current_value, prefix) : '—'}
                          </td>

                          {/* P&L */}
                          <td className={`py-3 pr-4 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                            <span className="flex items-center gap-1">
                              {isProfit
                                ? <TrendingUp size={13} />
                                : <TrendingDown size={13} />
                              }
                              {h.pnl !== null ? fmt(h.pnl, prefix) : '—'}
                            </span>
                          </td>

                          {/* Return % */}
                          <td className={`py-3 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                            {h.pnl_pct !== null ? (
                              <span className={`px-2 py-0.5 rounded text-xs ${
                                isProfit ? 'bg-green-900/30' : 'bg-red-900/30'
                              }`}>
                                {isProfit ? '+' : ''}{h.pnl_pct}%
                              </span>
                            ) : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>

                  {/* Table Footer — totals row */}
                  <tfoot>
                    <tr className="border-t-2 border-gray-700">
                      <td colSpan={6} className="py-3 pr-4 text-gray-400 text-xs font-medium">
                        TOTAL ({portfolioData.total_holdings} stocks)
                      </td>
                      <td className="py-3 pr-4 text-white font-semibold text-sm">
                        {/* INR total */}
                        {portfolioData.summary?.inr?.total_invested > 0 && (
                          <div>₹{portfolioData.summary.inr.total_invested.toLocaleString()}</div>
                        )}
                        {portfolioData.summary?.usd?.total_invested > 0 && (
                          <div>${portfolioData.summary.usd.total_invested.toLocaleString()}</div>
                        )}
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
  )
}