import { useEffect, useRef, useState } from 'react'

interface Props {
  price: number | null
  currency: string
  stale?: boolean
}

export default function LivePriceTicker({ price, currency, stale }: Props) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const prevRef = useRef<number | null>(null)
  const prefix = currency === 'USD' ? '$' : '₹'

  useEffect(() => {
    if (!price || !prevRef.current) {
      prevRef.current = price
      return
    }
    if (price > prevRef.current) setFlash('up')
    else if (price < prevRef.current) setFlash('down')
    prevRef.current = price
    const t = setTimeout(() => setFlash(null), 800)
    return () => clearTimeout(t)
  }, [price])

  const flashClass =
    flash === 'up'   ? 'bg-green-500/20 transition-colors duration-500' :
    flash === 'down' ? 'bg-red-500/20 transition-colors duration-500'   :
    'transition-colors duration-500'

  return (
    <span className={`inline-flex items-center gap-1 px-1 rounded ${flashClass}`}>
      <span className="font-medium text-white">
        {price
          ? `${prefix}${price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
          : '—'
        }
      </span>
      {stale && (
        <span className="text-yellow-500 text-xs" title="Stale price">⚠</span>
      )}
    </span>
  )
}