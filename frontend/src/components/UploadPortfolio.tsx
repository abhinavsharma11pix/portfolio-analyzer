import { useState, useRef, useCallback, memo } from 'react'
import {
  Upload,
  CheckCircle,
  X,
  Download,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import axios from 'axios'

/* ── Types ── */

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
  confidence?: number
  warnings?: string[]
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
const ALLOWED_EXTS = ['.csv', '.xlsx', '.xls', '.pdf']

const UploadPortfolio = memo(function UploadPortfolio({
  onUploadSuccess,
}: Props) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [showValidation, setShowValidation] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase()

    if (!ALLOWED_EXTS.includes(ext)) {
      return 'Only CSV, Excel or PDF files allowed'
    }

    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      return `File too large. Max ${MAX_FILE_MB}MB`
    }

    return null
  }, [])

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

      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await axios.post<UploadResult>(
          'http://localhost:8000/api/portfolio/upload',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            timeout: 60000,
          }
        )

        setSuccess(true)
        setSourceType(res.data.source ?? 'csv')

        if (res.data.validation) {
          setValidation(res.data.validation)

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
        const msg =
          e.response?.data?.detail ??
          e.message ??
          'Upload failed'

        setError(
          typeof msg === 'string'
            ? msg
            : JSON.stringify(msg)
        )
      } finally {
        setIsLoading(false)
      }
    },
    [validateFile, onUploadSuccess]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)

      const file = e.dataTransfer.files[0]

      if (file) {
        handleFile(file)
      }
    },
    [handleFile]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]

      if (file) {
        handleFile(file)
      }
    },
    [handleFile]
  )

  const handleReset = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation()

      setSuccess(false)
      setSourceType(null)
      setValidation(null)
      setShowValidation(false)
      setFileName(null)
      setError(null)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    []
  )

  const handleZoneClick = useCallback(() => {
    if (!isLoading) {
      fileInputRef.current?.click()
    }
  }, [isLoading])

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">

      {/* Drop Zone */}
      <div
        onClick={handleZoneClick}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={[
          'border-2 border-dashed rounded-2xl p-10 text-center transition-colors duration-200',
          isLoading
            ? 'cursor-wait opacity-75'
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
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />

            <p className="text-gray-300 font-medium">
              Parsing &amp; fetching live prices...
            </p>

            {fileName && (
              <p className="text-gray-500 text-sm">
                {fileName}
              </p>
            )}
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
              <span className="text-xs bg-blue-900/40 text-blue-300 px-3 py-1 rounded-full">
                {SOURCE_LABELS[sourceType] ?? sourceType}
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

      {/* Error Banner */}
      {error && (
        <div className="flex items-start gap-3 bg-red-950/40 border border-red-800 text-red-400 px-4 py-3 rounded-xl">
          <span className="text-sm flex-1">
            {error}
          </span>

          <button
            onClick={() => setError(null)}
            className="shrink-0 hover:text-red-200 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Validation Report */}
      {validation && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">

          <button
            onClick={() =>
              setShowValidation(!showValidation)
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

              {(validation.error_count ?? 0) > 0 && (
                <span className="text-xs bg-red-900/40 text-red-400 px-2 py-0.5 rounded-full">
                  {validation.error_count} errors
                </span>
              )}

              {(validation.low_confidence_count ?? 0) > 0 && (
                <span className="text-xs bg-yellow-900/40 text-yellow-400 px-2 py-0.5 rounded-full">
                  {validation.low_confidence_count} low confidence
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

              {validation.errors?.length > 0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-red-400 text-xs font-medium mb-2">
                    ❌ Errors (rows skipped)
                  </p>

                  {validation.errors.map((e, i) => (
                    <p
                      key={i}
                      className="text-red-300 text-xs bg-red-950/20 px-3 py-1.5 rounded-lg"
                    >
                      {e}
                    </p>
                  ))}
                </div>
              )}

              {validation.warnings?.length > 0 && (
                <div className="space-y-1">
                  <p className="text-yellow-400 text-xs font-medium mb-2">
                    ⚠️ Warnings
                  </p>

                  {validation.warnings.map((w, i) => (
                    <p
                      key={i}
                      className="text-yellow-300 text-xs bg-yellow-950/20 px-3 py-1.5 rounded-lg"
                    >
                      {w}
                    </p>
                  ))}
                </div>
              )}

              {validation.low_confidence?.length > 0 && (
                <div className="space-y-1">
                  <p className="text-yellow-400 text-xs font-medium mb-2">
                    🔍 Low Confidence Symbol Mappings
                  </p>

                  {validation.low_confidence.map((lc, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between bg-yellow-950/10 px-3 py-2 rounded-lg"
                    >
                      <span className="text-gray-400 text-xs">
                        &ldquo;{lc.raw}&rdquo;

                        <span className="text-gray-500 mx-2">
                          →
                        </span>

                        <span className="text-white font-medium">
                          {lc.symbol}
                        </span>
                      </span>

                      <span className="text-xs text-yellow-400 shrink-0">
                        {Math.round(
                          lc.confidence * 100
                        )}
                        %
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {validation.errors?.length === 0 &&
                validation.warnings?.length === 0 &&
                validation.low_confidence?.length === 0 && (
                  <p className="text-green-400 text-xs mt-3">
                    ✅ All {validation.valid_count}{' '}
                    holdings parsed with high confidence
                  </p>
                )}
            </div>
          )}
        </div>
      )}

      {/* Format Guide */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">

        <div className="flex items-center justify-between mb-3">
          <p className="text-gray-400 text-sm font-medium">
            📋 Supported formats
          </p>

          <a
            href="http://localhost:8000/api/portfolio/template"
            download="portfolio_template.xlsx"
            onClick={(
              e: React.MouseEvent<HTMLAnchorElement>
            ) => e.stopPropagation()}
            className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            <Download size={11} />
            Download Template
          </a>
        </div>

        <div className="space-y-2">

          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-400 text-xs font-medium mb-1">
              Standard CSV / Template:
            </p>

            <code className="text-xs text-green-400 leading-relaxed">
              Symbol, Quantity, Buy_Price, Sector
              <br />
              RELIANCE.NS, 10, 2500, Energy
              <br />
              AAPL, 3, 175, Technology
            </code>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-400 text-xs font-medium mb-1">
              🟠 Zerodha Console export:
            </p>

            <code className="text-xs text-orange-400 leading-relaxed">
              Instrument, Qty., Avg. cost, ...
            </code>
          </div>

          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-400 text-xs font-medium mb-1">
              🟢 Groww export:
            </p>

            <code className="text-xs text-green-400 leading-relaxed">
              Stock Name, NSE Symbol, Quantity,
              Average Price
            </code>
          </div>

        </div>
      </div>
    </div>
  )
})

export default UploadPortfolio