import { useState, useRef } from 'react'
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, X } from 'lucide-react'
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
}

interface UploadResult {
  message: string
  total_holdings: number
  holdings: Holding[]
  summary: any
}

interface Props {
  onUploadSuccess: (data: UploadResult) => void
}

const MAX_FILE_MB = 5
const ALLOWED_TYPES = ['.csv', '.xlsx', '.xls']

export default function UploadPortfolio({ onUploadSuccess }: Props) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_TYPES.includes(ext)) return 'Only CSV or Excel files allowed'
    if (file.size > MAX_FILE_MB * 1024 * 1024) return `File too large. Max size is ${MAX_FILE_MB}MB`
    return null
  }

  const handleFile = async (file: File) => {
    const validationError = validateFile(file)
    if (validationError) { setError(validationError); return }

    setError(null)
    setSuccess(false)
    setFileName(file.name)
    setIsLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(
        'http://localhost:8000/api/portfolio/upload',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 30000 }
      )
      setSuccess(true)
      onUploadSuccess(res.data)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed. Please try again.'
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

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onClick={() => !isLoading && fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200
          ${isLoading ? 'cursor-wait' : 'cursor-pointer'}
          ${isDragging ? 'border-blue-400 bg-blue-950/30' : 'border-gray-700 hover:border-gray-500 bg-gray-900/50'}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {isLoading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-300 font-medium">Fetching live prices...</p>
            <p className="text-gray-500 text-sm">{fileName}</p>
          </div>
        ) : success ? (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle size={48} className="text-green-400" />
            <p className="text-green-400 font-semibold text-lg">Portfolio loaded!</p>
            <p className="text-gray-500 text-sm">{fileName} · Click to upload different file</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center">
              <Upload size={32} className="text-blue-400" />
            </div>
            <div>
              <p className="text-white font-semibold text-lg">Drop your portfolio file here</p>
              <p className="text-gray-400 mt-1">or click to browse</p>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <FileSpreadsheet size={16} />
              <span>CSV or Excel · Max {MAX_FILE_MB}MB · Up to 50 holdings</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 flex items-start gap-3 bg-red-950/50 border border-red-800 text-red-400 px-4 py-3 rounded-xl">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span className="text-sm flex-1">{error}</span>
          <button onClick={() => setError(null)}><X size={16} /></button>
        </div>
      )}

      <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <p className="text-gray-400 text-sm font-medium mb-2">📋 Required CSV format:</p>
        <code className="text-xs text-green-400 leading-relaxed">
          symbol, quantity, avg_buy_price, sector<br />
          RELIANCE.NS, 10, 2500, Energy<br />
          TCS.NS, 5, 3500, Technology<br />
          AAPL, 3, 175, Technology
        </code>
      </div>
    </div>
  )
}