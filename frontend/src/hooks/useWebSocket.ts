/**
 * hooks/useWebSocket.ts — Complete file.
 * Uses WS_BASE (derived from API_BASE) instead of a hardcoded ws:// URL.
 * Includes ping/pong keepalive and exponential-backoff reconnect.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { WS_BASE } from '../config/api'

interface PriceAlert {
  id: string
  symbol: string
  message: string
  severity: 'low' | 'medium' | 'high'
  created_at: string
}

interface UseWebSocketOptions {
  symbols: string[]
  baselines: Record<string, number>
  enabled: boolean
}

interface UseWebSocketResult {
  prices: Record<string, number>
  alerts: PriceAlert[]
  connected: boolean
  staleSymbols: string[]
  lastUpdated: Date | null
  nextRefresh: number
  dismissAlert: (id: string) => void
}

const STALE_THRESHOLD_MS = 90_000   // 90s without an update = stale
const MAX_RECONNECT_DELAY = 15_000  // 15s ceiling on backoff

export function useWebSocket({
  symbols, baselines, enabled,
}: UseWebSocketOptions): UseWebSocketResult {
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  const [connected, setConnected] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [nextRefresh, setNextRefresh] = useState(30)
  const [staleSymbols, setStaleSymbols] = useState<string[]>([])

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempt = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastUpdateMap = useRef<Record<string, number>>({})

  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }, [])

  useEffect(() => {
    if (!enabled || symbols.length === 0) {
      return
    }

    let isUnmounted = false

    const connect = () => {
      if (isUnmounted) return

      const ws = new WebSocket(`${WS_BASE}/ws/prices`)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        reconnectAttempt.current = 0
        ws.send(JSON.stringify({
          type: 'subscribe',
          symbols,
          baseline_prices: baselines,
        }))
        setNextRefresh(30)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }))
            return
          }

          if (data.type === 'prices' && data.prices) {
            setPrices((prev) => ({ ...prev, ...data.prices }))
            const now = Date.now()
            Object.keys(data.prices).forEach((sym) => {
              lastUpdateMap.current[sym] = now
            })
            setLastUpdated(new Date())
            setNextRefresh(30)
          }

          if (data.type === 'alert' && data.alert) {
            setAlerts((prev) => [
              { id: `${Date.now()}-${Math.random()}`, ...data.alert },
              ...prev,
            ].slice(0, 20))
          }
        } catch {
          // Ignore malformed message
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (isUnmounted) return
        const delay = Math.min(
          1000 * Math.pow(1.5, reconnectAttempt.current),
          MAX_RECONNECT_DELAY
        )
        reconnectAttempt.current += 1
        reconnectTimer.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    countdownTimer.current = setInterval(() => {
      setNextRefresh((prev) => (prev > 0 ? prev - 1 : 30))

      const now = Date.now()
      const stale = symbols.filter((sym) => {
        const last = lastUpdateMap.current[sym]
        return !last || now - last > STALE_THRESHOLD_MS
      })
      setStaleSymbols(stale)
    }, 1000)

    return () => {
      isUnmounted = true
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (countdownTimer.current) clearInterval(countdownTimer.current)
      wsRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, symbols.join(','), JSON.stringify(baselines)])

  return { prices, alerts, connected, staleSymbols, lastUpdated, nextRefresh, dismissAlert }
}

export default useWebSocket
