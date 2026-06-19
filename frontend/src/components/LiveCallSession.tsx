import { useEffect, useRef, useState } from 'react'
import { Phone, PhoneOff, PhoneCall, Bot, Stethoscope, Volume2, VolumeX, SkipForward, CheckCircle, XCircle, UserCheck, Clock, BedDouble } from 'lucide-react'

interface Turn { speaker: string; text: string }
interface CallResult {
  facility_name: string
  rank: number
  outcome: string
  proposed?: boolean
  transcript: Turn[]
  bed_type?: string
  accepting_physician?: string
  decline_reason?: string
  contact_name?: string
  contact_role?: string
}

type Phase = 'dialing' | 'ringing' | 'connected' | 'talking' | 'wrapup'

interface Props {
  results: CallResult[]
  onComplete: () => void
}

export default function LiveCallSession({ results, onComplete }: Props) {
  const [callIndex, setCallIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('dialing')
  const [shownTurns, setShownTurns] = useState<Turn[]>([])
  const [speakingIdx, setSpeakingIdx] = useState(-1)
  const [muted, setMuted] = useState(false)
  const [done, setDone] = useState(false)

  const cancelRef = useRef(false)
  const skipRef = useRef(false)
  const mutedRef = useRef(false)
  const resolverRef = useRef<null | (() => void)>(null)
  const voicesRef = useRef<{ ai?: SpeechSynthesisVoice; fac?: SpeechSynthesisVoice }>({})
  const scrollRef = useRef<HTMLDivElement>(null)

  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined

  // Load distinct voices for the AI and the hospital
  useEffect(() => {
    if (!synth) return
    const load = () => {
      const vs = synth.getVoices().filter(v => v.lang.toLowerCase().startsWith('en'))
      if (!vs.length) return
      // Prefer two DISTINCT female voices for both speakers
      const femaleRe = /female|zira|samantha|karen|victoria|tessa|fiona|moira|serena|susan|google uk english female|google us english/i
      const females = vs.filter(v => femaleRe.test(v.name))
      const ai = females[0] || vs[0]
      const fac = females.find(v => v !== ai) || vs.find(v => v !== ai) || ai
      voicesRef.current = { ai, fac }
    }
    load()
    synth.addEventListener('voiceschanged', load)
    return () => synth.removeEventListener('voiceschanged', load)
  }, [synth])

  useEffect(() => {
    mutedRef.current = muted
    if (muted) synth?.cancel()
  }, [muted, synth])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [shownTurns, speakingIdx])

  // Drive the WHOLE session in a single, cancellation-safe loop.
  // A local `cancelled` flag means React StrictMode's throwaway first run is
  // aborted cleanly while the real run plays through — no double messages/audio.
  useEffect(() => {
    let cancelled = false
    cancelRef.current = false
    const isCancelled = () => cancelled || cancelRef.current

    async function run() {
      for (let idx = 0; idx < results.length; idx++) {
        if (isCancelled()) return
        setCallIndex(idx)
        await playCall(results[idx], isCancelled)
        if (isCancelled()) return
      }
      if (!isCancelled()) setDone(true)
    }
    run()

    return () => { cancelled = true; synth?.cancel(); resolverRef.current?.() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results])

  const interruptible = (run: (finish: () => void) => void) =>
    new Promise<void>(resolve => {
      let finished = false
      const finish = () => { if (!finished) { finished = true; resolverRef.current = null; resolve() } }
      resolverRef.current = finish
      run(finish)
    })

  const wait = (ms: number) => interruptible(finish => setTimeout(finish, ms))

  const speak = (turn: Turn) => interruptible(finish => {
    if (mutedRef.current || !synth) {
      const ms = Math.min(7000, Math.max(1400, turn.text.length * 48))
      setTimeout(finish, ms)
      return
    }
    const u = new SpeechSynthesisUtterance(turn.text)
    const v = voicesRef.current
    if (turn.speaker === 'AI') { if (v.ai) u.voice = v.ai; u.pitch = 1.05; u.rate = 1.05 }
    else { if (v.fac) u.voice = v.fac; u.pitch = 1.3; u.rate = 0.95 }
    u.onend = finish
    u.onerror = finish
    synth.speak(u)
  })

  async function playCall(call: CallResult, isCancelled: () => boolean) {
    setShownTurns([]); setSpeakingIdx(-1); skipRef.current = false
    setPhase('dialing'); await wait(750); if (isCancelled()) return
    setPhase('ringing'); await wait(1700); if (isCancelled()) return
    setPhase('connected'); await wait(650); if (isCancelled()) return
    setPhase('talking')

    const turns = call.transcript || []
    for (let i = 0; i < turns.length; i++) {
      if (isCancelled()) return
      if (skipRef.current) break
      setShownTurns(prev => [...prev, turns[i]])
      setSpeakingIdx(i)
      await speak(turns[i])
      setSpeakingIdx(-1)
      if (isCancelled()) return
      if (skipRef.current) break
      await wait(320)
    }

    setPhase('wrapup')
    await wait(skipRef.current ? 250 : 1500)
  }

  const skipCall = () => {
    skipRef.current = true
    synth?.cancel()
    resolverRef.current?.()
  }

  const endSession = () => {
    cancelRef.current = true
    synth?.cancel()
    resolverRef.current?.()
    setDone(true)
  }

  const current = results[callIndex]

  const statusLabel: Record<Phase, string> = {
    dialing: 'Dialing\u2026',
    ringing: 'Ringing\u2026',
    connected: 'Connected',
    talking: 'On call',
    wrapup: 'Wrapping up',
  }

  const outcomeBadge = (r: CallResult) => {
    if (r.proposed) return { label: 'Verbal Accept', cls: 'text-orange-700 bg-orange-100', Icon: UserCheck }
    if (r.outcome === 'DECLINED') return { label: 'Declined', cls: 'text-rose-700 bg-rose-100', Icon: XCircle }
    if (r.outcome === 'ACCEPTED') return { label: 'Accepted', cls: 'text-emerald-700 bg-emerald-100', Icon: CheckCircle }
    return { label: (r.outcome || '').replace(/_/g, ' '), cls: 'text-slate-600 bg-slate-200', Icon: Clock }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 overflow-hidden flex flex-col" style={{ maxHeight: '90vh' }}>
        {done ? (
          <div className="p-6 text-center">
            <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/20 flex items-center justify-center mb-3">
              <CheckCircle className="w-7 h-7 text-emerald-400" />
            </div>
            <h3 className="text-white font-bold text-lg">AI Calls Complete</h3>
            <p className="text-slate-400 text-xs mt-1 mb-4">
              {results.filter(r => r.proposed).length > 0
                ? `${results.filter(r => r.proposed).length} facility verbally accepted. Review the conversation and confirm with the accepting physician to lock the transfer.`
                : 'No facility accepted. Review the call details below.'}
            </p>
            <div className="space-y-1.5 text-left mb-4 max-h-48 overflow-y-auto">
              {results.map((r, i) => {
                const b = outcomeBadge(r)
                return (
                  <div key={i} className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800">
                    <span className="text-xs text-slate-200">#{r.rank} {r.facility_name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${b.cls}`}>
                      <b.Icon className="w-3 h-3" /> {b.label}
                    </span>
                  </div>
                )
              })}
            </div>
            <button
              onClick={onComplete}
              className="w-full px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-bold hover:bg-primary-700"
            >
              Review & Confirm
            </button>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                <PhoneCall className="w-3.5 h-3.5 text-primary-400" /> AI Transfer Calls
              </span>
              <span className="text-[11px] text-slate-500">Call {callIndex + 1} of {results.length}</span>
            </div>

            {/* Call screen */}
            <div className="px-5 pt-5 pb-3 text-center bg-gradient-to-b from-slate-800 to-slate-900">
              <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3 ${phase === 'ringing' ? 'animate-pulse bg-primary-500/30' : 'bg-slate-700'}`}>
                <Phone className={`w-7 h-7 ${phase === 'talking' || phase === 'connected' ? 'text-emerald-400' : 'text-primary-300'}`} />
              </div>
              <h3 className="text-white font-bold text-base leading-tight">{current?.facility_name}</h3>
              <div className="flex items-center justify-center gap-1.5 mt-1">
                {(phase === 'talking') ? (
                  <div className="flex items-end gap-0.5 h-3">
                    {[0, 1, 2, 3, 4].map(n => (
                      <span key={n} className="w-1 bg-emerald-400 rounded-full animate-pulse" style={{ height: `${6 + ((n % 3) + 1) * 3}px`, animationDelay: `${n * 120}ms`, animationDuration: '700ms' }} />
                    ))}
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">{statusLabel[phase]}</span>
                )}
              </div>
            </div>

            {/* Live transcript */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-2 min-h-[180px]">
              {phase === 'dialing' && <p className="text-center text-xs text-slate-500 py-6">Connecting to transfer line\u2026</p>}
              {shownTurns.map((t, i) => {
                const isAI = t.speaker === 'AI'
                const isSpeaking = speakingIdx === i
                return (
                  <div key={i} className={`flex gap-2 ${isAI ? '' : 'flex-row-reverse'}`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${isAI ? 'bg-primary-600' : 'bg-slate-600'} ${isSpeaking ? 'ring-2 ring-offset-1 ring-offset-slate-900 ' + (isAI ? 'ring-primary-400' : 'ring-slate-400') : ''}`}>
                      {isAI ? <Bot className="w-3.5 h-3.5 text-white" /> : <Stethoscope className="w-3.5 h-3.5 text-white" />}
                    </div>
                    <div className={`max-w-[80%] px-3 py-1.5 rounded-lg text-[11px] leading-relaxed ${isAI ? 'bg-primary-600/20 text-primary-100' : 'bg-slate-700 text-slate-100'} ${isSpeaking ? 'opacity-100' : 'opacity-90'}`}>
                      <span className={`block text-[9px] font-bold uppercase tracking-wider mb-0.5 ${isAI ? 'text-primary-300' : 'text-slate-400'}`}>{isAI ? 'AI Coordinator' : 'Hospital'}</span>
                      {t.text}
                    </div>
                  </div>
                )
              })}

              {/* Outcome at wrap-up */}
              {phase === 'wrapup' && current && (() => {
                const b = outcomeBadge(current)
                return (
                  <div className="pt-2">
                    <div className={`mx-auto w-fit text-[11px] px-3 py-1 rounded-full font-bold flex items-center gap-1.5 ${b.cls}`}>
                      <b.Icon className="w-3.5 h-3.5" /> {b.label}
                    </div>
                    {current.proposed && (
                      <div className="flex justify-center flex-wrap gap-3 mt-2 text-[10px] text-slate-400">
                        {current.bed_type && <span className="flex items-center gap-1"><BedDouble className="w-3 h-3" /> {current.bed_type}</span>}
                        {current.accepting_physician && <span className="flex items-center gap-1"><Stethoscope className="w-3 h-3" /> {current.accepting_physician}</span>}
                      </div>
                    )}
                    {current.decline_reason && <p className="text-center text-[10px] text-rose-400 mt-1.5">{current.decline_reason}</p>}
                  </div>
                )
              })()}
            </div>

            {/* Controls */}
            <div className="px-4 py-3 border-t border-slate-700 flex items-center gap-2">
              <button
                onClick={() => setMuted(m => !m)}
                className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                title={muted ? 'Unmute' : 'Mute'}
              >
                {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              <button
                onClick={skipCall}
                className="flex-1 px-3 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs font-medium hover:bg-slate-700 flex items-center justify-center gap-1.5"
              >
                <SkipForward className="w-3.5 h-3.5" /> Skip call
              </button>
              <button
                onClick={endSession}
                className="px-3 py-2 rounded-lg bg-rose-600 text-white text-xs font-bold hover:bg-rose-700 flex items-center justify-center gap-1.5"
              >
                <PhoneOff className="w-3.5 h-3.5" /> End & review
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
