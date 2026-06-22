import { useEffect, useState } from "react"
import { ArrowRight, Ambulance, Shield, Building2, Phone, Menu, X } from "lucide-react"
import { Link } from "react-router-dom"

export function MedTransferLanding() {
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
  }, [mobileOpen])

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white overflow-x-hidden relative">
      {/* Background gradient overlays */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-r from-[rgba(0,132,255,0.15)] via-transparent to-transparent opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-bl from-[rgba(0,132,255,0.1)] via-transparent to-transparent opacity-50" />
      </div>

      {/* Top Nav */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0a]/80 backdrop-blur-md border-b border-white/5">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px] flex items-center justify-between h-16">
          <Link to="/landing" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-[#0084ff] rounded-lg flex items-center justify-center">
              <Ambulance className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight">MedTransfer<span className="text-[#0084ff]">AI</span></span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-[#b8b8b8] hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm text-[#b8b8b8] hover:text-white transition-colors">How It Works</a>
            <a href="#compliance" className="text-sm text-[#b8b8b8] hover:text-white transition-colors">Compliance</a>
            <Link
              to="/dashboard"
              className="flex items-center gap-2 bg-[#0084ff] text-white py-2 px-5 rounded-md text-sm font-medium hover:bg-[#0066cc] transition-all"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
          </nav>

          {/* Mobile Menu Toggle */}
          <button className="md:hidden text-white" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <div className="md:hidden bg-[#0a0a0a] border-t border-white/5 px-6 py-6 space-y-4">
            <a href="#features" onClick={() => setMobileOpen(false)} className="block text-sm text-[#b8b8b8] hover:text-white">Features</a>
            <a href="#how-it-works" onClick={() => setMobileOpen(false)} className="block text-sm text-[#b8b8b8] hover:text-white">How It Works</a>
            <a href="#compliance" onClick={() => setMobileOpen(false)} className="block text-sm text-[#b8b8b8] hover:text-white">Compliance</a>
            <Link to="/dashboard" className="block bg-[#0084ff] text-white py-2.5 px-5 rounded-md text-sm font-medium text-center" onClick={() => setMobileOpen(false)}>
              Get Started
            </Link>
          </div>
        )}
      </header>

      {/* Hero Section */}
      <main className="min-h-screen pt-[200px] md:pt-[280px] pb-20 relative">
        {/* Hero Video Background */}
        <video
          className="absolute -top-[20%] left-0 w-full h-[120%] object-cover z-0 bg-[#111]"
          autoPlay
          muted
          loop
          playsInline
        >
          <source
            src="https://mybycketvercelprojecttest.s3.sa-east-1.amazonaws.com/animation-bg.mp4"
            type="video/mp4"
          />
        </video>

        {/* Dark overlay for readability */}
        <div className="absolute inset-0 bg-black/40 z-[1]" />

        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px] flex flex-col md:flex-row justify-between items-end relative z-[2]">
          {/* Left Content */}
          <div className="max-w-[800px]">
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-1.5 mb-8 border border-white/10">
              <Shield className="w-4 h-4 text-[#0084ff]" />
              <span className="text-xs font-medium text-[#b8b8b8]">EMTALA Compliant · HIPAA Aware</span>
            </div>

            <h1 className="text-[40px] md:text-[72px] font-light leading-[1.08] mb-8 tracking-[-2px]">
              Intelligent Patient
              <br />
              <span className="text-[#0084ff]">Transfer Coordination</span>
            </h1>
            <p className="text-base md:text-lg leading-relaxed text-[#b8b8b8] mb-12 font-normal max-w-[600px]">
              AI-powered multi-agent system that automates hospital-to-hospital transfers.
              Broadcast to all facilities simultaneously, enforce EMTALA compliance automatically,
              and reduce transfer time from 45 minutes to under 5.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
              <Link
                to="/dashboard/patients"
                className="flex items-center gap-2.5 bg-[#0084ff] text-white py-3.5 px-7 rounded-md text-base font-medium hover:bg-[#0066cc] hover:translate-x-0.5 transition-all duration-200"
              >
                Start Coordinating Transfers
                <ArrowRight className="w-5 h-5" />
              </Link>
              <a
                href="#how-it-works"
                className="bg-transparent text-[#b8b8b8] py-3.5 px-7 text-base font-medium hover:text-white transition-colors duration-200"
              >
                See how it works
              </a>
            </div>
          </div>

          {/* Stats Section */}
          <div className="flex gap-12 md:gap-20 items-end mt-16 md:mt-0">
            <div className="text-center">
              <div className="text-[48px] md:text-[64px] font-light leading-none mb-3">10x</div>
              <div className="text-sm md:text-base text-[#b8b8b8] font-normal">Faster transfers</div>
            </div>
            <div className="text-center">
              <div className="text-[48px] md:text-[64px] font-light leading-none mb-3">100%</div>
              <div className="text-sm md:text-base text-[#b8b8b8] font-normal">EMTALA compliant</div>
            </div>
          </div>
        </div>
      </main>

      {/* Features Section */}
      <section id="features" className="relative z-10 bg-[#0f0f0f] py-24">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px]">
          <h2 className="text-3xl md:text-4xl font-light mb-4 tracking-tight">Why MedTransfer AI?</h2>
          <p className="text-[#b8b8b8] text-lg mb-16 max-w-[600px]">
            Every minute matters in emergency transfers. Our agentic mesh architecture replaces manual phone trees with intelligent automation.
          </p>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Phone,
                title: "Broadcast, Not Sequential",
                desc: "Contact all eligible hospitals simultaneously with AI-generated SBAR summaries. No more calling one by one.",
                stat: "45 min → 3 min",
              },
              {
                icon: Shield,
                title: "EMTALA Compliance Gates",
                desc: "Automated hard-stop checkpoints — MSE, stabilization, MD certification, consent — all enforced before transport dispatch.",
                stat: "$100K+ risk eliminated",
              },
              {
                icon: Building2,
                title: "Intelligent Facility Matching",
                desc: "AI scores hospitals by specialty, bed availability, distance, and capability. Atomic locking prevents double-booking.",
                stat: "6 agents working in parallel",
              },
            ].map(({ icon: Icon, title, desc, stat }) => (
              <div
                key={title}
                className="bg-[#161616] rounded-2xl p-8 border border-white/5 hover:border-[#0084ff]/30 transition-colors duration-300 group"
              >
                <div className="w-12 h-12 rounded-xl bg-[#0084ff]/10 flex items-center justify-center mb-6 group-hover:bg-[#0084ff]/20 transition-colors">
                  <Icon className="w-6 h-6 text-[#0084ff]" />
                </div>
                <h3 className="text-xl font-medium mb-3">{title}</h3>
                <p className="text-[#b8b8b8] text-sm leading-relaxed mb-6">{desc}</p>
                <div className="text-[#0084ff] text-sm font-medium">{stat}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="relative z-10 bg-[#0a0a0a] py-24">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px]">
          <h2 className="text-3xl md:text-4xl font-light mb-16 tracking-tight">How It Works</h2>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: "01", title: "Patient Data Entry", desc: "Select patient from EHR. AI auto-generates SBAR clinical summary from structured data." },
              { step: "02", title: "Clinician Verifies SBAR", desc: "Human-in-the-loop review. NP verifies, edits if needed, and approves the AI-generated summary." },
              { step: "03", title: "AI Broadcasts to Hospitals", desc: "Multi-agent system contacts all matched facilities simultaneously. First acceptance wins via atomic lock." },
              { step: "04", title: "EMTALA → Transport", desc: "Compliance gates enforce all checkpoints. Once complete, transport auto-dispatches." },
            ].map(({ step, title, desc }) => (
              <div key={step} className="relative">
                <div className="text-[#0084ff] text-sm font-mono font-bold mb-4">{step}</div>
                <h3 className="text-lg font-medium mb-2">{title}</h3>
                <p className="text-[#b8b8b8] text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance Section */}
      <section id="compliance" className="relative z-10 bg-[#0f0f0f] py-24">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px]">
          <div className="flex flex-col md:flex-row gap-16 items-center">
            <div className="flex-1">
              <h2 className="text-3xl md:text-4xl font-light mb-6 tracking-tight">Built for EMTALA Compliance</h2>
              <p className="text-[#b8b8b8] text-lg mb-8 leading-relaxed">
                EMTALA violations cost hospitals $50K–$100K per incident, plus CMS termination risk.
                Our system creates an automatic, timestamped, digital compliance record for every transfer.
              </p>
              <div className="space-y-4">
                {[
                  "Medical Screening Exam — pre-verified from EHR",
                  "Stabilization documented — auto-checked at transfer creation",
                  "MD Certification & Patient Consent — manual gate, cannot skip",
                  "Receiving Facility Confirmed — auto-set on acceptance",
                  "Transport dispatch blocked until all gates pass",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full bg-[#0084ff]/20 flex items-center justify-center mt-0.5 shrink-0">
                      <div className="w-2 h-2 rounded-full bg-[#0084ff]" />
                    </div>
                    <span className="text-sm text-[#d4d4d4]">{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex-1 bg-[#161616] rounded-2xl p-8 border border-white/5">
              <div className="flex items-center gap-2 mb-6">
                <Shield className="w-5 h-5 text-[#0084ff]" />
                <span className="text-sm font-semibold">EMTALA Checklist</span>
              </div>
              {[
                { label: "Medical Screening Exam", checked: true, locked: true },
                { label: "Stabilization Documented", checked: true, locked: true },
                { label: "MD Certification Signed", checked: true, locked: false },
                { label: "Patient Consent", checked: true, locked: false },
                { label: "Receiving Facility Confirmed", checked: true, locked: true },
                { label: "Transport Appropriate", checked: true, locked: false },
                { label: "Records Sent", checked: true, locked: false },
              ].map(({ label, checked, locked }) => (
                <div key={label} className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center ${checked ? 'bg-emerald-500/20' : 'bg-white/5'}`}>
                    {checked && <div className="w-2 h-2 rounded-full bg-emerald-400" />}
                  </div>
                  <span className="text-sm text-[#d4d4d4] flex-1">{label}</span>
                  {locked && <span className="text-[10px] text-[#0084ff]/60 font-mono">AUTO</span>}
                </div>
              ))}
              <div className="mt-4 p-3 bg-emerald-500/10 rounded-lg text-center">
                <span className="text-xs font-medium text-emerald-400">✓ All checks passed — ready for transport</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 bg-[#0a0a0a] py-24">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px] text-center">
          <h2 className="text-3xl md:text-5xl font-light mb-6 tracking-tight">
            Ready to transform patient transfers?
          </h2>
          <p className="text-[#b8b8b8] text-lg mb-10 max-w-[500px] mx-auto">
            See the intelligent transfer coordinator in action. No setup required.
          </p>
          <Link
            to="/dashboard/transfers/new"
            className="inline-flex items-center gap-2.5 bg-[#0084ff] text-white py-4 px-10 rounded-md text-lg font-medium hover:bg-[#0066cc] transition-all duration-200"
          >
            Start Your First Transfer <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 bg-[#0a0a0a] border-t border-white/5 py-8">
        <div className="max-w-[1400px] mx-auto px-6 md:px-[60px] flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-[#0084ff] rounded flex items-center justify-center">
              <Ambulance className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-medium">MedTransfer<span className="text-[#0084ff]">AI</span></span>
          </div>
          <div className="flex items-center gap-6">
            <span className="text-xs text-[#666]">EMTALA Compliant</span>
            <span className="text-xs text-[#666]">HIPAA Aware</span>
          </div>
          <span className="text-xs text-[#666]">© 2026 MedTransfer AI. All rights reserved.</span>
        </div>
      </footer>
    </div>
  )
}
