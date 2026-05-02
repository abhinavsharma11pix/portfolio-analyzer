import { useNavigate } from 'react-router-dom'
import { BarChart3, Shield, TrendingUp, Brain } from 'lucide-react'

const features = [
  {
    icon: <BarChart3 size={24} className="text-blue-400" />,
    title: 'Real-Time Tracking',
    description: 'Track Indian & US stocks live with instant portfolio valuation.',
  },
  {
    icon: <Shield size={24} className="text-green-400" />,
    title: 'Risk Analytics',
    description: 'Sharpe ratio, volatility, drawdown — know your real risk exposure.',
  },
  {
    icon: <TrendingUp size={24} className="text-purple-400" />,
    title: 'Price Predictions',
    description: 'ML-powered 30-day forecasts using Prophet & LSTM models.',
  },
  {
    icon: <Brain size={24} className="text-yellow-400" />,
    title: 'AI Insights',
    description: 'Get plain-English insights like "You are overexposed to banking sector".',
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="max-w-7xl mx-auto px-6 py-20">
      {/* Hero */}
      <div className="text-center mb-20">
        <div className="inline-block bg-blue-600/20 text-blue-400 text-sm font-medium px-4 py-1 rounded-full mb-6">
          AI-Powered Portfolio Analytics
        </div>
        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
          Understand Your Portfolio <br />
          <span className="text-blue-400">Like Never Before</span>
        </h1>
        <p className="text-gray-400 text-xl max-w-2xl mx-auto mb-10">
          Upload your holdings, get real-time data, risk metrics, AI insights
          and 30-day predictions — all in one place.
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
          >
            Analyze My Portfolio →
          </button>
          <button className="border border-gray-700 hover:border-gray-500 text-gray-300 px-8 py-3 rounded-lg font-semibold text-lg transition-colors">
            See Demo
          </button>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((f, i) => (
          <div
            key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-600 transition-colors"
          >
            <div className="mb-4">{f.icon}</div>
            <h3 className="text-white font-semibold text-lg mb-2">{f.title}</h3>
            <p className="text-gray-400 text-sm">{f.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}