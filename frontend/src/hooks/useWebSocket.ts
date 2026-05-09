import {
  useEffect, useRef, useState, useCallback
} from 'react'

export interface PriceAlert {
  symbol: string
  type: 'session_move' | 'tick_move'
  current: number | null
  baseline?: number | null
  previous?: number | null
  change_pct: number
  direction: 'up' | 'down'
  severity: 'high' | 'medium' | 'low'
}

interface UseWebSocketProps {
  symbols: string[]
  baselines: Record<string, number>
  enabled: boolean
}

interface WebSocketReturn {
  prices: Record<string, number | null>
  alerts: PriceAlert[]
  connected: boolean
  staleSymbols: string[]
  lastUpdated: Date | null
  nextRefresh: number
  dismissAlert: (index: number) => void
}

const WS_URL      = 'ws://localhost:8000/ws/prices'
const PING_MS     = 30_000
const MAX_BACKOFF = 30_000

export function useWebSocket({
  symbols,
  baselines,
  enabled,
}: UseWebSocketProps): WebSocketReturn {
  const wsRef        = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>  | null>(null)
  const pingRef      = useRef<ReturnType<typeof setInterval> | null>(null)
  const attemptsRef  = useRef(0)
  const closedRef    = useRef(false)
  const symbolsRef   = useRef(symbols)
  const baselinesRef = useRef(baselines)

  useEffect(() => { symbolsRef.current  = symbols  }, [symbols])
  useEffect(() => { baselinesRef.current = baselines }, [baselines])

  const [prices,       setPrices]       = useState<Record<string, number | null>>({})
  const [alerts,       setAlerts]       = useState<PriceAlert[]>([])
  const [connected,    setConnected]    = useState(false)
  const [staleSymbols, setStaleSymbols] = useState<string[]>([])
  const [lastUpdated,  setLastUpdated]  = useState<Date | null>(null)
  const [nextRefresh,  setNextRefresh]  = useState(300)

  const clearTimers = useCallback(() => {
    if (reconnectRef.current) { clearTimeout(reconnectRef.current);  reconnectRef.current = null }
    if (pingRef.current)      { clearInterval(pingRef.current);       pingRef.current      = null }
  }, [])

  const connect = useCallback(() => {
    if (!enabled || !symbolsRef.current.length)             return
    if (wsRef.current?.readyState === WebSocket.OPEN)       return

    closedRef.current = false

    try {
      const ws      = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        attemptsRef.current = 0
        ws.send(JSON.stringify({
          type:      'subscribe',
          symbols:   symbolsRef.current,
          baselines: baselinesRef.current,
        }))
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN)
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        }, PING_MS)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'price_update') return

          const newPrices: Record<string, number | null> = data.prices || {}

          setPrices(prev => {
            const changed = Object.entries(newPrices).some(([k, v]) => prev[k] !== v)
            return changed ? { ...prev, ...newPrices } : prev
          })

          setStaleSymbols(data.stale_symbols  || [])
          setNextRefresh(data.next_refresh_seconds ?? 300)
          setLastUpdated(new Date())

          const important: PriceAlert[] = (data.alerts || []).filter(
            (a: PriceAlert) => a.severity !== 'low'
          )
          if (important.length > 0)
            setAlerts(prev => [...important, ...prev].slice(0, 10))

        } catch { /* ignore parse errors */ }
      }

      ws.onclose = () => {
        setConnected(false)
        clearTimers()
        if (!closedRef.current) {
          const delay = Math.min(1000 * 2 ** attemptsRef.current, MAX_BACKOFF)
          attemptsRef.current++
          reconnectRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = () => ws.close()

    } catch {
      const delay = Math.min(5000 * (attemptsRef.current + 1), MAX_BACKOFF)
      reconnectRef.current = setTimeout(connect, delay)
    }
  }, [enabled, clearTimers])

  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      closedRef.current = true
      clearTimers()
      wsRef.current?.close()
      wsRef.current = null
    }
    return () => {
      closedRef.current = true
      clearTimers()
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [enabled, connect, clearTimers])

  const dismissAlert = useCallback((index: number) => {
    setAlerts(prev => prev.filter((_, i) => i !== index))
  }, [])

  return { prices, alerts, connected, staleSymbols, lastUpdated, nextRefresh, dismissAlert }
}