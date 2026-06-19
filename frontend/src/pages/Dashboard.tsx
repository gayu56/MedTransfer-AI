import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, Clock, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react'
import { fetchTransfers, fetchAnalytics } from '../services/api'

const statusColors: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  INITIATED: 'bg-blue-100 text-blue-700',
  PENDING_REVIEW: 'bg-amber-100 text-amber-700',
  ACCEPTED: 'bg-emerald-100 text-emerald-700',
  TRANSPORT_DISPATCHED: 'bg-purple-100 text-purple-700',
  IN_TRANSIT: 'bg-indigo-100 text-indigo-700',
  ARRIVED: 'bg-teal-100 text-teal-700',
  COMPLETED: 'bg-green-100 text-green-700',
  DECLINED: 'bg-rose-100 text-rose-700',
  CANCELLED: 'bg-slate-100 text-slate-600',
  RE_ROUTING: 'bg-orange-100 text-orange-700',
}

const urgencyColors: Record<string, string> = {
  EMERGENT: 'bg-rose-500 text-white',
  URGENT: 'bg-amber-500 text-white',
  ROUTINE: 'bg-slate-400 text-white',
}

export default function Dashboard() {
  const [transfers, setTransfers] = useState<any[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [tRes, aRes] = await Promise.all([fetchTransfers(), fetchAnalytics()])
        setTransfers(tRes.data || [])
        setAnalytics(aRes)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const stats = [
    { label: 'Active Transfers', value: analytics?.active_transfers ?? 0, icon: Activity, color: 'text-primary-600', bg: 'bg-primary-50', accent: 'from-primary-400 to-primary-600' },
    { label: 'Completed', value: analytics?.completed_transfers ?? 0, icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50', accent: 'from-emerald-400 to-emerald-600' },
    { label: 'Total', value: analytics?.total_transfers ?? 0, icon: Clock, color: 'text-slate-600', bg: 'bg-slate-100', accent: 'from-slate-300 to-slate-500' },
    { label: 'Emergent', value: analytics?.by_urgency?.emergent ?? 0, icon: AlertTriangle, color: 'text-rose-600', bg: 'bg-rose-50', accent: 'from-rose-400 to-rose-600' },
  ]

  if (loading) {
    return <div className="p-8 text-slate-500">Loading dashboard...</div>
  }

  return (
    <div className="p-6 max-w-7xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Transfer Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time overview of all patient transfers</p>
        </div>
        <Link
          to="/dashboard/transfers/new"
          className="px-4 py-2.5 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg text-sm font-medium hover:from-primary-700 hover:to-primary-800 transition-all shadow-sm shadow-primary-600/30 hover:shadow-md hover:-translate-y-0.5 flex items-center gap-2"
        >
          New Transfer <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color, bg, accent }, i) => (
          <div
            key={label}
            className="stat-card p-5 animate-fade-in-up"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${accent}`} />
            <div className="flex items-center gap-3">
              <div className={`w-11 h-11 rounded-xl ${bg} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 tabular-nums">{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Transfer List */}
      <div className="card overflow-hidden animate-fade-in-up" style={{ animationDelay: '240ms' }}>
        <div className="px-6 py-4 border-b border-slate-200/70 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 tracking-tight">Recent Transfers</h2>
          <span className="text-xs text-slate-400">{transfers.length} total</span>
        </div>
        {transfers.length === 0 ? (
          <div className="p-12 text-center">
            <Activity className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No transfers yet. Start by creating a new transfer.</p>
            <Link to="/dashboard/transfers/new" className="text-primary-600 text-sm font-medium hover:underline mt-2 inline-block">
              Create New Transfer →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {transfers.map((t: any) => (
              <Link
                key={t.id}
                to={`/dashboard/transfers/${t.id}`}
                className="group flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${urgencyColors[t.urgency] || 'bg-slate-200'}`}>
                    {t.urgency}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {t.patient?.first_name} {t.patient?.last_name}
                      <span className="text-slate-400 font-normal ml-2">
                        {t.patient?.age}{t.patient?.gender} · MRN: {t.patient?.mrn}
                      </span>
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{t.transfer_number} · {t.reason_for_transfer?.substring(0, 80)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[t.status] || 'bg-slate-100'}`}>
                    {t.status?.replace(/_/g, ' ')}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
