import { useEffect, useState } from 'react'
import { Building2, MapPin, Bed, Stethoscope } from 'lucide-react'
import { fetchFacilities } from '../services/api'

const traumaColors: Record<string, string> = {
  LEVEL_1: 'bg-rose-100 text-rose-700',
  LEVEL_2: 'bg-amber-100 text-amber-700',
  LEVEL_3: 'bg-blue-100 text-blue-700',
  NONE: 'bg-slate-100 text-slate-600',
}

export default function Facilities() {
  const [facilities, setFacilities] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFacilities()
      .then(res => setFacilities(res.data || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-slate-500">Loading facilities...</div>

  return (
    <div className="p-6 max-w-7xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Facilities</h1>
        <p className="text-sm text-slate-500 mt-1">Network hospitals and their capabilities</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {facilities.map((f: any, i: number) => (
          <div key={f.id} className="card card-hover p-5 animate-fade-in-up" style={{ animationDelay: `${i * 40}ms` }}>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center shadow-sm">
                  <Building2 className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{f.name}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1">
                    <MapPin className="w-3 h-3" /> {f.city}, {f.state} {f.zip_code}
                  </p>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${traumaColors[f.trauma_level] || traumaColors.NONE}`}>
                {f.trauma_level === 'NONE' ? 'Non-Trauma' : f.trauma_level?.replace('_', ' ')}
              </span>
            </div>

            {/* Beds */}
            {f.bed_availability?.length > 0 && (
              <div className="mb-3">
                <p className="text-xs font-semibold text-slate-500 mb-1.5 flex items-center gap-1">
                  <Bed className="w-3 h-3" /> Bed Availability
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {f.bed_availability.map((b: any) => (
                    <div key={b.unit_type} className={`text-[10px] px-2 py-1 rounded-lg border ${
                      b.available_beds > 2 ? 'border-emerald-200 bg-emerald-50 text-emerald-700' :
                      b.available_beds > 0 ? 'border-amber-200 bg-amber-50 text-amber-700' :
                      'border-rose-200 bg-rose-50 text-rose-700'
                    }`}>
                      {b.unit_type}: <span className="font-bold">{b.available_beds}</span>/{b.total_beds}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Capabilities */}
            {f.capabilities?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1.5 flex items-center gap-1">
                  <Stethoscope className="w-3 h-3" /> Capabilities
                </p>
                <div className="flex flex-wrap gap-1">
                  {f.capabilities.filter((c: any) => c.category === 'SPECIALTY').map((c: any) => (
                    <span key={c.name} className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                      {c.name.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {f.transfer_center_phone && (
              <p className="text-xs text-slate-400 mt-3">Transfer Center: {f.transfer_center_phone}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
