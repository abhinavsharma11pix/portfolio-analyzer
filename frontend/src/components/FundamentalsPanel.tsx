import { useState, memo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fundamentalsService } from '../services/auth'
import { BarChart3, ChevronDown, ChevronUp } from 'lucide-react'

interface Props { symbol: string; currency: string }

const GRADE_COLOR: Record<string, string> = {
  A: 'text-green-400 bg-green-950/40 border-green-700',
  B: 'text-blue-400 bg-blue-950/40 border-blue-700',
  C: 'text-yellow-400 bg-yellow-950/40 border-yellow-700',
  D: 'text-orange-400 bg-orange-950/40 border-orange-700',
  F: 'text-red-400 bg-red-950/40 border-red-700',
}

const ANALYST_COLOR: Record<string, string> = {
  'STRONG_BUY': 'text-green-400', 'BUY': 'text-green-400',
  'HOLD': 'text-yellow-400', 'SELL': 'text-red-400', 'STRONG_SELL': 'text-red-500',
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  if (score == null) return null
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-500 text-xs w-20 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all ${
            score >= 70 ? 'bg-green-500' : score >= 45 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs tabular-nums w-8 text-right text-gray-400">{score}</span>
    </div>
  )
}

function MetricRow({
  label, value, color = 'text-gray-300',
}: { label: string; value: string | null; color?: string }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/[0.03]">
      <span className="text-gray-500 text-xs">{label}</span>
      <span className={`text-xs font-semibold tabular-nums ${color}`}>{value}</span>
    </div>
  )
}

const FundamentalsPanel = memo(function FundamentalsPanel({ symbol, currency }: Props) {
  const [open, setOpen] = useState(false)
  const prefix = currency === 'USD' ? '$' : '₹'

  const { data, isLoading, isError } = useQuery({
    queryKey:  ['fundamentals', symbol],
    queryFn:   () => fundamentalsService.summary(symbol).then(r => r.data),
    enabled:   open,
    staleTime: 86400 * 1000,
  })

  return (
    <div className="border border-gray-800/60 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <BarChart3 size={13} className="text-blue-400" />
          <span className="text-gray-400 text-sm font-medium">Fundamentals</span>
          {data?.grade && (
            <span className={`text-xs px-2 py-0.5 rounded border font-bold ${
              GRADE_COLOR[data.grade] ?? 'text-gray-400 bg-gray-800 border-gray-700'
            }`}>
              {data.grade}
            </span>
          )}
        </div>
        {open
          ? <ChevronUp size={13} className="text-gray-500" />
          : <ChevronDown size={13} className="text-gray-500" />}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-800/60">
          {isLoading && (
            <div className="flex items-center gap-2 py-3 text-gray-500 text-sm">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              Loading fundamentals...
            </div>
          )}

          {isError && (
            <p className="text-gray-600 text-xs py-2">
              Fundamental data unavailable for {symbol}
            </p>
          )}

          {data && !isLoading && (
            <div className="space-y-3 mt-2">
              <div className="space-y-1.5">
                <ScoreBar label="Valuation" score={data.valuation_score} />
                <ScoreBar label="Quality"   score={data.quality_score} />
                <ScoreBar label="Growth"    score={data.growth_score} />
              </div>

              <div className="mt-3">
                <MetricRow label="P/E Ratio"      value={data.pe_ratio     ? data.pe_ratio.toFixed(1)                     : null} />
                <MetricRow label="P/B Ratio"      value={data.pb_ratio     ? data.pb_ratio.toFixed(2)                     : null} />
                <MetricRow label="ROE"            value={data.return_on_equity ? `${(data.return_on_equity*100).toFixed(1)}%` : null}
                  color={data.return_on_equity > 0.15 ? 'text-green-400' : 'text-gray-300'} />
                <MetricRow label="Profit Margin"  value={data.profit_margin ? `${(data.profit_margin*100).toFixed(1)}%`   : null}
                  color={data.profit_margin > 0.10 ? 'text-green-400' : 'text-yellow-400'} />
                <MetricRow label="Revenue Growth" value={data.revenue_growth ? `${(data.revenue_growth*100).toFixed(1)}%` : null}
                  color={(data.revenue_growth ?? 0) > 0 ? 'text-green-400' : 'text-red-400'} />
                <MetricRow label="Dividend Yield" value={data.dividend_yield ? `${(data.dividend_yield*100).toFixed(2)}%` : null}
                  color="text-yellow-400" />
                <MetricRow label="52W High"       value={data['52w_high'] ? `${prefix}${data['52w_high'].toFixed(0)}` : null} />
                <MetricRow label="52W Low"        value={data['52w_low']  ? `${prefix}${data['52w_low'].toFixed(0)}`  : null} />
                {data.analyst_rating && (
                  <MetricRow label="Analyst Rating" value={data.analyst_rating}
                    color={ANALYST_COLOR[data.analyst_rating] ?? 'text-gray-300'} />
                )}
                {data.target_price && (
                  <MetricRow label="Price Target" value={`${prefix}${data.target_price.toFixed(0)}`}
                    color="text-blue-400" />
                )}
              </div>

              {data.fundamental_summary && (
                <p className="text-gray-600 text-xs mt-2 leading-relaxed">
                  {data.fundamental_summary}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
})

export default FundamentalsPanel