import { useState, useRef, useEffect } from 'react'
import { MessageSquare, X, Send, Bot, User, Loader2, Sparkles, Wrench, ChevronDown, ChevronUp } from 'lucide-react'
import { chatWithAgent } from '../services/api'

interface ToolCall {
  tool: string
  arguments: Record<string, any>
  result_preview: string
}

interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  actions?: { action: string; label: string; data?: any }[]
  toolCalls?: ToolCall[]
  actionsTaken?: { action: string; details: string }[]
  timestamp: Date
}

const toolLabels: Record<string, string> = {
  search_patient: 'Searching patients',
  get_patient_details: 'Fetching patient data',
  generate_sbar: 'Generating SBAR',
  create_transfer: 'Creating transfer',
  get_transfer_status: 'Checking transfer',
  list_active_transfers: 'Listing transfers',
  check_emtala_compliance: 'Checking EMTALA',
  run_emtala_auto_checks: 'Running auto-checks',
  get_facility_matches: 'Finding facilities',
  generate_call_script: 'Generating call script',
  get_next_action: 'Determining next step',
}

export default function AgentChat() {
  const [open, setOpen] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'agent',
      content: "Hello! I'm the **IPTC Transfer Coordinator Agent**. I can:\n\n• Search patients and pull clinical data\n• Generate SBAR summaries\n• Create transfers and match facilities\n• Run EMTALA compliance checks\n• Guide you through the entire transfer workflow\n\nTry: *\"I need to transfer Dorothy Anderson, she has a STEMI\"*",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const toggleToolExpand = (msgId: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev)
      next.has(msgId) ? next.delete(msgId) : next.add(msgId)
      return next
    })
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const res = await chatWithAgent({
        message: text,
        session_id: sessionId || undefined,
      })

      if (res.session_id) setSessionId(res.session_id)

      const agentMsg: Message = {
        id: `agent-${Date.now()}`,
        role: 'agent',
        content: res.response || 'I processed your request.',
        actions: res.suggested_actions || [],
        toolCalls: res.tool_calls || [],
        actionsTaken: res.actions_taken || [],
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, agentMsg])
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'agent',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  const handleQuickAction = (text: string) => {
    setInput(text)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const renderMarkdown = (text: string) => {
    // Simple markdown: bold (**text**) and italic (*text*)
    return text.split('\n').map((line, i) => {
      const formatted = line
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
      return <span key={i} dangerouslySetInnerHTML={{ __html: formatted + (i < text.split('\n').length - 1 ? '<br/>' : '') }} />
    })
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 transition-all hover:scale-105 flex items-center justify-center z-50"
        >
          <MessageSquare className="w-6 h-6" />
        </button>
      )}

      {open && (
        <div className="fixed bottom-6 right-6 w-[420px] h-[650px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col z-50 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-primary-600 to-indigo-600 text-white px-4 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              <div>
                <p className="text-sm font-semibold">Transfer Coordinator Agent</p>
                <p className="text-[10px] text-primary-200">Agentic AI • ReAct • Tool Calling</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-white/20 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'agent' && (
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-100 to-indigo-100 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-primary-600" />
                  </div>
                )}
                <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                  {/* Tool calls display */}
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="mb-2">
                      <button
                        onClick={() => toggleToolExpand(msg.id)}
                        className="flex items-center gap-1.5 text-[10px] text-indigo-600 font-medium hover:text-indigo-800"
                      >
                        <Wrench className="w-3 h-3" />
                        {msg.toolCalls.length} tool{msg.toolCalls.length > 1 ? 's' : ''} used
                        {expandedTools.has(msg.id) ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                      {expandedTools.has(msg.id) && (
                        <div className="mt-1.5 space-y-1">
                          {msg.toolCalls.map((tc, i) => (
                            <div key={i} className="text-[10px] bg-indigo-50 border border-indigo-100 rounded-lg px-2.5 py-1.5">
                              <div className="flex items-center gap-1.5 text-indigo-700 font-medium">
                                <Wrench className="w-2.5 h-2.5" />
                                {toolLabels[tc.tool] || tc.tool}
                              </div>
                              {Object.keys(tc.arguments).length > 0 && (
                                <div className="text-indigo-500 mt-0.5">
                                  {Object.entries(tc.arguments).map(([k, v]) => (
                                    <span key={k} className="mr-2">{k}: <span className="font-medium text-indigo-700">{String(v).slice(0, 40)}</span></span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions taken badges */}
                  {msg.actionsTaken && msg.actionsTaken.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-1.5">
                      {msg.actionsTaken.map((a, i) => (
                        <span key={i} className="text-[9px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded border border-emerald-200 font-medium">
                          ✓ {a.details}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Message content */}
                  <div
                    className={`px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-primary-600 text-white rounded-br-md'
                        : 'bg-slate-100 text-slate-800 rounded-bl-md'
                    }`}
                  >
                    {msg.role === 'agent' ? renderMarkdown(msg.content) : msg.content}
                  </div>

                  {/* Suggested actions */}
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {msg.actions.map((action, i) => (
                        <button
                          key={i}
                          onClick={() => handleQuickAction(action.label)}
                          className="text-[11px] px-2.5 py-1 bg-primary-50 text-primary-700 rounded-full hover:bg-primary-100 transition-colors font-medium border border-primary-200"
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  )}

                  <p className="text-[10px] text-slate-400 mt-1 px-1">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4 text-slate-600" />
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-100 to-indigo-100 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-primary-600" />
                </div>
                <div className="px-3 py-2 rounded-2xl rounded-bl-md bg-slate-100">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 text-primary-500 animate-spin" />
                    <span className="text-xs text-slate-500">Agent is thinking and calling tools...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="px-4 pb-2 flex gap-1.5 flex-wrap shrink-0">
            {[
              'Transfer Dorothy Anderson for STEMI',
              'Show active transfers',
              'Check EMTALA compliance',
              'What should I do next?',
            ].map(q => (
              <button
                key={q}
                onClick={() => handleQuickAction(q)}
                className="text-[10px] px-2 py-1 bg-slate-50 text-slate-500 rounded-full hover:bg-slate-100 border border-slate-200 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="px-3 pb-3 shrink-0">
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Tell the agent what you need..."
                className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none"
                disabled={sending}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending}
                className="p-1.5 rounded-lg bg-primary-600 text-white disabled:opacity-40 hover:bg-primary-700 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
