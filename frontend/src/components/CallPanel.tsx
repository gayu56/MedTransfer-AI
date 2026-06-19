import { useState, useEffect } from 'react'
import { Phone, PhoneCall, PhoneOff, PhoneMissed, Clock, CheckCircle, XCircle, Loader2, ChevronDown, ChevronUp, AlertTriangle, Send, Radio, Bot, MessageSquare, UserCheck, Stethoscope, BedDouble } from 'lucide-react'
import { fetchCallsForTransfer, runAutoCall, runAICall, confirmAcceptance } from '../services/api'
import WarRoomCallView from './WarRoomCallView'

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
  PROPOSED_ACCEPT: { label: 'Verbal Accept — Confirm', color: 'text-orange-600 bg-orange-50', icon: UserCheck },
  PENDING_CONFIRMATION: { label: 'Awaiting Confirmation', color: 'text-orange-600 bg-orange-50', icon: AlertTriangle },
  CANCELLED: { label: 'Cancelled', color: 'text-slate-500 bg-slate-100', icon: XCircle },
  SUPERSEDED: { label: 'Superseded', color: 'text-amber-600 bg-amber-50', icon: Clock },
}

function Transcript({ turns }: { turns: { speaker: string; text: string }[] }) {
  if (!turns?.length) return null
  return (
    <div className="mt-2 space-y-2 bg-slate-900 rounded-lg p-3">
      {turns.map((t, i) => {
        const isAI = t.speaker === 'AI'
        return (
          <div key={i} className={`flex gap-2 ${isAI ? '' : 'flex-row-reverse'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${isAI ? 'bg-primary-600' : 'bg-slate-600'}`}>
              {isAI ? <Bot className="w-3.5 h-3.5 text-white" /> : <Stethoscope className="w-3.5 h-3.5 text-white" />}
            </div>
            <div className={`max-w-[80%] px-3 py-1.5 rounded-lg text-[11px] leading-relaxed ${isAI ? 'bg-primary-600/20 text-primary-100' : 'bg-slate-700 text-slate-100'}`}>
              <span className={`block text-[9px] font-bold uppercase tracking-wider mb-0.5 ${isAI ? 'text-primary-300' : 'text-slate-400'}`}>{isAI ? 'AI Coordinator' : 'Hospital'}</span>
              {t.text}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function CallPanel({ transferId, facilityMatches, transferStatus, onCallOutcome }: CallPanelProps) {
  const [calls, setCalls] = useState<any[]>([])
  const [showHistory, setShowHistory] = useState(false)

  // Broadcast state
  const [broadcastRunning, setBroadcastRunning] = useState(false)
  const [broadcastResults, setBroadcastResults] = useState<any>(null)

  // Phase 1 AI audio-agent call state
  const [aiCallRunning, setAiCallRunning] = useState(false)
  const [aiResults, setAiResults] = useState<any>(null)
  const [openTranscript, setOpenTranscript] = useState<number | null>(null)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [physicianInput, setPhysicianInput] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState('')
  const [showLiveCall, setShowLiveCall] = useState(false)

  useEffect(() => {
    loadCalls()
  }, [transferId])

  const loadCalls = async () => {
    try {
      const res = await fetchCallsForTransfer(transferId)
      setCalls(res)
    } catch (e) { console.error(e) }
  }

  const handleBroadcast = async () => {
    setBroadcastRunning(true)
    setBroadcastResults(null)
    try {
      const res = await runAutoCall(transferId)
      setBroadcastResults(res)
      loadCalls()
      onCallOutcome?.() // refresh parent to update status if accepted
    } catch (e) { console.error(e) }
    finally { setBroadcastRunning(false) }
  }

  const handleAICall = async () => {
    setAiCallRunning(true)
    setAiResults(null)
    setConfirmingId(null)
    try {
      const res = await runAICall(transferId)
      setAiResults(res)
      // Auto-expand the first proposed acceptance transcript
      const firstProposed = res.results?.findIndex((r: any) => r.proposed)
      if (firstProposed >= 0) setOpenTranscript(firstProposed)
      // Play the calls out live (audio + streaming transcript) before showing the board
      if (res.results?.length) setShowLiveCall(true)
      loadCalls()
    } catch (e: any) {
      setAiResults({ error: e.message || 'AI call failed' })
    }
    finally { setAiCallRunning(false) }
  }

  const startConfirm = (result: any) => {
    setConfirmingId(result.call_id)
    setPhysicianInput(result.accepting_physician || '')
    setConfirmError('')
  }

  const handleConfirm = async (result: any) => {
    if (!physicianInput.trim()) {
      setConfirmError('Accepting physician name is required.')
      return
    }
    setConfirming(true)
    setConfirmError('')
    try {
      const physician = physicianInput.trim()
      await confirmAcceptance({
        call_id: result.call_id,
        accepting_physician: physician,
        contact_name: result.contact_name,
        contact_role: result.contact_role,
        notes: `Clinician-confirmed AI call acceptance — ${result.bed_type || 'bed TBD'}`,
      })
      setConfirmingId(null)
      // Update the local results board so the confirmed card locks and other
      // proposed acceptances are no longer actionable (transfer is now ACCEPTED).
      setAiResults((prev: any) => {
        if (!prev?.results) return prev
        const results = prev.results.map((r: any) =>
          r.call_id === result.call_id
            ? { ...r, outcome: 'ACCEPTED', proposed: false, accepting_physician: physician, confirmed: true }
            : r.proposed
              ? { ...r, proposed: false, outcome: 'SUPERSEDED' }
              : r
        )
        return { ...prev, results, has_proposed_acceptance: false, proposed_count: 0, confirmed_facility: result.facility_name }
      })
      loadCalls()
      onCallOutcome?.() // refresh parent — transfer now ACCEPTED
    } catch (e: any) {
      setConfirmError(e.message || 'Confirmation failed.')
    }
    finally { setConfirming(false) }
  }

  const callableFacilities = facilityMatches?.filter(
    (m: any) => !['ACCEPTED', 'DECLINED', 'CANCELLED'].includes(m.status)
  ) || []

  const isTransferActive = ['INITIATED', 'PENDING_REVIEW', 'RE_ROUTING'].includes(transferStatus)

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      {showLiveCall && aiResults?.results?.length > 0 && (
        <WarRoomCallView results={aiResults.results} onComplete={() => setShowLiveCall(false)} />
      )}
      <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
        <Phone className="w-4 h-4 text-slate-400" /> Call Center
        {calls.length > 0 && (
          <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">{calls.length} call{calls.length !== 1 ? 's' : ''}</span>
        )}
      </h2>

      {/* AI Audio Agent Call Button (Phase 1) */}
      {isTransferActive && !aiResults && callableFacilities.length > 0 && (
        <div className="mb-4">
          <button
            onClick={handleAICall}
            disabled={aiCallRunning}
            className="w-full px-4 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg text-sm font-bold hover:from-primary-700 hover:to-primary-800 flex items-center justify-center gap-2 disabled:opacity-60 transition-all shadow-sm shadow-primary-600/30"
          >
            {aiCallRunning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> AI calling {callableFacilities.length} facilities...</>
            ) : (
              <><Bot className="w-4 h-4" /> AI Call Hospitals ({callableFacilities.length})</>
            )}
          </button>
          <p className="text-[10px] text-slate-400 mt-1 text-center">
            AI calls all facilities simultaneously. Watch every call live in the war room.
            <span className="text-orange-500 font-medium"> You confirm the final decision.</span>
          </p>
        </div>
      )}

      {/* AI Call Results — Live Conversation Board */}
      {aiResults && (
        <div className="mb-4">
          {aiResults.error ? (
            <div className="p-3 rounded-lg border-2 border-rose-300 bg-rose-50">
              <p className="text-sm font-bold text-rose-900 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" /> AI Call Failed</p>
              <p className="text-[11px] text-rose-700 mt-0.5">{aiResults.error}</p>
            </div>
          ) : (
            <>
              {/* Summary banner */}
              {aiResults.confirmed_facility ? (
                <div className="mb-3 p-3 rounded-lg border-2 border-emerald-400 bg-emerald-50">
                  <p className="text-sm font-bold text-emerald-900 flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4" /> Transfer Locked — {aiResults.confirmed_facility}
                  </p>
                  <p className="text-[11px] text-emerald-700 mt-0.5">
                    Acceptance confirmed by clinician. Complete the EMTALA checklist to dispatch transport.
                  </p>
                </div>
              ) : aiResults.has_proposed_acceptance ? (
                <div className="mb-3 p-3 rounded-lg border-2 border-orange-300 bg-orange-50">
                  <p className="text-sm font-bold text-orange-900 flex items-center gap-1.5">
                    <UserCheck className="w-4 h-4" /> {aiResults.proposed_count} Verbal Acceptance{aiResults.proposed_count !== 1 ? 's' : ''} — Confirm to Lock
                  </p>
                  <p className="text-[11px] text-orange-700 mt-0.5">
                    The AI secured verbal acceptance(s). Review the conversation and confirm with the accepting physician to finalize.
                  </p>
                </div>
              ) : (
                <div className="mb-3 p-3 rounded-lg border-2 border-rose-300 bg-rose-50">
                  <p className="text-sm font-bold text-rose-900 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" /> No Acceptances</p>
                  <p className="text-[11px] text-rose-700 mt-0.5">All facilities declined or did not answer. Consider expanding the search radius.</p>
                </div>
              )}

              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <Radio className="w-3 h-3" /> AI Call Results ({aiResults.call_count})
              </p>

              <div className="space-y-2">
                {aiResults.results.map((r: any, i: number) => {
                  const isProposed = r.proposed
                  const isConfirmed = r.confirmed || r.outcome === 'ACCEPTED'
                  const isDeclined = r.outcome === 'DECLINED'
                  const isOpen = openTranscript === i
                  const isConfirming = confirmingId === r.call_id
                  return (
                    <div key={i} className={`rounded-lg border ${isConfirmed ? 'border-emerald-300 bg-emerald-50' : isProposed ? 'border-orange-300 bg-orange-50' : isDeclined ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-slate-50'}`}>
                      <div className="p-3">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-xs font-semibold text-slate-900">#{r.rank} {r.facility_name}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                            isConfirmed ? 'text-emerald-700 bg-emerald-100' : isProposed ? 'text-orange-700 bg-orange-100' : isDeclined ? 'text-rose-700 bg-rose-100' : 'text-slate-600 bg-slate-200'
                          }`}>
                            {isConfirmed ? <CheckCircle className="w-3 h-3" /> : isProposed ? <UserCheck className="w-3 h-3" /> : isDeclined ? <XCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                            {isConfirmed ? 'CONFIRMED' : (r.outcome || '').replace(/_/g, ' ')}
                          </span>
                        </div>

                        {/* Accepted/proposed acceptance details */}
                        {(isProposed || isConfirmed) && (
                          <div className="flex flex-wrap gap-3 mt-1.5 mb-1">
                            {r.bed_type && <span className="text-[10px] text-slate-600 flex items-center gap-1"><BedDouble className="w-3 h-3 text-slate-400" /> {r.bed_type}</span>}
                            {r.accepting_physician && <span className="text-[10px] text-slate-600 flex items-center gap-1"><Stethoscope className="w-3 h-3 text-slate-400" /> {r.accepting_physician}</span>}
                            {r.contact_name && <span className="text-[10px] text-slate-500">Spoke with {r.contact_name}{r.contact_role ? ` (${r.contact_role})` : ''}</span>}
                          </div>
                        )}
                        {r.decline_reason && <p className="text-[10px] text-rose-600">Reason: {r.decline_reason}</p>}
                        {!isProposed && !isConfirmed && r.notes && <p className="text-[10px] text-slate-600">{r.notes}</p>}

                        {/* Transcript toggle */}
                        {r.transcript?.length > 0 && (
                          <button
                            onClick={() => setOpenTranscript(isOpen ? null : i)}
                            className="mt-1.5 flex items-center gap-1 text-[10px] font-medium text-primary-600 hover:text-primary-700"
                          >
                            <MessageSquare className="w-3 h-3" />
                            {isOpen ? 'Hide' : 'View'} conversation ({r.transcript.length} turns)
                            {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          </button>
                        )}
                        {isOpen && <Transcript turns={r.transcript} />}

                        {/* Confirmation gate for proposed acceptances */}
                        {isProposed && (
                          <div className="mt-2.5 pt-2.5 border-t border-orange-200">
                            {!isConfirming ? (
                              <button
                                onClick={() => startConfirm(r)}
                                className="w-full px-3 py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 flex items-center justify-center gap-1.5 transition-colors"
                              >
                                <CheckCircle className="w-3.5 h-3.5" /> Confirm Acceptance & Lock Transfer
                              </button>
                            ) : (
                              <div className="space-y-2">
                                <label className="block text-[10px] font-semibold text-slate-600">Accepting Physician (required for EMTALA)</label>
                                <input
                                  type="text"
                                  value={physicianInput}
                                  onChange={e => setPhysicianInput(e.target.value)}
                                  placeholder="Dr. Name"
                                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-400"
                                />
                                {confirmError && <p className="text-[10px] text-rose-600">{confirmError}</p>}
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => handleConfirm(r)}
                                    disabled={confirming}
                                    className="flex-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 disabled:opacity-60 flex items-center justify-center gap-1.5"
                                  >
                                    {confirming ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Confirming...</> : <><CheckCircle className="w-3.5 h-3.5" /> Confirm</>}
                                  </button>
                                  <button
                                    onClick={() => setConfirmingId(null)}
                                    disabled={confirming}
                                    className="px-3 py-1.5 bg-white border border-slate-300 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-50"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* Broadcast Button (legacy instant mode) */}
      {isTransferActive && !aiResults && !broadcastResults && callableFacilities.length > 0 && (
        <div className="mb-4">
          <button
            onClick={handleBroadcast}
            disabled={broadcastRunning}
            className="w-full px-4 py-2.5 bg-white border border-slate-300 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-50 flex items-center justify-center gap-2 disabled:opacity-60 transition-all"
          >
            {broadcastRunning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Broadcasting to {callableFacilities.length} facilities...</>
            ) : (
              <><Send className="w-3.5 h-3.5" /> Or instant broadcast (auto-accept) to all</>
            )}
          </button>
        </div>
      )}

      {/* Broadcast Results — Live Status Board */}
      {broadcastResults && broadcastResults.results?.length > 0 && (
        <div className="mb-4">
          {/* Accepted Banner */}
          {broadcastResults.accepted && (
            <div className="mb-3 p-3 rounded-lg border-2 border-emerald-400 bg-emerald-50">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="text-sm font-bold text-emerald-900">{broadcastResults.accepted_facility} Accepted!</p>
                  <p className="text-[10px] text-emerald-700">
                    Accepted by {broadcastResults.accepted_by} — Transfer locked in. Complete EMTALA checklist to dispatch transport.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* No one accepted */}
          {!broadcastResults.accepted && (
            <div className="mb-3 p-3 rounded-lg border-2 border-rose-300 bg-rose-50">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
                <div>
                  <p className="text-sm font-bold text-rose-900">No Facility Accepted</p>
                  <p className="text-[10px] text-rose-700">All facilities declined or did not respond. Consider expanding search radius or contacting manually.</p>
                </div>
              </div>
            </div>
          )}

          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-2">
            <Radio className="w-3 h-3" /> Broadcast Results ({broadcastResults.broadcast_count} facilities)
          </p>
          <div className="space-y-1.5">
            {broadcastResults.results.map((r: any, i: number) => {
              const isAccepted = r.outcome === 'ACCEPTED'
              const isDeclined = r.outcome === 'DECLINED'
              const isCancelled = r.outcome === 'CANCELLED'
              return (
                <div key={i} className={`p-3 rounded-lg border ${isAccepted ? 'border-emerald-300 bg-emerald-50' : isDeclined ? 'border-rose-200 bg-rose-50' : isCancelled ? 'border-slate-300 bg-slate-50 opacity-60' : 'border-slate-200 bg-slate-50'}`}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className={`text-xs font-semibold ${isCancelled ? 'text-slate-400 line-through' : 'text-slate-900'}`}>#{r.rank} {r.facility_name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                      isAccepted ? 'text-emerald-700 bg-emerald-100' : isDeclined ? 'text-rose-700 bg-rose-100' : isCancelled ? 'text-slate-500 bg-slate-200' : 'text-slate-600 bg-slate-200'
                    }`}>
                      {isAccepted ? <CheckCircle className="w-3 h-3" /> : isDeclined ? <XCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                      {r.outcome?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  {r.notes && <p className="text-[10px] text-slate-600">{r.notes}</p>}
                  {r.decline_reason && <p className="text-[10px] text-rose-600 mt-0.5">Reason: {r.decline_reason}</p>}
                  {r.contact_name && <p className="text-[10px] text-slate-500 mt-0.5">Contact: {r.contact_name}{r.contact_role ? ` (${r.contact_role})` : ''}</p>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Transfer already accepted/completed */}
      {!isTransferActive && (
        <p className="text-xs text-slate-400 text-center py-3">Transfer is {transferStatus?.replace(/_/g, ' ').toLowerCase()}.</p>
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
