import React, { useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FileText, Bot, BarChart3, Map, TrendingUp, Shield,
  ChevronRight, ArrowRight, Zap, Database, AlertTriangle,
} from 'lucide-react'

const CAPABILITIES = [
  { icon: <FileText size={20} />, title: 'Document Intelligence', desc: 'OCR + extraction pipeline. PDFs, DOCX, XLSX ingested and indexed automatically.' },
  { icon: <Bot size={20} />, title: 'AI Mining Copilot', desc: 'Evidence-grounded answers from 14B LLM. Every claim cited. Conflicts surfaced. No hallucination.' },
  { icon: <Database size={20} />, title: 'Data Trust Engine', desc: 'Automated conflict detection and resolution. Normalized facts with full audit trail.' },
  { icon: <BarChart3 size={20} />, title: 'Analytics Intelligence', desc: 'Time series, comparative analysis, anomaly detection. Evidence-backed, not fabricated.' },
  { icon: <Map size={20} />, title: 'GIS Mine Intelligence', desc: 'Geographic layer data across Indian coal regions. Production, dispatch, quality maps.' },
  { icon: <TrendingUp size={20} />, title: 'Forecasting Engine', desc: 'MA → SES → ARIMA ladder. Model-based forecasts with confidence intervals.' },
  { icon: <AlertTriangle size={20} />, title: 'Conflict Review', desc: 'Human-in-the-loop verification. AI recommendation + evidence. Reviewer decisions.' },
  { icon: <Shield size={20} />, title: 'Parliamentary Copilot', desc: 'Draft → Review → Approve workflow. Multi-source evidence. Audit trail.' },
]

const PIPELINE_STAGES = [
  { label: 'PDF / DOCX / XLSX', color: 'text-amber-500' },
  { label: 'OCR + PARSE', color: 'text-coal-300' },
  { label: 'EXTRACT FACTS', color: 'text-coal-300' },
  { label: 'NORMALIZE', color: 'text-coal-300' },
  { label: 'EMBED', color: 'text-coal-300' },
  { label: 'INTELLIGENCE', color: 'text-amber-500' },
]

