import { useEffect, useRef, useState, memo } from 'react'

interface Props {
  price: number | null
  currency: string
  stale?: boolean
}

const LivePriceTicker = memo(function LivePriceTicker({ price, currency, stale }: Props) {
  const [flash, setFlash]   = useState<'up' | 'down' | null>(null)
  const prevRef             = useRef<number | null>(null)
  const timerRef            = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prefix              = currency === 'USD' ? '$' : '₹'

  useEffect(() => {
    if (price === null) return
    if (prevRef.current !== null && prevRef.current !== price) {
      const dir = price > prevRef.current ? 'up' : 'down'
      setFlash(dir)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setFlash(null), 700)
    }
    prevRef.current = price
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [price])

  const flashClass =
    flash === 'up'   ? 'bg-green-500/20' :
    flash === 'down' ? 'bg-red-500/20'   : ''

  return (
    <span className={`inline-flex items-center gap-1 px-1 rounded transition-colors duration-500 ${flashClass}`}>
      <span className="font-medium text-white tabular-nums">
        {price != null
          ? `${prefix}${price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
          : <span className="text-gray-600">Unavailable</span>
        }
      </span>
      {stale && (
        <span className="text-yellow-500 text-xs" title="Price may be delayed">⚠</span>
      )}
    </span>
  )
})

export default LivePriceTicker