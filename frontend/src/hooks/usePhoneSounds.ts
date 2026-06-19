import { useRef, useCallback, useEffect } from 'react'

/**
 * Generates realistic telephone sounds using the Web Audio API.
 *
 * - dialTone  : North-American dial tone (350 Hz + 440 Hz continuous)
 * - ringback  : Ringback / ringing tone (440 Hz + 480 Hz, 2 s on / 4 s off)
 * - connectBeep : Short rising beep indicating the call was answered
 */

export function usePhoneSounds(muted: boolean) {
  const ctxRef = useRef<AudioContext | null>(null)
  const activeRef = useRef<{ nodes: AudioNode[]; stop: () => void } | null>(null)

  // Lazily create AudioContext (must happen after a user gesture)
  const getCtx = useCallback(() => {
    if (!ctxRef.current || ctxRef.current.state === 'closed') {
      ctxRef.current = new AudioContext()
    }
    if (ctxRef.current.state === 'suspended') {
      ctxRef.current.resume()
    }
    return ctxRef.current
  }, [])

  // Stop whatever is currently playing
  const stop = useCallback(() => {
    if (activeRef.current) {
      activeRef.current.stop()
      activeRef.current = null
    }
  }, [])

  // ── Dial tone: 350 Hz + 440 Hz continuous ──────────────────────────
  const dialTone = useCallback(() => {
    stop()
    if (muted) return
    const ctx = getCtx()
    const gain = ctx.createGain()
    gain.gain.value = 0.08

    const osc1 = ctx.createOscillator()
    osc1.type = 'sine'
    osc1.frequency.value = 350

    const osc2 = ctx.createOscillator()
    osc2.type = 'sine'
    osc2.frequency.value = 440

    osc1.connect(gain)
    osc2.connect(gain)
    gain.connect(ctx.destination)
    osc1.start()
    osc2.start()

    activeRef.current = {
      nodes: [osc1, osc2, gain],
      stop: () => {
        try { osc1.stop() } catch {}
        try { osc2.stop() } catch {}
        try { gain.disconnect() } catch {}
      },
    }
  }, [muted, getCtx, stop])

  // ── Ringback tone: 440 Hz + 480 Hz, 2 s on / 4 s off ─────────────
  const ringback = useCallback(() => {
    stop()
    if (muted) return
    const ctx = getCtx()
    const gain = ctx.createGain()
    gain.gain.value = 0.07

    const osc1 = ctx.createOscillator()
    osc1.type = 'sine'
    osc1.frequency.value = 440

    const osc2 = ctx.createOscillator()
    osc2.type = 'sine'
    osc2.frequency.value = 480

    osc1.connect(gain)
    osc2.connect(gain)
    gain.connect(ctx.destination)
    osc1.start()
    osc2.start()

    // Pulse: 2 s on, 4 s off
    let on = true
    const interval = setInterval(() => {
      on = !on
      gain.gain.setTargetAtTime(on ? 0.07 : 0, ctx.currentTime, 0.02)
    }, on ? 2000 : 4000)

    // More accurate version with dual timers
    clearInterval(interval)
    let running = true
    const pulse = () => {
      if (!running) return
      gain.gain.setTargetAtTime(0.07, ctx.currentTime, 0.02) // on
      setTimeout(() => {
        if (!running) return
        gain.gain.setTargetAtTime(0, ctx.currentTime, 0.02)   // off
        setTimeout(() => pulse(), 4000)
      }, 2000)
    }
    pulse()

    activeRef.current = {
      nodes: [osc1, osc2, gain],
      stop: () => {
        running = false
        try { osc1.stop() } catch {}
        try { osc2.stop() } catch {}
        try { gain.disconnect() } catch {}
      },
    }
  }, [muted, getCtx, stop])

  // ── Connection beep: short ascending tone ─────────────────────────
  const connectBeep = useCallback(() => {
    stop()
    if (muted) return
    const ctx = getCtx()
    const gain = ctx.createGain()
    gain.gain.value = 0.12

    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(600, ctx.currentTime)
    osc.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.15)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.2)

    gain.gain.setTargetAtTime(0, ctx.currentTime + 0.15, 0.02)

    activeRef.current = {
      nodes: [osc, gain],
      stop: () => {
        try { osc.stop() } catch {}
        try { gain.disconnect() } catch {}
      },
    }
    // Auto-clear after beep ends
    setTimeout(() => { activeRef.current = null }, 250)
  }, [muted, getCtx, stop])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stop()
      if (ctxRef.current && ctxRef.current.state !== 'closed') {
        ctxRef.current.close()
      }
    }
  }, [stop])

  return { dialTone, ringback, connectBeep, stop }
}
