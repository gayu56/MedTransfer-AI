import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Clock, AlertTriangle, Building2, Truck, Shield, FileText, Phone, Pencil, ShieldCheck, Upload, Download, Trash2 } from 'lucide-react'
import { fetchTransfer, acceptTransfer, declineTransfer, updateTransferStatus, updateCompliance, reviewSBAR, fetchComplianceDocuments, uploadComplianceDocument, deleteComplianceDocument, getDocumentDownloadUrl } from '../services/api'
import CallPanel from '../components/CallPanel'

const statusSteps = ['INITIATED', 'PENDING_REVIEW', 'ACCEPTED', 'TRANSPORT_DISPATCHED']
const statusColors: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  INITIATED: 'bg-blue-100 text-blue-700',
  PENDING_REVIEW: 'bg-amber-100 text-amber-700',
  ACCEPTED: 'bg-emerald-100 text-emerald-700',
  TRANSPORT_DISPATCHED: 'bg-purple-100 text-purple-700',
  DECLINED: 'bg-rose-100 text-rose-700',
  RE_ROUTING: 'bg-orange-100 text-orange-700',
}
const urgencyColors: Record<string, string> = {
  EMERGENT: 'bg-rose-500 text-white',
  URGENT: 'bg-amber-500 text-white',
  ROUTINE: 'bg-slate-400 text-white',
}

