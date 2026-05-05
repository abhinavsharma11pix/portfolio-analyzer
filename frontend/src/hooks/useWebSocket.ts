import { useEffect, useRef, useState, useCallback } from 'react'

/* -------------------- TYPES -------------------- */

interface PriceAlert {
  symbol: string
  type: 'session_move' | 'tick_move'
  current: number | null
  baseline?: number | null
  previous?: number | null
  change_pct: number
  direction: 'up' | 'down'
  severity: 'high' | 'medium' | 'low'
}

interface PriceUpdate {
  type: string
  prices: Record<string, number | null>
  alerts?: PriceAlert[]
  market: { nse_open: boolean; us_open: boolean }
  sources?: Record<string, string>
  stale_symbols?: string[]
  timestamp: string
  next_refresh_seconds?: number
}

interface UseWebSocketProps {
  symbols: string[]
  baselines: Record<string, number>
  enabled: boolean
}

/* -------------------- HELPERS -------------------- */

const normalizePrices = (prices: Record<string, number | null>) =>
  Object.fromEntries(
    Object.entries(prices).map(([k, v]) => [k, v ?? null])
  )

const normalizeAlerts = (alerts: PriceAlert[] = []) =>
  alerts
    .filter(a => a.severity !== 'low')
    .map(a => ({
      ...a,
      current:  a.current  ?? null,
      baseline: a.baseline ?? null,
      previous: a.previous ?? null,
    }))

/* -------------------- HOOK -------------------- */

export function useWebSocket({
  symbols,
  baselines,
  enabled,
}: UseWebSocketProps) {
  const ws             = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>  | null>(null)
  const pingTimer      = useRef<ReturnType<typeof setInterval> | null>(null)

  const reconnectAttempts = useRef(0)
  const isManuallyClosed  = useRef(false)

  const [prices,       setPrices]       = useState<Record<string, number | null>>({})
  const [alerts,       setAlerts]       = useState<PriceAlert[]>([])
  const [connected,    setConnected]    = useState(false)
  const [marketOpen,   setMarketOpen]   = useState(false)
  const [staleSymbols, setStaleSymbols] = useState<string[]>([])
  const [lastUpdated,  setLastUpdated]  = useState<Date | null>(null)
  const [nextRefresh,  setNextRefresh]  = useState<number>(300)

  /* -------------------- CONNECT -------------------- */

  const connect = useCallback(() => {
    if (!enabled || symbols.length === 0) return

    isManuallyClosed.current = false

    try {
      ws.current = new WebSocket('ws://localhost:8000/ws/prices')

      ws.current.onopen = () => {
        setConnected(true)
        reconnectAttempts.current = 0

        ws.current?.send(JSON.stringify({
          type:      'subscribe',
          symbols,
          baselines,
        }))

        // Keep-alive ping every 30s
        pingTimer.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
              type:      'ping',
              timestamp: Date.now(),
            }))
          }
        }, 30000)
      }

      ws.current.onmessage = (event) => {
        try {
          const data: PriceUpdate = JSON.parse(event.data)
          if (data.type !== 'price_update') return

          setPrices(prev => ({
            ...prev,
            ...normalizePrices(data.prices || {})
          }))

          setMarketOpen(!!(data.market?.nse_open || data.market?.us_open))
          setStaleSymbols(data.stale_symbols || [])
          setLastUpdated(new Date(data.timestamp || Date.now()))
          setNextRefresh(data.next_refresh_seconds ?? 300)

          if (data.alerts?.length) {
            const important = normalizeAlerts(data.alerts)
            if (important.length) {
              setAlerts(prev => [...important, ...prev.slice(0, 9)])
            }
          }
        } catch {
          // Ignore malformed WebSocket messages
        }
      }

      ws.current.onclose = () => {
        setConnected(false)
        if (pingTimer.current) clearInterval(pingTimer.current)

        if (!isManuallyClosed.current) {
          // Exponential backoff: 5s, 10s, 15s... max 30s
          const delay = Math.min(
            5000 * (reconnectAttempts.current + 1),
            30000
          )
          reconnectAttempts.current += 1
          reconnectTimer.current = setTimeout(connect, delay)
        }
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }

    } catch {
      reconnectTimer.current = setTimeout(connect, 5000)
    }
  }, [enabled, symbols, baselines])

  /* -------------------- LIFECYCLE -------------------- */

  useEffect(() => {
    connect()
    return () => {
      isManuallyClosed.current = true
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (pingTimer.current)      clearInterval(pingTimer.current)
      ws.current?.close()
    }
  }, [connect])

  /* -------------------- ACTIONS -------------------- */

  const dismissAlert = useCallback((index: number) => {
    setAlerts(prev => prev.filter((_, i) => i !== index))
  }, [])

  return {
    prices,
    alerts,
    connected,
    marketOpen,
    staleSymbols,
    lastUpdated,
    nextRefresh,
    dismissAlert,
  }
}