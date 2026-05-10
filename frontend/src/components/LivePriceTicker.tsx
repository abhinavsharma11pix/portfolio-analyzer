import { useEffect, useRef, useState, memo } from 'react'

interface Props { price: number | null; currency: string; stale?: boolean }

const LivePriceTicker = memo(function LivePriceTicker({ price, currency, stale }: Props) {
  const [flashClass, setFlashClass] = useState('')
  const prevRef   = useRef<number | null>(null)
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prefix    = currency === 'USD' ? '$' : '₹'

  useEffect(() => {
    if (price == null || prevRef.current == null) { prevRef.current = price; return }
    if (price === prevRef.current) return

    const cls = price > prevRef.current ? 'flash-green' : 'flash-red'
    setFlashClass(cls)
    prevRef.current = price
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setFlashClass(''), 650)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [price])

  return (
    <span className={`inline-flex items-center gap-1 px-1 rounded ${flashClass}`}>
      <span className="font-medium text-white tabular-nums">
        {price != null
          ? `${prefix}${price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
          : <span className="text-gray-600 text-xs">—</span>
        }
      </span>
      {stale && <span className="text-yellow-600 text-xs" title="Delayed price">⚠</span>}
    </span>
  )
})

export default LivePriceTicker