import { memo, useCallback } from 'react'
import { X, TrendingUp, TrendingDown } from 'lucide-react'

export interface PriceAlert {
  symbol: string; type: string
  current: number | null; change_pct: number
  direction: 'up' | 'down'; severity: 'high' | 'medium' | 'low'
}

interface Props { alerts: PriceAlert[]; onDismiss: (i: number) => void }

const AlertItem = memo(function AlertItem({
  alert, index, onDismiss
}: { alert: PriceAlert; index: number; onDismiss: (i: number) => void }) {
  const isUp  = alert.direction === 'up'
  const color = alert.severity === 'high' ? 'border-red-700 bg-red-950/90' : 'border-yellow-700 bg-yellow-950/90'
  const dismiss = useCallback(() => onDismiss(index), [index, onDismiss])

  return (
    <div className={`flex items-start gap-3 border ${color} backdrop-blur-sm px-4 py-3 rounded-xl shadow-lg animate-slide-right`}>
      <span className={`shrink-0 mt-0.5 ${isUp ? 'text-green-400' : 'text-red-400'}`}>
        {isUp ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-semibold">{alert.symbol}</p>
        <p className={`text-xs ${isUp ? 'text-green-400' : 'text-red-400'}`}>
          {isUp ? '+' : ''}{alert.change_pct.toFixed(2)}% since session start
        </p>
      </div>
      <button onClick={dismiss} className="text-gray-500 hover:text-white transition-colors shrink-0">
        <X size={13} />
      </button>
    </div>
  )
})

const PriceAlertBanner = memo(function PriceAlertBanner({ alerts, onDismiss }: Props) {
  if (!alerts.length) return null
  return (
    <div className="fixed top-20 right-4 z-50 space-y-2 w-72">
      {alerts.slice(0, 3).map((a, i) => (
        <AlertItem key={`${a.symbol}-${i}`} alert={a} index={i} onDismiss={onDismiss} />
      ))}
    </div>
  )
})

export default PriceAlertBanner