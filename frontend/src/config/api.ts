/**
 * config/api.ts — Complete file (new).
 * Single source of truth for backend URLs.
 *
 * Local dev:  VITE_API_URL is unset → falls back to http://localhost:8000
 * Production: VITE_API_URL is set in .env.production / Vercel dashboard
 *             → e.g. https://portfolio-ai-backend.onrender.com
 *
 * WS_BASE is derived automatically — https:// becomes wss://, http:// becomes ws://
 */
export const API_BASE: string =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const WS_BASE: string =
  API_BASE.replace('https://', 'wss://').replace('http://', 'ws://')
