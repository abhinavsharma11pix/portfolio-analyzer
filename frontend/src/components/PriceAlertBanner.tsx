import { X, TrendingUp, TrendingDown } from 'lucide-react'

export interface PriceAlert {
  symbol: string
  type: string
  current: number | null
  baseline?: number | null
  previous?: number | null
  change_pct: number
  direction: 'up' | 'down'
  severity: 'high' | 'medium' | 'low'
}

interface Props {
  alerts: PriceAlert[]
  onDismiss: (index: number) => void
}

export default function PriceAlertBanner({ alerts, onDismiss }: Props) {
  if (!alerts || alerts.length === 0) return null

  return (
    <div className="fixed top-16 right-4 z-50 space-y-2 max-w-sm">
      {alerts.slice(0, 3).map((alert, i) => {
        const isUp = alert.direction === 'up'
        const borderColor = alert.severity === 'high'
          ? 'border-red-600' : 'border-yellow-600'
        const bgColor = alert.severity === 'high'
          ? 'bg-red-950/90' : 'bg-yellow-950/90'

        return (
          <div
            key={`${alert.symbol}-${i}`}
            className={`flex items-start gap-3 border ${borderColor} ${bgColor}
              backdrop-blur-sm px-4 py-3 rounded-xl shadow-xl`}
          >
            <span className={isUp ? 'text-green-400' : 'text-red-400'}>
              {isUp ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            </span>
            <div className="flex-1">
              <p className="text-white text-sm font-semibold">{alert.symbol}</p>
              <p className={`text-xs ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                {isUp ? '+' : ''}{alert.change_pct.toFixed(2)}% since session start
              </p>
            </div>
            <button
              onClick={() => onDismiss(i)}
              className="text-gray-500 hover:text-white transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}