export default function TransferDetail() {
  const { id } = useParams<{ id: string }>()
  const [transfer, setTransfer] = useState<any>(null)
  const [sbarEditing, setSbarEditing] = useState(false)
  const [sbarDraft, setSbarDraft] = useState<Record<string, string>>({})
  const [sbarSaving, setSbarSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [complianceDocs, setComplianceDocs] = useState<any[]>([])
  const [uploading, setUploading] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [pendingDocType, setPendingDocType] = useState<string | null>(null)

  const load = async () => {
    if (!id) return
    try {
      const res = await fetchTransfer(id)
      setTransfer(res)
      const docs = await fetchComplianceDocuments(id)
      setComplianceDocs(docs)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleDocUpload = async (docType: string, file: File) => {
    if (!id) return
    setUploading(docType)
    try {
      await uploadComplianceDocument(id, docType, file)
      await load()
    } catch (e) { console.error('Upload failed:', e) }
    setUploading(null)
  }

  const handleDocDelete = async (docId: string) => {
    if (!id) return
    try {
      await deleteComplianceDocument(id, docId)
      await load()
    } catch (e) { console.error('Delete failed:', e) }
  }

  useEffect(() => { load() }, [id])

  const handleAccept = async () => {
    if (!id) return
    await acceptTransfer(id, { accepting_physician_notes: 'Accepted via dashboard' })
    load()
  }

  const handleDecline = async () => {
    if (!id) return
    await declineTransfer(id, { reason: 'NO_BED_AVAILABLE', notes: 'No beds currently', auto_reroute: true })
    load()
  }

  const handleComplianceToggle = async (field: string, current: boolean) => {
    if (!id) return
    await updateCompliance(id, { field, value: !current })
    // Auto-advance to TRANSPORT_DISPATCHED when all EMTALA checks pass
    const updated = await fetchTransfer(id)
    if (updated?.compliance_record?.all_checks_passed && updated.status === 'ACCEPTED') {
      try {
        await updateTransferStatus(id, { status: 'TRANSPORT_DISPATCHED' })
      } catch (e) { console.error('Auto-dispatch failed:', e) }
    }
    load()
  }

  if (loading) return <div className="p-8 text-slate-500">Loading transfer...</div>
  if (!transfer) return <div className="p-8 text-slate-500">Transfer not found</div>

  const currentStepIdx = statusSteps.indexOf(transfer.status)
  const cs = transfer.clinical_summary
  const cr = transfer.compliance_record

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/dashboard" className="p-2 rounded-lg hover:bg-slate-100"><ArrowLeft className="w-4 h-4 text-slate-500" /></Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900">{transfer.transfer_number}</h1>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${urgencyColors[transfer.urgency]}`}>{transfer.urgency}</span>
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[transfer.status]}`}>{transfer.status?.replace(/_/g, ' ')}</span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">{transfer.reason_for_transfer}</p>
        </div>
        {transfer.status === 'PENDING_REVIEW' && (
          <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-xs font-medium border border-blue-200 flex items-center gap-1.5">
            <Phone className="w-3.5 h-3.5" /> Scroll down to Call Center → call a facility to accept
          </div>
        )}
        {/* Auto-dispatch: no manual advance button — TRANSPORT_DISPATCHED triggers automatically when EMTALA completes */}
        {transfer.status === 'ACCEPTED' && cr && !cr.all_checks_passed && (
          <div className="px-3 py-1.5 bg-amber-50 text-amber-700 rounded-lg text-xs font-medium border border-amber-200 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" /> Complete EMTALA checklist to auto-dispatch transport
          </div>
        )}
        {transfer.status === 'TRANSPORT_DISPATCHED' && (
          <div className="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-bold border border-emerald-300 flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" /> Transport Dispatched — EMTALA Complete
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <div className="flex items-center justify-between">
          {statusSteps.map((step, i) => (
            <div key={step} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                i < currentStepIdx ? 'bg-emerald-500 text-white' : i === currentStepIdx ? 'bg-primary-600 text-white' : 'bg-slate-200 text-slate-400'
              }`}>
                {i < currentStepIdx ? '✓' : i + 1}
              </div>
              <span className={`ml-2 text-xs font-medium hidden lg:block ${i <= currentStepIdx ? 'text-slate-900' : 'text-slate-400'}`}>
                {step.replace(/_/g, ' ')}
              </span>
              {i < statusSteps.length - 1 && <div className={`w-8 h-0.5 mx-2 ${i < currentStepIdx ? 'bg-emerald-500' : 'bg-slate-200'}`} />}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Patient + SBAR */}
        <div className="col-span-2 space-y-6">
          {/* Patient Info */}
          {transfer.patient && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" /> Patient Information
              </h2>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><span className="text-slate-500">Name:</span> <span className="font-medium">{transfer.patient.first_name} {transfer.patient.last_name}</span></div>
                <div><span className="text-slate-500">Age/Gender:</span> <span className="font-medium">{transfer.patient.age}{transfer.patient.gender}</span></div>
                <div><span className="text-slate-500">MRN:</span> <span className="font-medium">{transfer.patient.mrn}</span></div>
                <div><span className="text-slate-500">Insurance:</span> <span className="font-medium">{transfer.patient.insurance_provider}</span></div>
                <div><span className="text-slate-500">Code Status:</span> <span className="font-medium">{transfer.patient.code_status}</span></div>
                <div><span className="text-slate-500">Language:</span> <span className="font-medium">{transfer.patient.primary_language}</span></div>
              </div>
            </div>
          )}

          {/* SBAR */}
          {cs && (
            <div className={`bg-white rounded-xl border p-5 ${cs.human_verified ? 'border-emerald-300' : 'border-amber-300'}`}>
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" /> SBAR Clinical Summary
                {cs.human_verified ? (
                  <span className="text-[10px] px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full font-medium flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Clinician Verified</span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">Pending Review</span>
                )}
                {cs.edited_by_human && <span className="text-[10px] px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">Edited</span>}
              </h2>
              {[
                { key: 'situation', label: 'Situation', color: 'border-blue-400' },
                { key: 'background', label: 'Background', color: 'border-emerald-400' },
                { key: 'assessment', label: 'Assessment', color: 'border-amber-400' },
                { key: 'recommendation', label: 'Recommendation', color: 'border-rose-400' },
              ].map(({ key, label, color }) => (
                <div key={key} className={`mb-3 pl-3 border-l-2 ${color}`}>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">{label}</p>
                  {sbarEditing ? (
                    <textarea
                      className="w-full text-sm text-slate-700 mt-1 p-2 border border-slate-200 rounded-lg resize-y min-h-[60px] focus:outline-none focus:ring-2 focus:ring-primary-300"
                      value={sbarDraft[key] ?? cs[key]}
                      onChange={e => setSbarDraft(prev => ({ ...prev, [key]: e.target.value }))}
                    />
                  ) : (
                    <p className="text-sm text-slate-700 whitespace-pre-wrap mt-0.5">{cs[key]}</p>
                  )}
                </div>
              ))}
              {/* Action buttons */}
              <div className="flex gap-2 mt-3">
                {!cs.human_verified && !sbarEditing && (
                  <>
                    <button
                      onClick={async () => {
                        setSbarSaving(true)
                        try {
                          await reviewSBAR(cs.id, { approved: true })
                          await load()
                        } catch (e) { console.error('SBAR approve failed:', e) }
                        setSbarSaving(false)
                      }}
                      disabled={sbarSaving}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" /> {sbarSaving ? 'Approving...' : 'Verify & Approve'}
                    </button>
                    <button
                      onClick={() => { setSbarEditing(true); setSbarDraft({}) }}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-200 transition-colors"
                    >
                      <Pencil className="w-3.5 h-3.5" /> Edit
                    </button>
                  </>
                )}
                {sbarEditing && (
                  <>
                    <button
                      onClick={async () => {
                        setSbarSaving(true)
                        try {
                          await reviewSBAR(cs.id, { ...sbarDraft, approved: true })
                          setSbarEditing(false)
                          setSbarDraft({})
                          await load()
                        } catch (e) { console.error('SBAR save failed:', e) }
                        setSbarSaving(false)
                      }}
                      disabled={sbarSaving}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" /> {sbarSaving ? 'Saving...' : 'Save & Approve'}
                    </button>
                    <button
                      onClick={() => { setSbarEditing(false); setSbarDraft({}) }}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-200 transition-colors"
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Facility Matches */}
          {transfer.facility_matches?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4 text-slate-400" /> Facility Matches
              </h2>
              <div className="space-y-2">
                {transfer.facility_matches.map((m: any) => (
                  <div key={m.facility_id} className={`p-3 rounded-lg border ${m.status === 'ACCEPTED' ? 'border-emerald-300 bg-emerald-50' : m.status === 'DECLINED' ? 'border-rose-200 bg-rose-50' : 'border-slate-200'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-slate-900">#{m.rank} {m.facility_name}</p>
                        <p className="text-xs text-slate-500">{m.facility_city}, {m.facility_state} · {m.distance_miles} mi · ~{m.estimated_transport_min} min</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-primary-600">{m.overall_score}</p>
                        <p className={`text-xs font-medium ${m.status === 'ACCEPTED' ? 'text-emerald-600' : m.status === 'DECLINED' ? 'text-rose-600' : 'text-slate-400'}`}>
                          {m.status}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timeline */}
          {transfer.timeline?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" /> Timeline
              </h2>
              <div className="space-y-3">
                {transfer.timeline.map((t: any) => (
                  <div key={t.id} className="flex gap-3">
                    <div className="w-2 h-2 rounded-full bg-primary-400 mt-1.5 shrink-0" />
                    <div>
                      <p className="text-sm text-slate-700">{t.event_description}</p>
                      <p className="text-xs text-slate-400">{t.created_at ? new Date(t.created_at).toLocaleString() : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Compliance + Transport */}
        <div className="space-y-6">
          {/* Compliance Checklist */}
          {cr && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-400" /> EMTALA Compliance
              </h2>
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file && pendingDocType) {
                    handleDocUpload(pendingDocType, file)
                  }
                  e.target.value = ''
                  setPendingDocType(null)
                }}
              />
              <div className="space-y-2">
                {[
                  { field: 'mse_completed', label: 'Medical Screening Exam', locked: true, hint: 'Pre-verified from EHR', docType: null },
                  { field: 'stabilization_attempted', label: 'Stabilization Documented', locked: true, hint: 'Pre-verified from EHR', docType: null },
                  { field: 'md_certification_signed', label: 'MD Certification Signed', locked: false, docType: 'MD_CERTIFICATION' },
                  { field: 'consent_obtained', label: 'Patient Consent', locked: false, docType: 'CONSENT_FORM' },
                  { field: 'receiving_facility_confirmed', label: 'Receiving Facility Confirmed', locked: true, hint: 'Auto-confirmed on acceptance', docType: null },
                  { field: 'transport_appropriate', label: 'Transport Appropriate', locked: false, docType: 'TRANSPORT_ORDER' },
                  { field: 'records_sent', label: 'Records Sent', locked: false, docType: 'RECORDS_PACKET' },
                ].map(({ field, label, locked, hint, docType }) => {
                  const fieldDocs = docType ? complianceDocs.filter((d: any) => d.document_type === docType) : []
                  return (
                    <div key={field} className="rounded-lg border border-slate-100 p-2">
                      <button
                        onClick={() => !locked && handleComplianceToggle(field, cr[field])}
                        className={`w-full flex items-center gap-3 transition-colors text-left ${
                          locked ? 'cursor-default' : 'hover:bg-slate-50 cursor-pointer'
                        }`}
                      >
                        {(cr[field] || locked) ? (
                          <CheckCircle className="w-5 h-5 shrink-0 text-emerald-500" />
                        ) : (
                          <div className="w-5 h-5 rounded-full border-2 border-slate-300 shrink-0" />
                        )}
                        <div className="flex flex-col flex-1">
                          <span className={`text-sm ${(cr[field] || locked) ? 'text-slate-900' : 'text-slate-500'}`}>{label}</span>
                          {locked && hint && <span className="text-[10px] text-slate-400">{hint}</span>}
                        </div>
                      </button>
                      {/* Document upload area */}
                      {docType && (
                        <div className="ml-8 mt-1.5">
                          {fieldDocs.length > 0 ? (
                            <div className="space-y-1">
                              {fieldDocs.map((doc: any) => (
                                <div key={doc.id} className="flex items-center gap-2 text-xs bg-slate-50 rounded px-2 py-1">
                                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                                  <span className="flex-1 truncate text-slate-700">{doc.file_name}</span>
                                  <span className="text-slate-400">{(doc.file_size_bytes / 1024).toFixed(0)}KB</span>
                                  <a
                                    href={getDocumentDownloadUrl(id!, doc.id)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-0.5 hover:text-primary-600 text-slate-400"
                                    title="Download"
                                  >
                                    <Download className="w-3.5 h-3.5" />
                                  </a>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleDocDelete(doc.id) }}
                                    className="p-0.5 hover:text-rose-600 text-slate-400"
                                    title="Delete"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : null}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setPendingDocType(docType)
                              fileInputRef.current?.click()
                            }}
                            disabled={uploading === docType}
                            className="mt-1 flex items-center gap-1.5 text-[11px] text-primary-600 hover:text-primary-700 font-medium"
                          >
                            <Upload className="w-3.5 h-3.5" />
                            {uploading === docType ? 'Uploading...' : fieldDocs.length > 0 ? 'Upload another' : 'Upload document'}
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
              <div className={`mt-3 p-2 rounded-lg text-center text-xs font-medium ${
                cr.all_checks_passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
              }`}>
                {cr.all_checks_passed ? '✓ All checks passed — ready for transport' : '⚠ Incomplete — cannot dispatch transport'}
              </div>
            </div>
          )}

          {/* Call Center */}
          <CallPanel
            transferId={id!}
            facilityMatches={transfer.facility_matches || []}
            transferStatus={transfer.status}
            onCallOutcome={load}
          />

          {/* Transfer Info */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Transfer Info</h2>
            <div className="space-y-2 text-sm">
              {transfer.sending_facility && (
                <div><span className="text-slate-500">From:</span> <span className="font-medium">{transfer.sending_facility.name}</span></div>
              )}
              {transfer.receiving_facility && (
                <div><span className="text-slate-500">To:</span> <span className="font-medium">{transfer.receiving_facility.name}</span></div>
              )}
              {transfer.requested_specialty && (
                <div><span className="text-slate-500">Specialty:</span> <span className="font-medium">{transfer.requested_specialty.replace(/_/g, ' ')}</span></div>
              )}
              {transfer.initiated_at && (
                <div><span className="text-slate-500">Initiated:</span> <span className="font-medium">{new Date(transfer.initiated_at).toLocaleString()}</span></div>
              )}
              {transfer.accepted_at && (
                <div><span className="text-slate-500">Accepted:</span> <span className="font-medium">{new Date(transfer.accepted_at).toLocaleString()}</span></div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
