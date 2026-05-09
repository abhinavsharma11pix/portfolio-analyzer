import { memo, useCallback } from 'react'
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

const AlertCard = memo(function AlertCard({
  alert, index, onDismiss
}: { alert: PriceAlert; index: number; onDismiss: (i: number) => void }) {
  const isUp       = alert.direction === 'up'
  const borderColor = alert.severity === 'high' ? 'border-red-600' : 'border-yellow-600'
  const bgColor     = alert.severity === 'high' ? 'bg-red-950/90' : 'bg-yellow-950/90'
  const handleDismiss = useCallback(() => onDismiss(index), [index, onDismiss])

  return (
    <div className={`flex items-start gap-3 border ${borderColor} ${bgColor}
      backdrop-blur-sm px-4 py-3 rounded-xl shadow-xl fade-in`}>
      <span className={isUp ? 'text-green-400 shrink-0' : 'text-red-400 shrink-0'}>
        {isUp ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-semibold">{alert.symbol}</p>
        <p className={`text-xs ${isUp ? 'text-green-400' : 'text-red-400'}`}>
          {isUp ? '+' : ''}{alert.change_pct.toFixed(2)}% since session start
        </p>
      </div>
      <button
        onClick={handleDismiss}
        className="text-gray-500 hover:text-white transition-colors shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  )
})

const PriceAlertBanner = memo(function PriceAlertBanner({ alerts, onDismiss }: Props) {
  if (!alerts.length) return null
  return (
    <div className="fixed top-16 right-4 z-50 space-y-2 max-w-sm w-full">
      {alerts.slice(0, 3).map((alert, i) => (
        <AlertCard key={`${alert.symbol}-${i}`} alert={alert} index={i} onDismiss={onDismiss} />
      ))}
    </div>
  )
})

export default PriceAlertBanner