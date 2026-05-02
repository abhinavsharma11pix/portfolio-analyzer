import { useState, useRef } from 'react'
import {
  Upload, FileSpreadsheet, CheckCircle,
  AlertCircle, X, Download, Info
} from 'lucide-react'
import axios from 'axios'

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
  raw_symbol?: string
  warnings?: string[]
}

interface UploadResult {
  message: string
  total_holdings: number
  holdings: Holding[]
  summary: any
  source?: string
  validation?: {
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
}

interface Props {
  onUploadSuccess: (data: UploadResult) => void
}

const MAX_FILE_MB = 5
const ALLOWED_TYPES = ['.csv', '.xlsx', '.xls', '.pdf']

const SOURCE_LABELS: Record<string, string> = {
  csv:     '📄 Standard CSV',
  excel:   '📊 Excel File',
  zerodha: '🟠 Zerodha Statement',
  groww:   '🟢 Groww Statement',
  pdf:     '📑 PDF Contract Note',
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color =
    pct >= 90 ? 'bg-green-900/50 text-green-400' :
    pct >= 70 ? 'bg-yellow-900/50 text-yellow-400' :
                'bg-red-900/50 text-red-400'

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {pct}% confidence
    </span>
  )
}

export default function UploadPortfolio({ onUploadSuccess }: Props) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [validation, setValidation] = useState<UploadResult['validation'] | null>(null)
  const [showValidation, setShowValidation] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_TYPES.includes(ext))
      return 'Only CSV, Excel or PDF files allowed'
    if (file.size > MAX_FILE_MB * 1024 * 1024)
      return `File too large. Max size is ${MAX_FILE_MB}MB`
    return null
  }

  const handleFile = async (file: File) => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
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
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000,
        }
      )

      setSuccess(true)
      setSourceType(res.data.source || 'csv')

      if (res.data.validation) {
        setValidation(res.data.validation)

        if (
          res.data.validation.warning_count > 0 ||
          res.data.validation.low_confidence_count > 0
        ) {
          setShowValidation(true)
        }
      }

      onUploadSuccess(res.data)
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Upload failed. Please try again.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setIsLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleReset = () => {
    setSuccess(false)
    setSourceType(null)
    setValidation(null)
    setShowValidation(false)
    setFileName(null)
    setError(null)
  }

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">

      {/* Upload Zone */}
      <div
        onClick={() => !isLoading && fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all
        ${isLoading ? 'cursor-wait opacity-80' : 'cursor-pointer'}
        ${isDragging ? 'border-blue-400 bg-blue-950/30'
        : 'border-gray-700 hover:border-gray-500 bg-gray-900/50'}`}
      >

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {isLoading && (
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-300">Parsing & fetching prices...</p>
          </div>
        )}

        {!isLoading && success && (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle size={40} className="text-green-400" />
            <p className="text-green-400 font-semibold">Portfolio loaded</p>
            {sourceType && (
              <span className="text-xs bg-blue-900/50 px-3 py-1 rounded-full">
                {SOURCE_LABELS[sourceType]}
              </span>
            )}
            <button onClick={handleReset} className="text-xs text-gray-400 underline">
              Upload again
            </button>
          </div>
        )}

        {!isLoading && !success && (
          <div className="flex flex-col items-center gap-4">
            <Upload size={32} className="text-blue-400" />
            <p className="text-white">Drop your file or click</p>
            <p className="text-gray-500 text-sm">CSV · Excel · PDF</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950 text-red-400 p-3 rounded-lg flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)}><X size={14} /></button>
        </div>
      )}

      {validation && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-white font-medium mb-2">Ingestion Summary</p>

          <div className="flex gap-2 flex-wrap text-xs">
            <span className="bg-green-900/50 text-green-400 px-2 py-1 rounded">
              {validation.valid_count} valid
            </span>

            {validation.error_count > 0 && (
              <span className="bg-red-900/50 text-red-400 px-2 py-1 rounded">
                {validation.error_count} errors
              </span>
            )}

            {validation.warning_count > 0 && (
              <span className="bg-yellow-900/50 text-yellow-400 px-2 py-1 rounded">
                {validation.warning_count} warnings
              </span>
            )}
          </div>
        </div>
      )}

      {/* Template Download */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex justify-between items-center">

          <p className="text-gray-400 text-sm">📋 Supported formats</p>

          <a
            href="http://localhost:8000/api/portfolio/template"
            download="portfolio_template.xlsx"
            onClick={(e: React.MouseEvent<HTMLAnchorElement>) => e.stopPropagation()}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg
            ${isLoading
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-500 text-white'}`}
          >
            <Download size={12} />
            Download Template
          </a>

        </div>
      </div>

    </div>
  )
}