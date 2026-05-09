import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart2,
} from 'lucide-react'
import Tooltip from './ui/Tooltip'

interface CurrencySummary {
  total_invested: number
  total_current_value: number
  total_pnl: number
  total_pnl_pct: number
}

interface Summary {
  inr: CurrencySummary
  usd: CurrencySummary
}

interface Props {
  summary: Summary
}

function formatINR(val: number) {
  if (Math.abs(val) >= 100000) {
    return `₹${(val / 100000).toFixed(2)}L`
  }

  if (Math.abs(val) >= 1000) {
    return `₹${(val / 1000).toFixed(2)}K`
  }

  return `₹${val.toFixed(2)}`
}

function formatUSD(val: number) {
  if (Math.abs(val) >= 1000) {
    return `$${(val / 1000).toFixed(2)}K`
  }

  return `$${val.toFixed(2)}`
}

function CurrencyBlock({
  label,
  data,
  formatFn,
  flag,
}: {
  label: string
  data: CurrencySummary
  formatFn: (v: number) => string
  flag: string
}) {
  const isProfit = data.total_pnl >= 0

  const pnlColor = isProfit
    ? 'text-green-400'
    : 'text-red-400'

  const Icon = isProfit
    ? TrendingUp
    : TrendingDown

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">

      {/* Currency Header */}
      <p className="text-gray-400 text-sm font-medium mb-4">
        <Tooltip
          content={
            label === 'Indian'
              ? 'All values shown in Indian Rupees for NSE/BSE stocks'
              : 'All values shown in US Dollars for NASDAQ/NYSE stocks'
          }
          showIcon
        >
          <span>
            {flag} {label} Portfolio
          </span>
        </Tooltip>
      </p>

      {/* Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">

        {/* Invested */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <DollarSign
              size={14}
              className="text-blue-400"
            />

            <span className="text-gray-500 text-xs">
              Invested
            </span>
          </div>

          <p className="text-white font-bold text-lg">
            {formatFn(data.total_invested)}
          </p>
        </div>

        {/* Current */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <BarChart2
              size={14}
              className="text-purple-400"
            />

            <span className="text-gray-500 text-xs">
              Current
            </span>
          </div>

          <p className="text-white font-bold text-lg">
            {formatFn(data.total_current_value)}
          </p>
        </div>

        {/* PnL */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Icon
              size={14}
              className={pnlColor}
            />

            <span className="text-gray-500 text-xs">
              P&L
            </span>
          </div>

          <p className={`font-bold text-lg ${pnlColor}`}>
            {formatFn(data.total_pnl)}
          </p>
        </div>

        {/* Return */}
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Icon
              size={14}
              className={pnlColor}
            />

            <span className="text-gray-500 text-xs">
              Return
            </span>
          </div>

          <p className={`font-bold text-lg ${pnlColor}`}>
            {isProfit ? '+' : ''}
            {data.total_pnl_pct.toFixed(2)}%
          </p>
        </div>

      </div>
    </div>
  )
}

export default function SummaryCards({
  summary,
}: Props) {
  const hasINR =
    (summary?.inr?.total_invested ?? 0) > 0

  const hasUSD =
    (summary?.usd?.total_invested ?? 0) > 0

  return (
    <div className="space-y-4 mb-8">

      {hasINR && (
        <CurrencyBlock
          label="Indian"
          data={summary.inr}
          formatFn={formatINR}
          flag="🇮🇳"
        />
      )}

      {hasUSD && (
        <CurrencyBlock
          label="US"
          data={summary.usd}
          formatFn={formatUSD}
          flag="🇺🇸"
        />
      )}

    </div>
  )
}