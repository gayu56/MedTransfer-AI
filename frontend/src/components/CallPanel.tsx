import { useState, useEffect } from 'react'
import { Phone, PhoneCall, PhoneOff, PhoneMissed, FileText, Clock, CheckCircle, XCircle, Loader2, Copy, ChevronDown, ChevronUp, MessageSquare, Zap, AlertTriangle, ShieldCheck, UserCheck } from 'lucide-react'
import { fetchCallsForTransfer, createCallLog, updateCallLog, generateCallScript, runAutoCall, confirmAcceptance } from '../services/api'

interface CallPanelProps {
  transferId: string
  facilityMatches: any[]
  transferStatus: string
  onCallOutcome?: () => void // refresh parent
}

const outcomeConfig: Record<string, { label: string; color: string; icon: any }> = {
  PENDING: { label: 'In Progress', color: 'text-amber-600 bg-amber-50', icon: PhoneCall },
  CONNECTED: { label: 'Connected', color: 'text-blue-600 bg-blue-50', icon: PhoneCall },
  ACCEPTED: { label: 'Accepted', color: 'text-emerald-600 bg-emerald-50', icon: CheckCircle },
  DECLINED: { label: 'Declined', color: 'text-rose-600 bg-rose-50', icon: XCircle },
  NO_ANSWER: { label: 'No Answer', color: 'text-slate-600 bg-slate-100', icon: PhoneMissed },
  VOICEMAIL: { label: 'Voicemail', color: 'text-purple-600 bg-purple-50', icon: PhoneOff },
  CALLBACK_REQUESTED: { label: 'Callback Requested', color: 'text-amber-600 bg-amber-50', icon: Clock },
  TRANSFERRED_TO_MD: { label: 'Transferred to MD', color: 'text-indigo-600 bg-indigo-50', icon: Phone },
  PENDING_CONFIRMATION: { label: 'Awaiting Confirmation', color: 'text-orange-600 bg-orange-50', icon: AlertTriangle },
}

