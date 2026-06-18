import React, {
  useState,
  useRef,
  useCallback,
  memo,
} from 'react'

import {
  Upload,
  CheckCircle,
  X,
  Download,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react'

import axios from 'axios'
import { API_BASE } from '../config/api'

interface Holding {
  symbol: string
  quantity: number
  avg_buy_price: number
  sector?: string
  current_price: number | null
  currency: string
  invested_value: number
  current_value: number | null
  pnl: number | null
  pnl_pct: number | null
}

interface ValidationResult {
  valid_count: number
  error_count: number
  warning_count: number
  low_confidence_count: number
  errors: string[]
  warnings: string[]
  low_confidence: {
    symbol: string
    raw: string
    confidence: number
    suggestion: string
  }[]
}

interface UploadResult {
  message: string
  total_holdings: number
  holdings: Holding[]
  summary: any
  source?: string
  validation?: ValidationResult
}

interface Props {
  onUploadSuccess: (data: UploadResult) => void
}

const SOURCE_LABELS: Record<string, string> = {
  csv: '📄 CSV',
  excel: '📊 Excel',
  zerodha: '🟠 Zerodha',
  groww: '🟢 Groww',
  pdf: '📑 PDF',
}

const MAX_FILE_MB = 5

const ALLOWED_EXTS = [
  '.csv',
  '.xlsx',
  '.xls',
  '.pdf',
]

// Realistic prices from ~June 2025 — shows modest gains/losses,
// a much better demo experience for recruiters than fictional prices.
const DEMO_CSV = `Symbol,Qty,Buy_Price,Sector
RELIANCE.NS,10,1280,Energy
TCS.NS,5,2100,Technology
INFY.NS,8,1500,Technology
HDFCBANK.NS,15,1520,Banking
WIPRO.NS,20,240,Technology
AAPL,3,190,Technology
GOOGL,2,165,Technology`

const UploadPortfolio = memo(function UploadPortfolio({
  onUploadSuccess,
}: Props) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)

  const [validation, setValidation] =
    useState<ValidationResult | null>(null)

  const [showValidation, setShowValidation] =
    useState(false)

  const [progress, setProgress] = useState('')

  const fileInputRef =
    useRef<HTMLInputElement>(null)

  const validateFile = useCallback(
    (file: File): string | null => {
      const ext =
        '.' +
        (file.name.split('.').pop() ?? '').toLowerCase()

      if (!ALLOWED_EXTS.includes(ext)) {
        return 'Only CSV, Excel or PDF files allowed'
      }

      if (
        file.size >
        MAX_FILE_MB * 1024 * 1024
      ) {
        return `File too large. Max ${MAX_FILE_MB}MB`
      }

      return null
    },
    []
  )

  const handleFile = useCallback(
    async (file: File) => {
      const err = validateFile(file)

      if (err) {
        setError(err)
        return
      }

      setError(null)
      setSuccess(false)
      setValidation(null)
      setShowValidation(false)
      setFileName(file.name)
      setIsLoading(true)

      setProgress('Parsing file...')

      const formData = new FormData()

      formData.append('file', file)

      const progressTimer = setInterval(() => {
        setProgress((prev) => {
          if (prev === 'Parsing file...') {
            return 'Fetching live prices...'
          }

          if (
            prev ===
            'Fetching live prices...'
          ) {
            return 'Enriching portfolio data...'
          }

          if (
            prev ===
            'Enriching portfolio data...'
          ) {
            return 'Almost done...'
          }

          return prev
        })
      }, 4000)

      try {
        const res =
          await axios.post<UploadResult>(
            `${API_BASE}/api/portfolio/upload`,
            formData,
            {
              headers: {
                'Content-Type':
                  'multipart/form-data',
              },

              timeout: 90_000,
            }
          )

        clearInterval(progressTimer)

        setSuccess(true)

        setSourceType(
          res.data.source ?? 'csv'
        )

        if (res.data.validation) {
          setValidation(
            res.data.validation
          )

          const v = res.data.validation

          if (
            (v.warning_count ?? 0) > 0 ||
            (v.low_confidence_count ?? 0) > 0
          ) {
            setShowValidation(true)
          }
        }

        onUploadSuccess(res.data)
      } catch (e: any) {
        clearInterval(progressTimer)

        const msg =
          e.response?.data?.detail ??
          e.message ??
          'Upload failed'

        const friendly =
          typeof msg === 'string'
            ? msg.includes('timeout')
              ? 'Request timed out. The server may be fetching prices for many stocks. Please try again.'
              : msg
            : JSON.stringify(msg)

        setError(friendly)
      } finally {
        clearInterval(progressTimer)
        setIsLoading(false)
        setProgress('')
      }
    },
    [validateFile, onUploadSuccess]
  )

  // Load demo portfolio — creates a File object from the CSV string
  // and runs it through the exact same upload pipeline as a real file.
  const handleDemo = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation()
      const blob = new Blob([DEMO_CSV], { type: 'text/csv' })
      const file = new File([blob], 'demo_portfolio.csv', { type: 'text/csv' })
      handleFile(file)
    },
    [handleFile]
  )

  const handleDrop = useCallback(
    (
      e: React.DragEvent<HTMLDivElement>
    ) => {
      e.preventDefault()

      setIsDragging(false)

      const file =
        e.dataTransfer.files[0]

      if (file) {
        handleFile(file)
      }
    },
    [handleFile]
  )

  const handleInputChange = useCallback(
    (
      e: React.ChangeEvent<HTMLInputElement>
    ) => {
      const file = e.target.files?.[0]

      if (file) {
        handleFile(file)
      }

      e.target.value = ''
    },
    [handleFile]
  )

  const handleReset = useCallback(
    (
      e: React.MouseEvent<HTMLButtonElement>
    ) => {
      e.stopPropagation()

      setSuccess(false)
      setSourceType(null)
      setValidation(null)
      setShowValidation(false)
      setFileName(null)
      setError(null)
    },
    []
  )

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">

      {/* Drop zone */}

      <div
        onClick={() =>
          !isLoading &&
          fileInputRef.current?.click()
        }
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() =>
          setIsDragging(false)
        }
        onDrop={handleDrop}
        className={[
          'border-2 border-dashed rounded-2xl p-10 text-center transition-colors duration-200',

          isLoading
            ? 'cursor-wait opacity-80'
            : 'cursor-pointer',

          isDragging
            ? 'border-blue-400 bg-blue-950/20'
            : success
            ? 'border-green-700 bg-green-950/10'
            : 'border-gray-700 hover:border-gray-500 bg-gray-900/40',
        ].join(' ')}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          onChange={handleInputChange}
        />

        {isLoading && (
          <div className="flex flex-col items-center gap-4">
            <div className="relative w-14 h-14">
              <div className="w-14 h-14 border-4 border-blue-900 rounded-full" />

              <div className="absolute inset-0 w-14 h-14 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
            </div>

            <div>
              <p className="text-gray-200 font-medium">
                {progress || 'Processing...'}
              </p>

              {fileName && (
                <p className="text-gray-500 text-sm mt-1">
                  {fileName}
                </p>
              )}
            </div>

            <p className="text-gray-600 text-xs">
              This may take 10-30 seconds for live price fetching
            </p>
          </div>
        )}

        {!isLoading && success && (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle
              size={44}
              className="text-green-400"
            />

            <p className="text-green-400 font-semibold text-lg">
              Portfolio loaded!
            </p>

            {sourceType && (
              <span className="text-xs bg-gray-800 text-gray-300 px-3 py-1 rounded-full">
                {SOURCE_LABELS[sourceType] ??
                  sourceType}
              </span>
            )}

            <button
              onClick={handleReset}
              className="text-xs text-gray-500 hover:text-gray-300 underline mt-1"
            >
              Upload different file
            </button>
          </div>
        )}

        {!isLoading && !success && (
          <div className="flex flex-col items-center gap-4">
            <div className="w-14 h-14 bg-blue-600/15 rounded-2xl flex items-center justify-center">
              <Upload
                size={28}
                className="text-blue-400"
              />
            </div>

            <div>
              <p className="text-white font-semibold text-lg">
                Drop your file or click
              </p>

              <p className="text-gray-400 mt-1 text-sm">
                CSV · Excel · PDF · Zerodha · Groww
              </p>
            </div>

            <p className="text-gray-600 text-xs">
              Max {MAX_FILE_MB}MB · Up to 50 holdings
            </p>
          </div>
        )}
      </div>

      {/* Demo button — shown only when idle (not loading, not already succeeded) */}
      {!isLoading && !success && (
        <button
          onClick={handleDemo}
          className="w-full flex items-center justify-center gap-2 border border-blue-800/50 bg-blue-950/20 hover:bg-blue-950/40 text-blue-400 hover:text-blue-300 py-3 rounded-xl text-sm font-medium transition-all"
        >
          <Sparkles size={15} />
          ✨ Try with Demo Portfolio — no file needed
        </button>
      )}

      {/* Error */}

      {error && (
        <div className="flex items-start gap-3 bg-red-950/40 border border-red-800 text-red-300 px-4 py-3 rounded-xl">
          <span className="text-sm flex-1">
            {error}
          </span>

          <button
            onClick={() =>
              setError(null)
            }
            className="shrink-0 hover:text-red-100 transition-colors mt-0.5"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Validation report */}

      {validation && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <button
            onClick={() =>
              setShowValidation(
                !showValidation
              )
            }
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/40 transition-colors"
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-white">
                Ingestion Report
              </span>

              <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded-full">
                {validation.valid_count} valid
              </span>

              {(validation.error_count ??
                0) > 0 && (
                <span className="text-xs bg-red-900/40 text-red-400 px-2 py-0.5 rounded-full">
                  {validation.error_count} errors
                </span>
              )}

              {(validation.low_confidence_count ??
                0) > 0 && (
                <span className="text-xs bg-yellow-900/40 text-yellow-400 px-2 py-0.5 rounded-full">
                  {
                    validation.low_confidence_count
                  }{' '}
                  low confidence
                </span>
              )}

              {(validation.warnings?.length ??
                0) > 0 && (
                <span className="text-xs bg-orange-900/40 text-orange-400 px-2 py-0.5 rounded-full">
                  {
                    validation.warnings.length
                  }{' '}
                  warnings
                </span>
              )}
            </div>

            {showValidation ? (
              <ChevronUp
                size={14}
                className="text-gray-500 shrink-0"
              />
            ) : (
              <ChevronDown
                size={14}
                className="text-gray-500 shrink-0"
              />
            )}
          </button>

          {showValidation && (
            <div className="px-4 pb-4 space-y-3 border-t border-gray-800">

              {validation.errors?.length >
                0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-red-400 text-xs font-medium mb-2">
                    ❌ Errors
                  </p>

                  {validation.errors.map(
                    (e, i) => (
                      <p
                        key={i}
                        className="text-red-300 text-xs bg-red-950/20 px-3 py-1.5 rounded-lg"
                      >
                        {e}
                      </p>
                    )
                  )}
                </div>
              )}

              {validation.warnings?.length >
                0 && (
                <div className="space-y-1">
                  <p className="text-orange-400 text-xs font-medium mb-2">
                    ⚠️ Warnings
                  </p>

                  {validation.warnings.map(
                    (w, i) => (
                      <p
                        key={i}
                        className="text-orange-300 text-xs bg-orange-950/10 px-3 py-1.5 rounded-lg"
                      >
                        {w}
                      </p>
                    )
                  )}
                </div>
              )}

              {validation.low_confidence
                ?.length > 0 && (
                <div className="space-y-1">
                  <p className="text-yellow-400 text-xs font-medium mb-2">
                    🔍 Low Confidence
                  </p>

                  {validation.low_confidence.map(
                    (lc, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between bg-yellow-950/10 px-3 py-2 rounded-lg"
                      >
                        <span className="text-gray-400 text-xs">
                          &ldquo;{lc.raw}
                          &rdquo; →{' '}
                          <span className="text-white">
                            {lc.symbol}
                          </span>
                        </span>

                        <span className="text-xs text-yellow-400">
                          {Math.round(
                            lc.confidence *
                              100
                          )}
                          %
                        </span>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Format guide */}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">

        <div className="flex items-center justify-between mb-3">
          <p className="text-gray-400 text-sm font-medium">
            📋 Supported formats
          </p>

          <a
              href={`${API_BASE}/api/portfolio/template`}
              download
              onClick={(
                e: React.MouseEvent<HTMLAnchorElement>
              ) => e.stopPropagation()}
              className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
            <Download size={11} />
            Template
          </a>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">

          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs font-medium mb-1">
              Standard CSV:
            </p>

            <code className="text-xs text-green-400">
              Symbol, Qty, Buy_Price,
              Sector
              <br />
              RELIANCE.NS, 10, 1280,
              Energy
            </code>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs font-medium mb-1">
              Also supports:
            </p>

            <p className="text-xs text-gray-400">
              🟠 Zerodha Console export
              <br />
              🟢 Groww portfolio export
            </p>
          </div>

        </div>
      </div>
    </div>
  )
})

export default UploadPortfolio