export default function LandingPage() {
  const capRef = useRef<HTMLDivElement>(null)

  return (
    <div className="min-h-screen bg-coal-950 text-white overflow-x-hidden">
      {/* ── HEADER ── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-coal-950/90 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Gov logo placeholder */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-sm bg-amber-500 flex items-center justify-center">
                <span className="text-coal-950 font-black text-xs">CG</span>
              </div>
              <div className="hidden sm:block">
                <div className="text-white font-bold text-sm">CMPDI GODLIKE</div>
                <div className="text-coal-400 text-[10px] uppercase tracking-widest">Ministry of Coal, Govt. of India</div>
              </div>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs text-coal-300 font-medium">
            <button onClick={() => capRef.current?.scrollIntoView({ behavior: 'smooth' })}
              className="hover:text-white transition-colors">Capabilities</button>
            <a href="/docs" target="_blank" className="hover:text-white transition-colors">API Docs</a>
          </nav>

          <Link
            to="/login"
            className="btn-primary text-xs px-4 py-2"
          >
            Sign In <ChevronRight size={12} />
          </Link>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="relative min-h-screen flex items-center pt-14">
        {/* Background: coal mine image */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: 'url(/images/hero/coal_mine_hero.jpg)' }}
        />
        {/* Dark overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-coal-950/95 via-coal-950/80 to-coal-950/40" />
        {/* Grid overlay */}
        <div className="absolute inset-0 bg-technical-grid opacity-30" />
        {/* Amber vignette bottom */}
        <div className="absolute bottom-0 left-0 right-0 h-64 bg-gradient-to-t from-coal-950 to-transparent" />

        {/* Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 w-full">
          <div className="max-w-2xl">
            {/* Org label */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="flex items-center gap-2 mb-6"
            >
              <div className="h-px w-8 bg-amber-500" />
              <span className="text-amber-500 text-xs font-mono uppercase tracking-[0.2em] font-semibold">
                Government of India · Ministry of Coal · CMPDI
              </span>
            </motion.div>

            {/* Main title */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              <h1 className="font-black leading-none mb-2">
                <span className="block text-6xl md:text-8xl text-white tracking-tight">CMPDI</span>
                <span className="block text-6xl md:text-8xl" style={{ color: '#F2A900' }}>GODLIKE</span>
              </h1>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.25 }}
            >
              <p className="text-xl font-light text-coal-200 tracking-wide mb-2">
                AI MINING INTELLIGENCE PLATFORM
              </p>
              <p className="text-coal-400 text-sm leading-relaxed max-w-lg mb-8">
                Transforming coal data into enterprise-grade intelligence.
                Document extraction, AI analysis, conflict detection, GIS mapping and
                forecasting — built for CMPDI engineers, geologists and analysts.
              </p>
            </motion.div>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="flex items-center gap-4"
            >
              <Link to="/login" className="btn-primary px-6 py-3 text-sm">
                <Zap size={15} />
                Access Platform
                <ArrowRight size={14} />
              </Link>
              <button
                onClick={() => capRef.current?.scrollIntoView({ behavior: 'smooth' })}
                className="btn-secondary px-6 py-3 text-sm"
              >
                Explore Intelligence
              </button>
            </motion.div>
          </div>

          {/* Stats strip */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="mt-16 flex flex-wrap gap-8"
          >
            {[
              { label: 'Documents Indexed', value: '—', note: 'Connect backend to see live stats' },
              { label: 'Facts Extracted',   value: '—', note: '' },
              { label: 'Mines Mapped',      value: '—', note: '' },
              { label: 'AI Intelligence',   value: 'LIVE', note: 'Grounded in evidence' },
            ].map((s) => (
              <div key={s.label} className="flex flex-col gap-0.5">
                <span className="section-label">{s.label}</span>
                <span className="text-2xl font-black text-white font-mono">{s.value}</span>
                {s.note && <span className="text-[10px] text-coal-400">{s.note}</span>}
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── INTELLIGENCE PIPELINE ── */}
      <section className="py-24 bg-coal-950 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-12">
            <div className="section-label mb-2">THE INTELLIGENCE LAYER</div>
            <h2 className="text-2xl font-bold text-white">From Raw Documents to Mining Intelligence</h2>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {PIPELINE_STAGES.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <div className="flex items-center gap-2">
                  <div className={`font-mono text-sm font-semibold px-3 py-2 bg-coal-900 border border-white/[0.06] rounded-sm ${stage.color}`}>
                    {stage.label}
                  </div>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <ArrowRight size={14} className="text-amber-500/50 shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* ── CAPABILITIES ── */}
      <section ref={capRef} className="py-24 bg-coal-900 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-12">
            <div className="section-label mb-2">PLATFORM CAPABILITIES</div>
            <h2 className="text-2xl font-bold text-white">Enterprise Mining Intelligence Suite</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {CAPABILITIES.map((cap) => (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4 }}
                className="industrial-card p-5 hover:border-amber-500/20 transition-colors"
              >
                <div className="text-amber-500 mb-3">{cap.icon}</div>
                <div className="text-white font-semibold text-sm mb-1">{cap.title}</div>
                <p className="text-coal-400 text-xs leading-relaxed">{cap.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECURITY ── */}
      <section className="py-20 bg-coal-950 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="section-label mb-2">ENTERPRISE SECURITY</div>
              <h2 className="text-2xl font-bold text-white mb-4">Secured. Audited. Compliant.</h2>
              <p className="text-coal-400 text-sm leading-relaxed mb-6">
                JWT-based authentication with bcrypt password hashing. Role-based access control
                with three privilege tiers. Every action creates an immutable audit log entry.
                Parliamentary query safeguards with mandatory human review.
              </p>
              <div className="space-y-3">
                {['JWT HS256 Authentication', 'Role-Based Access Control (Analyst / Reviewer / Admin)', 'Immutable Audit Log', 'Parliamentary Query Safeguards', 'Evidence-Grounded AI (no fabrication)'].map((item) => (
                  <div key={item} className="flex items-center gap-2 text-sm text-coal-200">
                    <div className="amber-dot" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div className="industrial-card p-6">
              <div className="section-label mb-4">ACCESS CONTROL MATRIX</div>
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="text-left text-coal-400 pb-2 font-medium">Feature</th>
                    <th className="text-center text-coal-400 pb-2 font-medium">Analyst</th>
                    <th className="text-center text-coal-400 pb-2 font-medium">Reviewer</th>
                    <th className="text-center text-amber-500 pb-2 font-medium">Admin</th>
                  </tr>
                </thead>
                <tbody className="space-y-1">
                  {[
                    ['Documents + AI', '✓', '✓', '✓'],
                    ['Analytics + Maps', '✓', '✓', '✓'],
                    ['Review Queue', '—', '✓', '✓'],
                    ['Parliamentary', '—', '✓', '✓'],
                    ['Audit Log', '—', '✓', '✓'],
                    ['User Management', '—', '—', '✓'],
                    ['System Health', '—', '—', '✓'],
                  ].map(([feat, a, r, ad]) => (
                    <tr key={feat} className="border-t border-white/[0.04]">
                      <td className="py-2 text-coal-200">{feat}</td>
                      <td className={`py-2 text-center ${a === '✓' ? 'text-status-operational' : 'text-coal-600'}`}>{a}</td>
                      <td className={`py-2 text-center ${r === '✓' ? 'text-status-operational' : 'text-coal-600'}`}>{r}</td>
                      <td className={`py-2 text-center ${ad === '✓' ? 'text-amber-500' : 'text-coal-600'}`}>{ad}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section className="py-24 bg-coal-900 border-t border-white/[0.04] text-center">
        <div className="max-w-2xl mx-auto px-6">
          <div className="section-label mb-3">READY TO DEPLOY</div>
          <h2 className="text-3xl font-black text-white mb-3">
            Turn Mining Data Into<br />
            <span style={{ color: '#F2A900' }}>Enterprise Intelligence.</span>
          </h2>
          <p className="text-coal-400 text-sm mb-8 leading-relaxed">
            Access the CMPDI GODLIKE platform. Authenticate with your assigned credentials.
            Contact your system administrator for access provisioning.
          </p>
          <Link to="/login" className="btn-primary px-8 py-3 text-sm">
            <Zap size={15} />
            Access CMPDI GODLIKE
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-coal-950 border-t border-white/[0.06] py-8">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 bg-amber-500 rounded-sm flex items-center justify-center">
                  <span className="text-coal-950 font-black text-[9px]">CG</span>
                </div>
                <span className="text-white font-bold text-sm">CMPDI GODLIKE</span>
              </div>
              <p className="text-coal-400 text-xs max-w-xs">
                Central Mine Planning &amp; Design Institute Ltd.<br />
                A Mini Ratna Company under Ministry of Coal<br />
                Government of India
              </p>
            </div>
            <div className="grid grid-cols-2 gap-8 text-xs text-coal-400">
              <div>
                <div className="text-coal-200 font-semibold mb-2 uppercase tracking-wider text-[10px]">Platform</div>
                <div className="space-y-1">
                  <div>AI Copilot</div>
                  <div>Document Intelligence</div>
                  <div>Analytics</div>
                  <div>Mine Maps</div>
                </div>
              </div>
              <div>
                <div className="text-coal-200 font-semibold mb-2 uppercase tracking-wider text-[10px]">Organization</div>
                <div className="space-y-1">
                  <div>CMPDI</div>
                  <div>Ministry of Coal</div>
                  <div>Coal India</div>
                  <div>Government of India</div>
                </div>
              </div>
            </div>
          </div>
          <div className="technical-separator mt-6 pt-4 text-[10px] text-coal-600 font-mono">
            © {new Date().getFullYear()} CMPDI GODLIKE — AI Mining Intelligence Platform · Confidential · Government of India
          </div>
        </div>
      </footer>
    </div>
  )
}
