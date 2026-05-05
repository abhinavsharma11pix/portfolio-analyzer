import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

interface MarketStatus {
  nse_open: boolean
  us_open: boolean
  refresh_interval_seconds: number
}

interface PriceUpdate {
  [symbol: string]: number | null
}

export function usePriceRefresh(symbols: string[]) {
  const [prices, setPrices]           = useState<PriceUpdate>({})
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchMarketStatus = useCallback(async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/market/status')
      setMarketStatus(res.data)
    } catch { /* silent */ }
  }, [])

  const refreshPrices = useCallback(async () => {
    if (!symbols.length) return
    setIsRefreshing(true)
    try {
      const res = await axios.get(
        `http://localhost:8000/api/prices/refresh?symbols=${symbols.join(',')}`
      )
      if (res.data.prices) {
        setPrices(res.data.prices)
        setLastUpdated(new Date())
      }
    } catch { /* silent */ }
    finally { setIsRefreshing(false) }
  }, [symbols])

  // Poll based on market hours
  useEffect(() => {
    fetchMarketStatus()
    const statusInterval = setInterval(fetchMarketStatus, 60000)
    return () => clearInterval(statusInterval)
  }, [fetchMarketStatus])

  useEffect(() => {
    if (!symbols.length) return
    const interval = marketStatus?.refresh_interval_seconds || 300
    const timer = setInterval(refreshPrices, interval * 1000)
    return () => clearInterval(timer)
  }, [symbols, marketStatus, refreshPrices])

  return { prices, marketStatus, lastUpdated, isRefreshing, refreshPrices }
}