export default function CallPanel({ transferId, facilityMatches, transferStatus, onCallOutcome }: CallPanelProps) {
  const [calls, setCalls] = useState<any[]>([])
  const [script, setScript] = useState<any>(null)
  const [scriptLoading, setScriptLoading] = useState(false)
  const [activeCall, setActiveCall] = useState<any>(null)
  const [showScript, setShowScript] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [callNotes, setCallNotes] = useState('')
  const [contactName, setContactName] = useState('')
  const [contactRole, setContactRole] = useState('')
  const [declineReason, setDeclineReason] = useState('')
  const [copied, setCopied] = useState(false)

  // Auto-call state
  const [autoCallRunning, setAutoCallRunning] = useState(false)
  const [autoCallResults, setAutoCallResults] = useState<any>(null)
  const [pendingCallId, setPendingCallId] = useState<string | null>(null)
  const [pendingFacility, setPendingFacility] = useState<string | null>(null)
  const [acceptingPhysician, setAcceptingPhysician] = useState('')
  const [confirmNotes, setConfirmNotes] = useState('')

  useEffect(() => {
    loadCalls()
  }, [transferId])

  const loadCalls = async () => {
    try {
      const res = await fetchCallsForTransfer(transferId)
      setCalls(res)
    } catch (e) { console.error(e) }
  }

  const handleGenerateScript = async (facilityId: string) => {
    setScriptLoading(true)
    try {
      const res = await generateCallScript({ transfer_id: transferId, facility_id: facilityId })
      setScript(res)
      setShowScript(true)
    } catch (e) { console.error(e) }
    finally { setScriptLoading(false) }
  }

  const handleStartCall = async (facilityId: string, facilityName: string, phone: string | null) => {
    try {
      const res = await createCallLog({
        transfer_id: transferId,
        facility_id: facilityId,
        phone_number: phone,
        notes: `Calling ${facilityName}`,
      })
      setActiveCall(res)
      setCallNotes('')
      setContactName('')
      setContactRole('')
      setDeclineReason('')
      loadCalls()
    } catch (e) { console.error(e) }
  }

  const handleEndCall = async (outcome: string) => {
    if (!activeCall) return
    try {
      await updateCallLog(activeCall.id, {
        outcome,
        notes: callNotes || undefined,
        contact_name: contactName || undefined,
        contact_role: contactRole || undefined,
        decline_reason: outcome === 'DECLINED' ? declineReason || 'No reason provided' : undefined,
      })
      setActiveCall(null)
      setScript(null)
      setShowScript(false)
      loadCalls()
      onCallOutcome?.()
    } catch (e) { console.error(e) }
  }

  const handleAutoCall = async () => {
    setAutoCallRunning(true)
    setAutoCallResults(null)
    setPendingCallId(null)
    setPendingFacility(null)
    try {
      const res = await runAutoCall(transferId)
      setAutoCallResults(res)
      if (res.needs_confirmation && res.pending_call_id) {
        setPendingCallId(res.pending_call_id)
        setPendingFacility(res.pending_facility)
      }
      loadCalls()
    } catch (e) { console.error(e) }
    finally { setAutoCallRunning(false) }
  }

  const handleConfirmAcceptance = async () => {
    if (!pendingCallId || !acceptingPhysician.trim()) return
    try {
      await confirmAcceptance({
        call_id: pendingCallId,
        accepting_physician: acceptingPhysician.trim(),
        notes: confirmNotes || undefined,
      })
      setPendingCallId(null)
      setPendingFacility(null)
      setAcceptingPhysician('')
      setConfirmNotes('')
      setAutoCallResults(null)
      loadCalls()
      onCallOutcome?.()
    } catch (e) { console.error(e) }
  }

  const copyScript = () => {
    if (script?.script) {
      navigator.clipboard.writeText(script.script)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const callableFacilities = facilityMatches?.filter(
    (m: any) => m.status !== 'ACCEPTED' && m.status !== 'DECLINED'
  ) || []

  const isTransferActive = ['INITIATED', 'PENDING_REVIEW', 'RE_ROUTING'].includes(transferStatus)

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
        <Phone className="w-4 h-4 text-slate-400" /> Call Center
        {calls.length > 0 && (
          <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">{calls.length} call{calls.length !== 1 ? 's' : ''}</span>
        )}
      </h2>

      {/* Active Call */}
      {activeCall && (
        <div className="mb-4 p-4 rounded-lg border-2 border-blue-300 bg-blue-50">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm font-bold text-blue-900">Call in Progress — {activeCall.facility_name}</span>
          </div>

          {/* Contact info inputs */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <input
              type="text"
              placeholder="Contact name..."
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              className="px-3 py-1.5 text-sm border border-blue-200 rounded-lg bg-white"
            />
            <input
              type="text"
              placeholder="Role (e.g. Charge Nurse)..."
              value={contactRole}
              onChange={(e) => setContactRole(e.target.value)}
              className="px-3 py-1.5 text-sm border border-blue-200 rounded-lg bg-white"
            />
          </div>

          <textarea
            placeholder="Call notes..."
            value={callNotes}
            onChange={(e) => setCallNotes(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-blue-200 rounded-lg bg-white mb-3 resize-none"
            rows={2}
          />

          {/* Outcome buttons */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <button onClick={() => handleEndCall('ACCEPTED')} className="flex-1 px-3 py-2 bg-emerald-600 text-white text-xs font-bold rounded-lg hover:bg-emerald-700 flex items-center justify-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" /> Accepted
              </button>
              <button onClick={() => handleEndCall('DECLINED')} className="flex-1 px-3 py-2 bg-rose-600 text-white text-xs font-bold rounded-lg hover:bg-rose-700 flex items-center justify-center gap-1.5">
                <XCircle className="w-3.5 h-3.5" /> Declined
              </button>
            </div>
            {/* Show decline reason input when about to decline */}
            <input
              type="text"
              placeholder="Decline reason (if declining)..."
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-blue-200 rounded-lg bg-white"
            />
            <div className="flex gap-2">
              <button onClick={() => handleEndCall('NO_ANSWER')} className="flex-1 px-2 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:bg-slate-300">
                No Answer
              </button>
              <button onClick={() => handleEndCall('VOICEMAIL')} className="flex-1 px-2 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:bg-slate-300">
                Voicemail
              </button>
              <button onClick={() => handleEndCall('CALLBACK_REQUESTED')} className="flex-1 px-2 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:bg-slate-300">
                Callback
              </button>
              <button onClick={() => handleEndCall('TRANSFERRED_TO_MD')} className="flex-1 px-2 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded-lg hover:bg-slate-300">
                To MD
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Call Script */}
      {showScript && script && (
        <div className="mb-4 p-4 rounded-lg border border-indigo-200 bg-indigo-50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-bold text-indigo-900 flex items-center gap-1.5">
              <FileText className="w-4 h-4" /> Call Script — {script.facility_name}
            </span>
            <div className="flex gap-2">
              <button onClick={copyScript} className="px-2 py-1 text-xs bg-indigo-200 text-indigo-800 rounded hover:bg-indigo-300 flex items-center gap-1">
                <Copy className="w-3 h-3" /> {copied ? 'Copied!' : 'Copy'}
              </button>
              <button onClick={() => setShowScript(false)} className="px-2 py-1 text-xs bg-indigo-200 text-indigo-800 rounded hover:bg-indigo-300">
                Close
              </button>
            </div>
          </div>

          {script.facility_phone && (
            <div className="mb-2 text-xs text-indigo-700">
              📞 <a href={`tel:${script.facility_phone}`} className="underline font-medium">{script.facility_phone}</a>
            </div>
          )}

          <pre className="text-xs text-indigo-900 whitespace-pre-wrap leading-relaxed bg-white rounded-lg p-3 border border-indigo-100 max-h-64 overflow-y-auto">
            {script.script}
          </pre>

          {script.key_points?.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-bold text-indigo-800 mb-1">Key Points:</p>
              <ul className="text-xs text-indigo-700 space-y-0.5">
                {script.key_points.map((p: string, i: number) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-indigo-400 shrink-0">•</span> {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {script.questions_to_ask?.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-bold text-indigo-800 mb-1">Questions to Ask:</p>
              <ul className="text-xs text-indigo-700 space-y-0.5">
                {script.questions_to_ask.map((q: string, i: number) => (
                  <li key={i} className="flex gap-1.5">
                    <MessageSquare className="w-3 h-3 text-indigo-400 shrink-0 mt-0.5" /> {q}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Auto-Call Button */}
      {isTransferActive && !activeCall && !pendingCallId && callableFacilities.length > 0 && (
        <div className="mb-4">
          <button
            onClick={handleAutoCall}
            disabled={autoCallRunning}
            className="w-full px-4 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg text-sm font-bold hover:from-indigo-700 hover:to-purple-700 flex items-center justify-center gap-2 disabled:opacity-60 transition-all"
          >
            {autoCallRunning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> AI is calling facilities...</>
            ) : (
              <><Zap className="w-4 h-4" /> Auto-Call Facilities (AI-Simulated)</>
            )}
          </button>
          <p className="text-[10px] text-slate-400 mt-1 text-center">
            AI simulates calls in rank order. You must confirm any acceptance.
          </p>
        </div>
      )}

      {/* Auto-Call Results */}
      {autoCallResults && autoCallResults.results?.length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Zap className="w-3 h-3" /> Auto-Call Results
          </p>
          {autoCallResults.results.map((r: any, i: number) => {
            const cfg = outcomeConfig[r.outcome] || outcomeConfig.PENDING
            const Icon = cfg.icon
            return (
              <div key={i} className={`p-3 rounded-lg border ${r.outcome === 'PENDING_CONFIRMATION' ? 'border-orange-300 bg-orange-50' : r.outcome === 'DECLINED' ? 'border-rose-200 bg-rose-50' : 'border-slate-200'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-slate-900">#{r.rank} {r.facility_name}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${cfg.color}`}>
                    <Icon className="w-3 h-3 inline mr-1" />{cfg.label}
                  </span>
                </div>
                {r.notes && <p className="text-[10px] text-slate-600">{r.notes}</p>}
                {r.decline_reason && <p className="text-[10px] text-rose-600">Reason: {r.decline_reason}</p>}
                {r.is_simulated && <p className="text-[9px] text-slate-400 mt-0.5 italic">AI-simulated call</p>}
              </div>
            )
          })}
        </div>
      )}

      {/* Confirmation Panel — requires accepting physician */}
      {pendingCallId && pendingFacility && (
        <div className="mb-4 p-4 rounded-lg border-2 border-orange-400 bg-orange-50">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-orange-600" />
            <div>
              <p className="text-sm font-bold text-orange-900">Confirm Acceptance — {pendingFacility}</p>
              <p className="text-[10px] text-orange-700">EMTALA requires a named clinician who agreed to accept</p>
            </div>
          </div>

          <div className="space-y-2">
            <div>
              <label className="text-[10px] font-bold text-orange-800 uppercase tracking-wider">Accepting Physician *</label>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-sm text-orange-700 font-medium">Dr.</span>
                <input
                  type="text"
                  placeholder="Last name of accepting physician..."
                  value={acceptingPhysician}
                  onChange={(e) => setAcceptingPhysician(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm border-2 border-orange-300 rounded-lg bg-white focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none"
                  autoFocus
                />
              </div>
            </div>
            <textarea
              placeholder="Additional notes (optional)..."
              value={confirmNotes}
              onChange={(e) => setConfirmNotes(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-orange-200 rounded-lg bg-white resize-none"
              rows={2}
            />
            <button
              onClick={handleConfirmAcceptance}
              disabled={!acceptingPhysician.trim()}
              className="w-full px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-bold hover:bg-emerald-700 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <UserCheck className="w-4 h-4" /> Confirm Acceptance (EMTALA Compliant)
            </button>
          </div>
        </div>
      )}

      {/* Callable Facilities */}
      {isTransferActive && !activeCall && callableFacilities.length > 0 && (
        <div className="space-y-2 mb-4">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Contact Facilities</p>
          {callableFacilities.map((m: any) => (
            <div key={m.facility_id} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors">
              <div>
                <p className="text-sm font-medium text-slate-900">#{m.rank} {m.facility_name}</p>
                <p className="text-xs text-slate-500">{m.facility_city}, {m.facility_state} · Score: {m.overall_score}</p>
              </div>
              <div className="flex gap-1.5">
                <button
                  onClick={() => handleGenerateScript(m.facility_id)}
                  disabled={scriptLoading}
                  className="px-2.5 py-1.5 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 flex items-center gap-1 disabled:opacity-50"
                >
                  {scriptLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                  Script
                </button>
                <button
                  onClick={() => handleStartCall(m.facility_id, m.facility_name, null)}
                  className="px-2.5 py-1.5 text-xs font-medium bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200 flex items-center gap-1"
                >
                  <Phone className="w-3 h-3" /> Call
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No facilities to call */}
      {isTransferActive && !activeCall && callableFacilities.length === 0 && (
        <p className="text-xs text-slate-400 text-center py-3">All facilities have been contacted.</p>
      )}

      {!isTransferActive && !activeCall && (
        <p className="text-xs text-slate-400 text-center py-3">Transfer is {transferStatus?.replace(/_/g, ' ').toLowerCase()} — calls no longer needed.</p>
      )}

      {/* Call History */}
      {calls.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-700 w-full"
          >
            {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            Call History ({calls.length})
          </button>

          {showHistory && (
            <div className="mt-2 space-y-2">
              {calls.map((c: any) => {
                const config = outcomeConfig[c.outcome] || outcomeConfig.PENDING
                const Icon = config.icon
                return (
                  <div key={c.id} className={`p-2.5 rounded-lg border border-slate-100 ${c.outcome === 'ACCEPTED' ? 'bg-emerald-50 border-emerald-200' : c.outcome === 'DECLINED' ? 'bg-rose-50 border-rose-200' : ''}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-3.5 h-3.5 ${config.color.split(' ')[0]}`} />
                        <span className="text-xs font-medium text-slate-900">{c.facility_name}</span>
                        {c.contact_name && <span className="text-xs text-slate-500">— {c.contact_name}</span>}
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${config.color}`}>
                        {config.label}
                      </span>
                    </div>
                    {c.notes && <p className="text-xs text-slate-600 mt-1">{c.notes}</p>}
                    {c.decline_reason && <p className="text-xs text-rose-600 mt-1">Reason: {c.decline_reason}</p>}
                    <p className="text-[10px] text-slate-400 mt-1">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</p>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
