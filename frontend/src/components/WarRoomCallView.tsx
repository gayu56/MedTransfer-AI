import { useEffect, useRef, useState, useCallback } from 'react'
import { Phone, PhoneOff, PhoneCall, Bot, Stethoscope, Volume2, VolumeX, CheckCircle, XCircle, UserCheck, Clock, BedDouble, Building2, Wifi, WifiOff } from 'lucide-react'
import { usePhoneSounds } from '../hooks/usePhoneSounds'

interface Turn { speaker: string; text: string }
interface CallResult {
  call_id: string
  facility_name: string
  rank: number
  outcome: string
  proposed?: boolean
  superseded?: boolean
  transcript: Turn[]
  bed_type?: string
  accepting_physician?: string
  decline_reason?: string
  contact_name?: string
  contact_role?: string
  delay?: number
}

type CardPhase = 'waiting' | 'dialing' | 'ringing' | 'connected' | 'talking' | 'done'

interface Props {
  results: CallResult[]
  onComplete: () => void
}

/* ── Individual Call Card ── */
function CallCard({
  result,
  startDelay,
  isFocused,
  onFocus,
  onDone,
  muted,
  phoneSounds,
}: {
  result: CallResult
  startDelay: number
  isFocused: boolean
  onFocus: () => void
  onDone: () => void
  muted: boolean
  phoneSounds: { dialTone: () => void; ringback: () => void; connectBeep: () => void; stop: () => void }
}) {
  const [phase, setPhase] = useState<CardPhase>('waiting')
  const [visibleTurns, setVisibleTurns] = useState<Turn[]>([])
  const [activeTurnIdx, setActiveTurnIdx] = useState(-1)
  const cancelledRef = useRef(false)
  const doneCalledRef = useRef(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const isFocusedRef = useRef(isFocused)

  // Keep isFocusedRef in sync so async closures see latest value
  useEffect(() => { isFocusedRef.current = isFocused }, [isFocused])

  // When this card gains focus mid-call, start appropriate sound
  useEffect(() => {
    if (!isFocused) return
    if (phase === 'dialing') phoneSounds.dialTone()
    else if (phase === 'ringing') phoneSounds.ringback()
  }, [isFocused, phase, phoneSounds])

  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined
  const voicesRef = useRef<{ ai?: SpeechSynthesisVoice; fac?: SpeechSynthesisVoice }>({})

  // Load voices
  useEffect(() => {
    if (!synth) return
    const load = () => {
      const vs = synth.getVoices().filter(v => v.lang.toLowerCase().startsWith('en'))
      if (!vs.length) return
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

  // Auto-scroll transcript
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [visibleTurns])

  // Drive card timeline
  useEffect(() => {
    cancelledRef.current = false
    doneCalledRef.current = false
    setVisibleTurns([])
    setActiveTurnIdx(-1)
    setPhase('waiting')
    const wait = (ms: number) => new Promise<void>(r => {
      const t = setTimeout(r, ms)
      const check = setInterval(() => { if (cancelledRef.current) { clearTimeout(t); clearInterval(check); r() } }, 100)
    })

    async function run() {
      await wait(startDelay * 1000)
      if (cancelledRef.current) return

      // No-answer shortcut
      if (result.outcome === 'NO_ANSWER' || result.outcome === 'VOICEMAIL') {
        setPhase('dialing')
        if (isFocusedRef.current) phoneSounds.dialTone()
        await wait(900); if (cancelledRef.current) return
        setPhase('ringing')
        if (isFocusedRef.current) phoneSounds.ringback()
        await wait(3500); if (cancelledRef.current) return
        phoneSounds.stop()
        setPhase('done')
        if (!doneCalledRef.current) { doneCalledRef.current = true; onDone() }
        return
      }

      setPhase('dialing')
      if (isFocusedRef.current) phoneSounds.dialTone()
      await wait(700 + Math.random() * 400); if (cancelledRef.current) return

      setPhase('ringing')
      if (isFocusedRef.current) phoneSounds.ringback()
      await wait(1200 + Math.random() * 600); if (cancelledRef.current) return

      phoneSounds.stop()
      setPhase('connected')
      if (isFocusedRef.current) phoneSounds.connectBeep()
      await wait(500); if (cancelledRef.current) return
      setPhase('talking')

      const turns = result.transcript || []
      const accumulated: Turn[] = []
      for (let i = 0; i < turns.length; i++) {
        if (cancelledRef.current) return
        accumulated.push(turns[i])
        setVisibleTurns([...accumulated])
        setActiveTurnIdx(i)
        const readMs = Math.min(5500, Math.max(1800, turns[i].text.length * 55))
        await wait(readMs)
        if (cancelledRef.current) return
      }
      setActiveTurnIdx(-1)

      await wait(600)
      if (cancelledRef.current) return
      setPhase('done')
      if (!doneCalledRef.current) { doneCalledRef.current = true; onDone() }
    }
    run()

    return () => { cancelledRef.current = true; synth?.cancel(); phoneSounds.stop() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDelay, result])

  // TTS for focused card
  useEffect(() => {
    if (!isFocused || muted || !synth || activeTurnIdx < 0) return
    const turn = visibleTurns[activeTurnIdx]
    if (!turn) return

    synth.cancel()
    const u = new SpeechSynthesisUtterance(turn.text)
    const v = voicesRef.current
    if (turn.speaker === 'AI') { if (v.ai) u.voice = v.ai; u.pitch = 1.05; u.rate = 1.05 }
    else { if (v.fac) u.voice = v.fac; u.pitch = 1.3; u.rate = 0.95 }
    synth.speak(u)

    return () => { synth.cancel() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isFocused, activeTurnIdx, muted])

  const outcomeBadge = () => {
    if (result.proposed) return { label: 'Verbal Accept', cls: 'text-orange-700 bg-orange-100 border-orange-300', icon: UserCheck }
    if (result.superseded) return { label: 'Superseded', cls: 'text-amber-700 bg-amber-100 border-amber-300', icon: Clock }
    if (result.outcome === 'ACCEPTED' || result.outcome === 'PROPOSED_ACCEPT') return { label: 'Accepted', cls: 'text-emerald-700 bg-emerald-100 border-emerald-300', icon: CheckCircle }
    if (result.outcome === 'DECLINED') return { label: 'Declined', cls: 'text-rose-700 bg-rose-100 border-rose-300', icon: XCircle }
    if (result.outcome === 'NO_ANSWER') return { label: 'No Answer', cls: 'text-slate-600 bg-slate-100 border-slate-300', icon: WifiOff }
    if (result.outcome === 'VOICEMAIL') return { label: 'Voicemail', cls: 'text-purple-600 bg-purple-100 border-purple-300', icon: PhoneOff }
    return { label: result.outcome?.replace(/_/g, ' ') || 'Pending', cls: 'text-slate-600 bg-slate-100 border-slate-300', icon: Clock }
  }

  const phaseLabel: Record<CardPhase, string> = {
    waiting: 'Queued',
    dialing: 'Dialing\u2026',
    ringing: 'Ringing\u2026',
    connected: 'Connected',
    talking: 'On Call',
    done: 'Complete',
  }

  const isActive = phase === 'talking' || phase === 'connected'
  const isRinging = phase === 'ringing'
  const isDone = phase === 'done'
  const badge = outcomeBadge()

  return (
    <div
      onClick={onFocus}
      className={`relative rounded-xl border-2 transition-all duration-300 cursor-pointer overflow-hidden flex flex-col ${
        isFocused && isActive
          ? 'border-primary-400 shadow-lg shadow-primary-500/20 ring-2 ring-primary-400/30'
          : isDone && result.proposed
            ? 'border-emerald-400 shadow-md shadow-emerald-500/20 bg-emerald-50/50'
            : isDone && result.outcome === 'DECLINED'
              ? 'border-rose-200 bg-rose-50/30'
              : isDone
                ? 'border-slate-200 bg-slate-50/50'
                : isActive
                  ? 'border-primary-200 bg-white'
                  : 'border-slate-200 bg-white hover:border-primary-200'
      }`}
      style={{ minHeight: 220 }}
    >
      {/* Card Header */}
      <div className={`px-3 py-2.5 border-b flex items-center justify-between ${
        isDone ? (result.proposed ? 'border-emerald-200 bg-emerald-50' : result.outcome === 'DECLINED' ? 'border-rose-100 bg-rose-50' : 'border-slate-100 bg-slate-50') : 'border-slate-100'
      }`}>
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
            isActive ? 'bg-primary-500' : isRinging ? 'bg-primary-400 animate-pulse' : isDone && result.proposed ? 'bg-emerald-500' : isDone && result.outcome === 'DECLINED' ? 'bg-rose-400' : 'bg-slate-300'
          }`}>
            {isDone ? (
              <badge.icon className="w-3.5 h-3.5 text-white" />
            ) : (
              <Building2 className="w-3.5 h-3.5 text-white" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-900 truncate">#{result.rank} {result.facility_name}</p>
            <div className="flex items-center gap-1">
              {isActive && (
                <div className="flex items-end gap-[2px] h-2.5">
                  {[0,1,2,3].map(n => (
                    <span key={n} className="w-[3px] bg-emerald-400 rounded-full animate-pulse" style={{ height: `${4 + ((n%3)+1)*2.5}px`, animationDelay: `${n*120}ms`, animationDuration: '700ms' }} />
                  ))}
                </div>
              )}
              <span className={`text-[10px] ${isActive ? 'text-emerald-600 font-medium' : isDone ? 'text-slate-500' : 'text-slate-400'}`}>
                {phaseLabel[phase]}
              </span>
            </div>
          </div>
        </div>
        {isFocused && isActive && (
          <Volume2 className="w-3.5 h-3.5 text-primary-500 shrink-0" />
        )}
      </div>

      {/* Card Body — mini transcript */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-2.5 py-2 space-y-1.5 max-h-36">
        {phase === 'waiting' && (
          <p className="text-center text-[10px] text-slate-400 py-4">Waiting to connect\u2026</p>
        )}
        {(phase === 'dialing' || phase === 'ringing') && (
          <div className="flex items-center justify-center py-4 gap-2">
            <Phone className={`w-5 h-5 ${isRinging ? 'text-primary-400 animate-bounce' : 'text-slate-300'}`} />
            <span className="text-xs text-slate-400">{phaseLabel[phase]}</span>
          </div>
        )}
        {visibleTurns.map((t, i) => {
          const isAI = t.speaker === 'AI'
          const isSpeaking = activeTurnIdx === i
          return (
            <div key={i} className={`flex gap-1.5 ${isAI ? '' : 'flex-row-reverse'}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${isAI ? 'bg-primary-600' : 'bg-slate-500'} ${isSpeaking && isFocused ? 'ring-2 ring-offset-1 ' + (isAI ? 'ring-primary-300' : 'ring-slate-300') : ''}`}>
                {isAI ? <Bot className="w-3 h-3 text-white" /> : <Stethoscope className="w-3 h-3 text-white" />}
              </div>
              <div className={`max-w-[85%] px-2 py-1 rounded-lg text-[10px] leading-relaxed ${isAI ? 'bg-primary-50 text-primary-900' : 'bg-slate-100 text-slate-800'}`}>
                {t.text}
              </div>
            </div>
          )
        })}
      </div>

      {/* Card Footer — outcome */}
      {isDone && (
        <div className={`px-3 py-2 border-t text-center ${result.proposed ? 'border-emerald-200 bg-emerald-50' : result.outcome === 'DECLINED' ? 'border-rose-100 bg-rose-50' : 'border-slate-100 bg-slate-50'}`}>
          <span className={`inline-flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${badge.cls}`}>
            <badge.icon className="w-3 h-3" /> {badge.label}
          </span>
          {result.proposed && result.bed_type && (
            <p className="text-[9px] text-emerald-600 mt-1 flex items-center justify-center gap-1">
              <BedDouble className="w-3 h-3" /> {result.bed_type}
              {result.accepting_physician && <> &middot; <Stethoscope className="w-3 h-3" /> {result.accepting_physician}</>}
            </p>
          )}
          {result.decline_reason && <p className="text-[9px] text-rose-500 mt-0.5">{result.decline_reason}</p>}
        </div>
      )}
    </div>
  )
}

/* ── War Room Parent ── */
export default function WarRoomCallView({ results, onComplete }: Props) {
  const [focusedIdx, setFocusedIdx] = useState(0)
  const [muted, setMuted] = useState(false)
  const phoneSounds = usePhoneSounds(muted)
  const [doneCount, setDoneCount] = useState(0)
  const [allDone, setAllDone] = useState(false)

  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined

  const handleCardDone = useCallback(() => {
    setDoneCount(c => {
      const next = c + 1
      if (next >= results.length) setAllDone(true)
      return next
    })
  }, [results.length])

  // Auto-focus first active card
  useEffect(() => {
    if (allDone) return
    // If current focused card is done, shift focus to next non-done card
    // (We can't easily check per-card phase from parent, so just keep current focus)
  }, [doneCount, allDone])

  const proposed = results.filter(r => r.proposed)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col" style={{ maxHeight: '92vh' }}>
        {/* Header */}
        <div className="px-5 py-3.5 bg-gradient-to-r from-slate-900 to-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary-500/20 flex items-center justify-center">
              <PhoneCall className="w-5 h-5 text-primary-300" />
            </div>
            <div>
              <h3 className="text-white font-bold text-sm">AI Transfer Calls — War Room</h3>
              <p className="text-slate-400 text-[10px]">
                Calling {results.length} facilities simultaneously &middot;
                {allDone
                  ? ` All calls complete`
                  : ` ${doneCount}/${results.length} done`
                }
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setMuted(m => !m); if (!muted) synth?.cancel() }}
              className="p-2 rounded-lg bg-slate-700/50 text-slate-300 hover:bg-slate-700 transition"
              title={muted ? 'Unmute' : 'Mute'}
            >
              {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            {!allDone && (
              <button
                onClick={() => setAllDone(true)}
                className="px-3 py-1.5 rounded-lg bg-rose-600/80 text-white text-xs font-bold hover:bg-rose-600 flex items-center gap-1.5 transition"
              >
                <PhoneOff className="w-3.5 h-3.5" /> End All
              </button>
            )}
          </div>
        </div>

        {/* Tip: click to hear */}
        {!allDone && (
          <div className="px-5 py-1.5 bg-primary-50 border-b border-primary-100">
            <p className="text-[10px] text-primary-700 text-center">
              <Wifi className="w-3 h-3 inline mr-1" />
              Click any card to hear that call live. Audio plays for the focused card.
            </p>
          </div>
        )}

        {!allDone ? (
          /* Grid of call cards */
          <div className="flex-1 overflow-y-auto p-4">
            <div className={`grid gap-3 ${
              results.length <= 2 ? 'grid-cols-2' : results.length <= 4 ? 'grid-cols-2 lg:grid-cols-2' : 'grid-cols-2 lg:grid-cols-3'
            }`}>
              {results.map((r, i) => (
                <CallCard
                  key={r.call_id || i}
                  result={r}
                  startDelay={r.delay ?? (i * 0.8 + Math.random() * 0.5)}
                  isFocused={focusedIdx === i}
                  onFocus={() => { synth?.cancel(); phoneSounds.stop(); setFocusedIdx(i) }}
                  onDone={handleCardDone}
                  muted={muted}
                  phoneSounds={phoneSounds}
                />
              ))}
            </div>
          </div>
        ) : (
          /* Summary view */
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-lg mx-auto text-center">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                <CheckCircle className="w-8 h-8 text-emerald-500" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-1">All Calls Complete</h3>
              <p className="text-sm text-slate-500 mb-6">
                {proposed.length > 0
                  ? `${proposed.length} facility verbally accepted. Review and confirm to lock the transfer.`
                  : 'No facility accepted. Consider expanding search or manual outreach.'}
              </p>

              <div className="space-y-2 text-left mb-6">
                {results.map((r, i) => {
                  const badge = r.proposed
                    ? { label: 'Verbal Accept', cls: 'text-orange-700 bg-orange-100', icon: UserCheck }
                    : r.superseded
                      ? { label: 'Superseded', cls: 'text-amber-700 bg-amber-100', icon: Clock }
                      : r.outcome === 'DECLINED'
                        ? { label: 'Declined', cls: 'text-rose-700 bg-rose-100', icon: XCircle }
                        : r.outcome === 'ACCEPTED'
                          ? { label: 'Accepted', cls: 'text-emerald-700 bg-emerald-100', icon: CheckCircle }
                          : { label: (r.outcome || '').replace(/_/g, ' '), cls: 'text-slate-600 bg-slate-100', icon: Clock }
                  return (
                    <div key={i} className={`flex items-center justify-between px-4 py-2.5 rounded-lg border ${
                      r.proposed ? 'border-emerald-300 bg-emerald-50' : r.outcome === 'DECLINED' ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-slate-50'
                    }`}>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-500">#{r.rank}</span>
                        <span className="text-sm font-medium text-slate-900">{r.facility_name}</span>
                      </div>
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 ${badge.cls}`}>
                        <badge.icon className="w-3 h-3" /> {badge.label}
                      </span>
                    </div>
                  )
                })}
              </div>

              <button
                onClick={onComplete}
                className="w-full px-5 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-xl text-sm font-bold hover:from-primary-700 hover:to-primary-800 shadow-md transition-all"
              >
                Review Results & Confirm
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
