import { memo, useCallback } from 'react'
import { X } from 'lucide-react'

export interface PriceAlert {
  id: string
  symbol: string
  message: string
  severity: 'low' | 'medium' | 'high'
  created_at: string
}

interface Props {
  alerts: PriceAlert[]
  onDismiss: (id: string) => void
}

const AlertItem = memo(function AlertItem({
  alert,
  onDismiss,
}: {
  alert: PriceAlert
  onDismiss: (id: string) => void
}) {
  const color =
    alert.severity === 'high'
      ? 'border-red-700 bg-red-950/90'
      : alert.severity === 'medium'
      ? 'border-yellow-700 bg-yellow-950/90'
      : 'border-blue-700 bg-blue-950/90'

  const dismiss = useCallback(
    () => onDismiss(alert.id),
    [alert.id, onDismiss]
  )

  return (
    <div
      className={`flex items-start gap-3 border ${color} backdrop-blur-sm px-4 py-3 rounded-xl shadow-lg animate-slide-right`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-semibold">
          {alert.symbol}
        </p>

        <p className="text-xs text-gray-300 mt-1">
          {alert.message}
        </p>
      </div>

      <button
        onClick={dismiss}
        className="text-gray-500 hover:text-white transition-colors shrink-0"
      >
        <X size={13} />
      </button>
    </div>
  )
})

const PriceAlertBanner = memo(function PriceAlertBanner({
  alerts,
  onDismiss,
}: Props) {
  if (!alerts.length) return null

  return (
    <div className="fixed top-20 right-4 z-50 space-y-2 w-72">
      {alerts.slice(0, 3).map((alert) => (
        <AlertItem
          key={alert.id}
          alert={alert}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  )
})

export default PriceAlertBanner