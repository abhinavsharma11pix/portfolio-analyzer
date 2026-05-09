import { useEffect, useState, memo } from 'react'
import { Wifi, WifiOff } from 'lucide-react'

interface MarketStatus {
  nse_open: boolean
  us_open: boolean
  is_weekend: boolean
  refresh_interval_seconds: number
  ist_time: string
  et_time: string
}

interface Props {
  connected?: boolean
  lastUpdated?: Date | null
  nextRefresh?: number
}

const MarketStatusBar = memo(function MarketStatusBar({
  connected = false,
  lastUpdated = null,
  nextRefresh = 300,
}: Props) {
  const [status, setStatus] = useState<MarketStatus | null>(null)

  useEffect(() => {
    let mounted = true
    const fetchStatus = async () => {
      try {
        const res  = await fetch('http://localhost:8000/api/market/status')
        const data = await res.json()
        if (mounted) setStatus(data)
      } catch { /* silent */ }
    }
    fetchStatus()
    const t = setInterval(fetchStatus, 60_000)
    return () => { mounted = false; clearInterval(t) }
  }, [])

  const refreshLabel = nextRefresh >= 60
    ? `${Math.round(nextRefresh / 60)}m`
    : `${nextRefresh}s`

  return (
    <div className="flex items-center gap-3 px-6 py-1.5 bg-gray-950 border-b border-gray-800/40 text-xs overflow-x-auto whitespace-nowrap">

      <div className="flex items-center gap-1.5 shrink-0">
        {connected
          ? <Wifi size={11} className="text-green-400" />
          : <WifiOff size={11} className="text-red-400" />
        }
        <span className={connected ? 'text-green-400' : 'text-red-400'}>
          {connected ? 'Live' : 'Offline'}
        </span>
      </div>

      <span className="text-gray-700">|</span>

      <div className="flex items-center gap-1.5 shrink-0">
        <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
          status?.nse_open ? 'bg-green-400 animate-pulse' : 'bg-gray-600'
        }`} />
        <span className={status?.nse_open ? 'text-green-400' : 'text-gray-500'}>
          NSE {status?.nse_open ? 'Open' : 'Closed'}
        </span>
        {status?.ist_time && (
          <span className="text-gray-600">{status.ist_time} IST</span>
        )}
      </div>

      <span className="text-gray-700">|</span>

      <div className="flex items-center gap-1.5 shrink-0">
        <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
          status?.us_open ? 'bg-green-400 animate-pulse' : 'bg-gray-600'
        }`} />
        <span className={status?.us_open ? 'text-green-400' : 'text-gray-500'}>
          US {status?.us_open ? 'Open' : 'Closed'}
        </span>
        {status?.et_time && (
          <span className="text-gray-600">{status.et_time} ET</span>
        )}
      </div>

      <span className="text-gray-700">|</span>

      <span className="text-gray-500 shrink-0">
        Refresh: {refreshLabel}
      </span>

      {lastUpdated && (
        <>
          <span className="text-gray-700">|</span>
          <span className="text-gray-600 shrink-0">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        </>
      )}

      {status?.is_weekend && (
        <>
          <span className="text-gray-700">|</span>
          <span className="text-yellow-600 shrink-0">
            Weekend — last close prices
          </span>
        </>
      )}
    </div>
  )
})

export default MarketStatusBar