import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, User, ArrowRight } from 'lucide-react'
import { fetchPatients } from '../services/api'

export default function Patients() {
  const [patients, setPatients] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchPatients(search || undefined)
        setPatients(res.data || [])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [search])

  return (
    <div className="p-6 max-w-7xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Patients</h1>
          <p className="text-sm text-slate-500 mt-1">Select a patient to initiate a transfer</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6 max-w-md">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search by name or MRN..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-400 transition-all bg-white"
        />
      </div>

      {loading ? (
        <p className="text-slate-500">Loading patients...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {patients.map((p: any, i: number) => (
            <Link
              key={p.id}
              to={`/dashboard/transfers/new?patient_id=${p.id}`}
              className="card card-hover p-5 group animate-fade-in-up"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center text-primary-700 font-bold text-sm ring-2 ring-white shadow-sm">
                    {p.first_name?.[0]}{p.last_name?.[0]}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{p.first_name} {p.last_name}</p>
                    <p className="text-xs text-slate-500">{p.age}{p.gender} · MRN: {p.mrn} · DOB: {p.date_of_birth}</p>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 group-hover:translate-x-0.5 transition-all" />
              </div>

              {/* Quick clinical info */}
              <div className="mt-3 space-y-1.5">
                {(p.active_conditions || []).slice(0, 2).map((c: any, i: number) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                    <span className="text-xs text-slate-600">{c.display}</span>
                  </div>
                ))}
                {p.insurance_provider && (
                  <p className="text-xs text-slate-400">Insurance: {p.insurance_provider} — {p.insurance_plan_name}</p>
                )}
                <p className="text-xs text-slate-400">Code Status: {p.code_status} · Language: {p.primary_language}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
