import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowRight, AlertTriangle, Clock, Zap, FileText, ShieldCheck, ShieldAlert } from 'lucide-react'
import { fetchPatient, fetchPatients, createTransfer, generateSBAR } from '../services/api'

export default function NewTransfer() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState<any>(null)
  const [sbar, setSbar] = useState<any>(null)
  const [sbarId, setSbarId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    urgency: 'EMERGENT',
    reason_for_transfer: '',
    requested_specialty: '',
    requested_unit_type: '',
    additional_notes: '',
  })

  useEffect(() => {
    const pid = searchParams.get('patient_id')
    if (pid) {
      fetchPatient(pid).then(p => { setSelectedPatient(p); setStep(2) })
    } else {
      fetchPatients().then(res => setPatients(res.data || []))
    }
  }, [searchParams])

  const handleGenerateSBAR = async () => {
    if (!selectedPatient || !form.reason_for_transfer) return
    setLoading(true)
    try {
      const res = await generateSBAR({
        patient_id: selectedPatient.id,
        reason_for_transfer: form.reason_for_transfer,
        urgency: form.urgency,
        requested_specialty: form.requested_specialty || undefined,
        additional_context: form.additional_notes || undefined,
      })
      setSbar(res)
      setSbarId(res.id || null)
      setStep(3)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitTransfer = async () => {
    if (!selectedPatient) return
    setSubmitting(true)
    try {
      const res = await createTransfer({
        patient_id: selectedPatient.id,
        urgency: form.urgency,
        reason_for_transfer: form.reason_for_transfer,
        requested_specialty: form.requested_specialty || undefined,
        requested_unit_type: form.requested_unit_type || undefined,
        additional_notes: form.additional_notes || undefined,
        clinical_summary_id: sbarId || undefined,
      })
      navigate(`/transfers/${res.id}`)
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900 mb-1">New Transfer Request</h1>
      <p className="text-sm text-slate-500 mb-6">Follow the steps below to initiate a patient transfer</p>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-8">
        {['Select Patient', 'Transfer Details', 'Review SBAR', 'Submit'].map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step > i + 1 ? 'bg-emerald-500 text-white' : step === i + 1 ? 'bg-primary-600 text-white' : 'bg-slate-200 text-slate-500'
            }`}>
              {step > i + 1 ? '✓' : i + 1}
            </div>
            <span className={`text-xs font-medium ${step === i + 1 ? 'text-primary-700' : 'text-slate-400'}`}>{label}</span>
            {i < 3 && <div className="w-8 h-px bg-slate-200" />}
          </div>
        ))}
      </div>

      {/* Step 1: Select Patient */}
      {step === 1 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Select Patient</h2>
          <div className="space-y-3">
            {patients.map((p: any) => (
              <button
                key={p.id}
                onClick={() => { setSelectedPatient(p); setStep(2) }}
                className="w-full text-left p-4 rounded-lg border border-slate-200 hover:border-primary-300 hover:bg-primary-50 transition-all"
              >
                <p className="text-sm font-semibold text-slate-900">{p.first_name} {p.last_name}</p>
                <p className="text-xs text-slate-500">{p.age}{p.gender} · MRN: {p.mrn} · {p.insurance_provider}</p>
                <div className="flex gap-2 mt-2 flex-wrap">
                  {(p.active_conditions || []).slice(0, 2).map((c: any, i: number) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 bg-rose-50 text-rose-600 rounded-full">{c.display}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Transfer Details */}
      {step === 2 && selectedPatient && (
        <div className="space-y-6">
          {/* Patient Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-semibold text-slate-900">{selectedPatient.first_name} {selectedPatient.last_name}</p>
                <p className="text-sm text-slate-500">{selectedPatient.age}{selectedPatient.gender} · MRN: {selectedPatient.mrn} · {selectedPatient.insurance_provider}</p>
              </div>
              <button onClick={() => { setSelectedPatient(null); setStep(1) }} className="text-xs text-primary-600 hover:underline">Change Patient</button>
            </div>
          </div>

          {/* Form */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
            <h2 className="text-lg font-semibold text-slate-900">Transfer Details</h2>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Urgency Level *</label>
              <div className="flex gap-3">
                {[
                  { value: 'EMERGENT', icon: Zap, label: 'Emergent', desc: 'Life-threatening, immediate', color: 'rose' },
                  { value: 'URGENT', icon: AlertTriangle, label: 'Urgent', desc: 'Serious, within hours', color: 'amber' },
                  { value: 'ROUTINE', icon: Clock, label: 'Routine', desc: 'Non-urgent, planned', color: 'slate' },
                ].map(({ value, icon: Icon, label, desc, color }) => (
                  <button
                    key={value}
                    onClick={() => setForm({ ...form, urgency: value })}
                    className={`flex-1 p-4 rounded-lg border-2 text-left transition-all ${
                      form.urgency === value ? `border-${color}-500 bg-${color}-50` : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <Icon className={`w-5 h-5 mb-2 ${form.urgency === value ? `text-${color}-600` : 'text-slate-400'}`} />
                    <p className="text-sm font-semibold text-slate-900">{label}</p>
                    <p className="text-xs text-slate-500">{desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Reason for Transfer *</label>
              <textarea
                value={form.reason_for_transfer}
                onChange={e => setForm({ ...form, reason_for_transfer: e.target.value })}
                placeholder="e.g., Acute STEMI requiring emergent cardiac catheterization not available at this facility"
                rows={3}
                className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Requested Specialty</label>
                <select
                  value={form.requested_specialty}
                  onChange={e => setForm({ ...form, requested_specialty: e.target.value })}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                >
                  <option value="">Select specialty...</option>
                  <option value="INTERVENTIONAL_CARDIOLOGY">Interventional Cardiology</option>
                  <option value="NEUROSURGERY">Neurosurgery</option>
                  <option value="NEUROLOGY">Neurology</option>
                  <option value="TRAUMA_SURGERY">Trauma Surgery</option>
                  <option value="GENERAL_SURGERY">General Surgery</option>
                  <option value="ORTHOPEDIC_SURGERY">Orthopedic Surgery</option>
                  <option value="BURN_SURGERY">Burn Surgery</option>
                  <option value="PSYCHIATRY">Psychiatry</option>
                  <option value="NEONATOLOGY">Neonatology</option>
                  <option value="PEDIATRIC_SURGERY">Pediatric Surgery</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Requested Unit Type</label>
                <select
                  value={form.requested_unit_type}
                  onChange={e => setForm({ ...form, requested_unit_type: e.target.value })}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                >
                  <option value="">Select unit...</option>
                  <option value="ICU">ICU</option>
                  <option value="CCU">CCU</option>
                  <option value="TELE">Telemetry</option>
                  <option value="MED_SURG">Med-Surg</option>
                  <option value="PSYCH_ACUTE">Psych Acute</option>
                  <option value="NICU">NICU</option>
                  <option value="PICU">PICU</option>
                  <option value="BURN_ICU">Burn ICU</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Additional Notes</label>
              <textarea
                value={form.additional_notes}
                onChange={e => setForm({ ...form, additional_notes: e.target.value })}
                placeholder="Any additional context for the receiving facility..."
                rows={2}
                className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="flex justify-between pt-2">
              <button onClick={() => setStep(1)} className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900">← Back</button>
              <button
                onClick={handleGenerateSBAR}
                disabled={!form.reason_for_transfer || loading}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                {loading ? 'Generating SBAR...' : 'Generate SBAR Summary'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Review SBAR */}
      {step === 3 && sbar && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-900">SBAR Clinical Summary</h2>
              {sbar.generated_by_ai && (
                <span className="text-[10px] px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">AI Generated</span>
              )}
            </div>

            {[
              { key: 'situation', label: 'S — Situation', color: 'blue' },
              { key: 'background', label: 'B — Background', color: 'emerald' },
              { key: 'assessment', label: 'A — Assessment', color: 'amber' },
              { key: 'recommendation', label: 'R — Recommendation', color: 'rose' },
            ].map(({ key, label, color }) => (
              <div key={key} className="mb-4">
                <div className={`text-xs font-bold text-${color}-600 uppercase tracking-wider mb-1`}>{label}</div>
                <div className="text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 rounded-lg p-3 border border-slate-100">
                  {sbar[key]}
                </div>
              </div>
            ))}

            {/* SBAR Verification Guard */}
            {sbar.generated_by_ai && sbar.verification && (
              <div className={`mt-4 p-4 rounded-lg border-2 ${
                sbar.verification.verified
                  ? 'border-emerald-300 bg-emerald-50'
                  : 'border-amber-400 bg-amber-50'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {sbar.verification.verified ? (
                    <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <ShieldAlert className="w-5 h-5 text-amber-600" />
                  )}
                  <div>
                    <p className={`text-sm font-bold ${sbar.verification.verified ? 'text-emerald-900' : 'text-amber-900'}`}>
                      EHR Verification: {sbar.verification.verification_score}% — {sbar.verification.verified_count}/{sbar.verification.total_values_checked} values verified
                    </p>
                    <p className={`text-[10px] ${sbar.verification.verified ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {sbar.verification.verified
                        ? 'All clinical values trace back to source EHR data'
                        : 'Some values could not be verified against source EHR — review flagged items below'
                      }
                    </p>
                  </div>
                </div>

                {sbar.verification.flags?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {sbar.verification.flags.map((flag: any, i: number) => (
                      <div key={i} className="flex items-start gap-2 text-[11px] bg-white rounded px-3 py-1.5 border border-amber-200">
                        <AlertTriangle className="w-3 h-3 text-amber-500 mt-0.5 shrink-0" />
                        <div>
                          <span className="font-bold text-amber-800 uppercase">{flag.section}</span>
                          <span className="text-amber-700"> — {flag.message}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-between pt-4 border-t border-slate-200 mt-4">
              <button onClick={() => setStep(2)} className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900">← Edit Details</button>
              <button
                onClick={handleSubmitTransfer}
                disabled={submitting}
                className="px-6 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
              >
                {submitting ? 'Submitting...' : 'Submit Transfer Request'} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
