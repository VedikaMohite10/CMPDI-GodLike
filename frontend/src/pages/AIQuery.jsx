import { useRef, useMemo, useState } from 'react'
import { aiQueryExamples } from '../data/aiQueryMock'

const seedHistory = [
  {
    id: 'today-1',
    title: 'Environmental compliance in MCL',
    time: '10:42 AM',
    question: 'Environmental compliance in MCL',
    responseTitle: 'Environmental Compliance Status in MCL',
    summary:
      'Based on the available CMPDI and CIL documents, MCL has maintained a largely compliant environmental status, with most clearances up to date. However, a few observations have been noted regarding pending renewals for certain mining projects and compliance with recent MoEF&CC guidelines.',
    quote: '“Sustainable Mining for a Greener Tomorrow”',
    answer: aiQueryExamples[0].answer,
  },
  {
    id: 'today-2',
    title: 'Safety audit discrepancies',
    time: '09:15 AM',
    question: 'Safety audit discrepancies',
    responseTitle: 'Safety Audit Discrepancies & Recommendations',
    summary:
      'Review of recent safety audit logs indicates key compliance milestones across operational pits. Identified minor gaps in automated sensor logging for SECL and WCL underground units have been assigned for immediate safety engineer verification.',
    quote: '“Safety First, Zero Harm in Every Mine”',
    answer: aiQueryExamples[1].answer,
  },
  {
    id: 'today-3',
    title: 'EIA report summary',
    time: '08:30 AM',
    question: 'EIA report summary',
    responseTitle: 'Environmental Impact Assessment Summary',
    summary:
      'The comprehensive EIA summary evaluates air quality indices, water discharge treatment, and afforestation benchmarks across major CIL open-cast mines for FY 2025-26, showing high alignment with statutory environmental norms.',
    quote: '“Ecological Balance with Responsible Extraction”',
    answer: aiQueryExamples[2].answer,
  },
  {
    id: 'yesterday-1',
    title: 'Land acquisition documents',
    time: '21 Sept 2026',
    question: 'Land acquisition documents',
    responseTitle: 'Land Acquisition & Rehabilitation Review',
    summary:
      'Land acquisition documentation records total acreage acquired under CBA Act provisions for CCL expansion projects, along with progressive R&R compensation tracking.',
    quote: '“Accountable Land Governance and Rehabilitation”',
    answer: null,
  },
  {
    id: 'yesterday-2',
    title: 'Compliance status for SECL',
    time: '21 Sept 2026',
    question: 'Compliance status for SECL',
    responseTitle: 'SECL Environmental & Regulatory Compliance',
    summary:
      'SECL compliance audit reports confirm full adherence to forestry stage-II clearances for Korba and Raigarh blocks, with quarterly monitoring logs uploaded to government portals.',
    quote: '“Compliance-Led Growth across Subsidiaries”',
    answer: null,
  },
  {
    id: 'yesterday-3',
    title: 'WCL vs CCL comparison',
    time: '21 Sept 2026',
    question: 'WCL vs CCL comparison',
    responseTitle: 'Comparative Output Analysis: WCL vs CCL',
    summary:
      'Comparative evaluation shows CCL leading in thermal coal tonnage for power sector dispatch, while WCL exhibits higher overburden removal automation efficiency.',
    quote: '“Operational Synergies across Coal India Units”',
    answer: null,
  },
  {
    id: 'yesterday-4',
    title: 'Pending clearances overview',
    time: '20 Sept 2026',
    question: 'Pending clearances overview',
    responseTitle: 'Pending Statutory Clearances Summary',
    summary:
      'Overview of pending environmental, forest, and CTE/CTO clearances across active mining blocks, including target resolution dates and ministry submission logs.',
    quote: '“Streamlined Environmental Clearances and Oversight”',
    answer: null,
  },
]

function SpeechBubbleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function SearchIcon({ style }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="15" height="15" aria-hidden="true" style={style}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22" aria-hidden="true">
      <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z" />
    </svg>
  )
}

function PaperclipIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="18" height="18" aria-hidden="true">
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  )
}

function normalizeQuestion(value) {
  return value.trim().toLowerCase()
}

export default function AIQueryPage({ hideHeader = false }) {
  const examples = useMemo(() => aiQueryExamples, [])
  const [chatHistory, setChatHistory] = useState(seedHistory)
  const [selectedHistoryId, setSelectedHistoryId] = useState('today-1')
  const [isNewChat, setIsNewChat] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [draftQuestion, setDraftQuestion] = useState('')
  const [attachedFile, setAttachedFile] = useState(null)
  const [toast, setToast] = useState('')
  const fileInputRef = useRef(null)

  const activeItem = useMemo(() => {
    if (isNewChat || !selectedHistoryId) return null
    return chatHistory.find((item) => item.id === selectedHistoryId) || null
  }, [chatHistory, selectedHistoryId, isNewChat])

  const filteredHistory = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    if (!query) return chatHistory
    return chatHistory.filter((item) => item.title.toLowerCase().includes(query) || item.question.toLowerCase().includes(query))
  }, [chatHistory, searchTerm])

  const groupedHistory = useMemo(() => {
    const groups = {
      Today: [],
      Yesterday: [],
    }

    filteredHistory.forEach((item) => {
      const bucket = item.id.startsWith('today-') ? 'Today' : 'Yesterday'
      groups[bucket].push(item)
    })

    return groups
  }, [filteredHistory])

  const loadAnswerForQuestion = (questionText) => {
    const trimmed = questionText.trim()
    if (!trimmed && !attachedFile) return

    const displayTitle = trimmed || (attachedFile ? `Analysis of ${attachedFile.name}` : 'Document Query')
    const normalizedInput = normalizeQuestion(displayTitle)
    const match = examples.find(
      (example) =>
        normalizeQuestion(example.question) === normalizedInput ||
        normalizedInput.includes(normalizeQuestion(example.question)) ||
        normalizeQuestion(example.question).includes(normalizedInput),
    )

    const selected = match || examples[0]
    const newEntry = {
      id: `today-${Date.now()}`,
      title: displayTitle,
      time: 'Just now',
      question: displayTitle,
      responseTitle: `Analysis: ${displayTitle}`,
      summary: attachedFile
        ? `Processed attached file (${attachedFile.name}). ${selected.answer?.executiveSummary || 'Relevant operational compliance and mining metrics extracted.'}`
        : (selected.answer?.executiveSummary || 'Based on CMPDI and CIL records, relevant operational and compliance data has been compiled for review.'),
      quote: '“Verified Operational Intelligence across CIL Units”',
      answer: selected.answer,
    }

    setIsNewChat(false)
    setSelectedHistoryId(newEntry.id)
    setChatHistory((current) => [newEntry, ...current])
    setDraftQuestion('')
    setAttachedFile(null)
  }

  const handleSelectConversation = (item) => {
    setIsNewChat(false)
    setSelectedHistoryId(item.id)
    setDraftQuestion('')
    setAttachedFile(null)
  }

  const handleNewChat = () => {
    setIsNewChat(true)
    setSelectedHistoryId(null)
    setDraftQuestion('')
    setAttachedFile(null)
  }

  const handleClearChat = () => {
    setChatHistory([])
    setIsNewChat(true)
    setSelectedHistoryId(null)
    setDraftQuestion('')
    setAttachedFile(null)
    setToast('Chat history cleared')
    window.setTimeout(() => setToast(''), 2500)
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setAttachedFile(file)
      setToast(`Attached file: ${file.name}`)
      window.setTimeout(() => setToast(''), 2500)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    if (!draftQuestion.trim() && !attachedFile) return
    loadAnswerForQuestion(draftQuestion)
  }

  const suggestionQuestions = [
    'Summarize EIA report',
    'Show compliance status',
    'Compare subsidiaries',
    'Find safety incidents',
  ]

  return (
    <div className="ai-query-page" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {toast && (
        <div style={{
          position: 'fixed',
          top: '90px',
          right: '32px',
          background: '#123a3e',
          color: '#ffffff',
          padding: '10px 18px',
          borderRadius: '4px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 100,
          fontSize: '13px',
          fontWeight: 600,
        }}>
          {toast}
        </div>
      )}

      {/* Hidden file input element */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.txt,.csv"
        style={{ display: 'none' }}
      />

      {!hideHeader && (
        <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--steel-700)' }}>
          AI INTELLIGENCE
        </div>
      )}

      <div className="ai-intelligence-shell" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* Left Sidebar: Chat History */}
        <aside
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px 16px',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0, fontSize: '12px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--navy-900)' }}>
              CHAT HISTORY
            </h2>
            <button
              type="button"
              onClick={handleNewChat}
              style={{
                background: 'linear-gradient(180deg, #123a3e 0%, #0d2e31 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 12px',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              + New Chat
            </button>
          </div>

          <div style={{ position: 'relative' }}>
            <SearchIcon style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search conversations..."
              className="platform-input"
              style={{ width: '100%', paddingLeft: '32px', height: '36px', fontSize: '12px' }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Object.entries(groupedHistory).map(([groupName, items]) => {
              if (!items.length) return null

              return (
                <div key={groupName}>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    {groupName}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {items.map((item) => {
                      const isSelected = !isNewChat && selectedHistoryId === item.id

                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handleSelectConversation(item)}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '10px',
                            padding: '10px 12px',
                            borderRadius: 'var(--radius-sm)',
                            border: 'none',
                            borderLeft: isSelected ? '3px solid #d9531e' : '3px solid transparent',
                            background: isSelected ? '#fef5ef' : 'transparent',
                            textAlign: 'left',
                            cursor: 'pointer',
                            transition: 'background 0.12s ease',
                            width: '100%',
                          }}
                        >
                          <span style={{ color: isSelected ? '#d9531e' : 'var(--text-secondary)', marginTop: '2px' }}>
                            <SpeechBubbleIcon />
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
                            <strong style={{ fontSize: '12px', color: 'var(--navy-900)', fontWeight: isSelected ? 700 : 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {item.title}
                            </strong>
                            <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {item.time}
                            </span>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </aside>

        {/* Right Main Panel */}
        <section
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            minHeight: '620px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Top Panel Bar */}
          <div style={{ padding: '16px 20px 0', display: 'flex', justifyContent: 'flex-end', zIndex: 10 }}>
            <button
              type="button"
              onClick={handleClearChat}
              style={{
                border: '1px solid var(--border)',
                background: '#ffffff',
                color: 'var(--text-secondary)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 12px',
                fontSize: '11px',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <TrashIcon />
              <span>Clear chat</span>
            </button>
          </div>

          {isNewChat || !activeItem ? (
            /* NEW CHAT / ASK AI WELCOME VIEW */
            <div style={{ padding: '24px 32px 28px', display: 'flex', flexDirection: 'column', gap: '32px', flex: 1, position: 'relative', justifyContent: 'space-between' }}>
              {/* Crescent Dome Artwork */}
              <div
                className="ai-response-half-moon-bg"
                style={{
                  position: 'absolute',
                  top: '10px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: 'min(90%, 720px)',
                  height: '380px',
                  pointerEvents: 'none',
                  zIndex: 1,
                  overflow: 'hidden',
                }}
              >
                <svg viewBox="0 0 720 380" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', height: '100%' }}>
                  <path
                    d="M 60 380 C 60 170 200 30 360 30 C 520 30 660 170 660 380 Z"
                    fill="rgba(18, 58, 62, 0.04)"
                    stroke="rgba(18, 58, 62, 0.08)"
                    strokeWidth="1"
                  />
                  <path
                    d="M 120 380 L 220 300 L 300 340 L 420 250 L 520 330 L 620 290 L 660 380 Z"
                    fill="rgba(18, 58, 62, 0.04)"
                  />
                  <polygon points="420,380 430,340 440,380" fill="rgba(18, 58, 62, 0.08)" />
                  <polygon points="438,380 446,330 454,380" fill="rgba(18, 58, 62, 0.1)" />
                  <polygon points="490,380 500,325 510,380" fill="rgba(18, 58, 62, 0.11)" />
                  <polygon points="525,380 535,315 545,380" fill="rgba(18, 58, 62, 0.12)" />
                </svg>
              </div>

              {/* Center Title Block */}
              <div style={{ position: 'relative', zIndex: 2, textAlign: 'center', marginTop: '30px', marginBottom: '10px' }}>
                <div style={{ color: '#123a3e', display: 'inline-flex', marginBottom: '12px' }}>
                  <SparkleIcon />
                </div>
                <h1
                  style={{
                    margin: '0 0 10px',
                    fontFamily: 'Georgia, serif',
                    fontSize: 'clamp(2.4rem, 3.6vw, 3.8rem)',
                    fontWeight: 700,
                    color: 'var(--navy-900)',
                    letterSpacing: '-0.03em',
                  }}
                >
                  Ask AI
                </h1>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '15px' }}>
                  Get insights from CIL documents, reports, and operational data.
                </p>
              </div>

              {/* 4 Suggested Query Cards Row */}
              <div
                style={{
                  position: 'relative',
                  zIndex: 2,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '12px',
                  width: '100%',
                }}
              >
                {suggestionQuestions.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => loadAnswerForQuestion(prompt)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '16px 18px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--navy-900)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-card)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span>{prompt}</span>
                    <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>&rarr;</span>
                  </button>
                ))}
              </div>

              {/* Input Composer Box */}
              <div style={{ position: 'relative', zIndex: 2, width: '100%' }}>
                <form onSubmit={handleSubmit}>
                  <div
                    style={{
                      background: '#ffffff',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      boxShadow: 'var(--shadow-card)',
                      padding: '16px 20px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '14px',
                    }}
                  >
                    <input
                      type="text"
                      value={draftQuestion}
                      onChange={(e) => setDraftQuestion(e.target.value)}
                      placeholder="Ask a question about CIL operations, documents, compliance, or anything else..."
                      style={{
                        border: 'none',
                        background: 'transparent',
                        fontSize: '14px',
                        color: 'var(--text-primary)',
                        width: '100%',
                        outline: 'none',
                      }}
                    />

                    {attachedFile && (
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: '#f6f4f0', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', color: '#123a3e', fontWeight: 600, width: 'fit-content' }}>
                        <span>📎 {attachedFile.name} ({(attachedFile.size / 1024).toFixed(1)} KB)</span>
                        <button type="button" onClick={() => setAttachedFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#888', fontWeight: 700 }}>×</button>
                      </div>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px', borderTop: '1px solid #f0ede6' }}>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                        title="Attach file"
                      >
                        <PaperclipIcon />
                      </button>

                      <button
                        type="submit"
                        style={{
                          background: 'linear-gradient(180deg, #123a3e 0%, #0d2e31 100%)',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '9px 20px',
                          fontSize: '12px',
                          fontWeight: 700,
                          letterSpacing: '0.05em',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '8px',
                          boxShadow: '0 2px 6px rgba(18, 58, 62, 0.2)',
                        }}
                      >
                        <span>Send</span>
                        <span style={{ fontSize: '14px', lineHeight: 1 }}>&rarr;</span>
                      </button>
                    </div>
                  </div>
                </form>

                <p style={{ margin: '12px 0 0', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
                  AI responses are based on official CIL and CMPDI documents. Please verify critical information.
                </p>
              </div>
            </div>
          ) : (
            /* AI RESEARCH RESPONSE VIEW */
            <div style={{ padding: '10px 28px 24px', display: 'flex', flexDirection: 'column', gap: '24px', flex: 1, position: 'relative' }}>
              {/* HALF MOON DOME & MOUNTAIN SILHOUETTE BACKGROUND ARTWORK */}
              <div
                className="ai-response-half-moon-bg"
                style={{
                  position: 'absolute',
                  top: '-10px',
                  right: '-10px',
                  width: 'min(75%, 620px)',
                  height: '420px',
                  pointerEvents: 'none',
                  zIndex: 1,
                  overflow: 'hidden',
                }}
              >
                <svg viewBox="0 0 620 420" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', height: '100%' }}>
                  <path
                    d="M 320 10 C 460 10 580 120 580 260 C 580 340 520 410 420 420 C 520 380 550 280 540 180 C 520 80 420 30 320 10 Z"
                    fill="rgba(18, 58, 62, 0.035)"
                    stroke="rgba(18, 58, 62, 0.07)"
                    strokeWidth="1"
                  />
                  <path
                    d="M 380 40 Q 520 140 500 290 Q 440 200 380 40 Z"
                    fill="rgba(217, 83, 30, 0.025)"
                  />
                  <path
                    d="M 100 420 L 220 320 L 300 365 L 420 270 L 520 350 L 620 300 L 620 420 Z"
                    fill="rgba(18, 58, 62, 0.05)"
                  />
                  <polygon points="420,420 430,380 440,420" fill="rgba(18, 58, 62, 0.08)" />
                  <polygon points="438,420 446,370 454,420" fill="rgba(18, 58, 62, 0.1)" />
                  <polygon points="490,420 500,365 510,420" fill="rgba(18, 58, 62, 0.11)" />
                  <polygon points="525,420 535,355 545,420" fill="rgba(18, 58, 62, 0.12)" />
                </svg>
              </div>

              {/* AI Research Response Content */}
              <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: '1fr 240px', gap: '32px', alignItems: 'start', minHeight: '260px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                    <div
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '50%',
                        background: '#feefe3',
                        border: '1px solid #fde047',
                        display: 'grid',
                        placeItems: 'center',
                        color: '#d9531e',
                        flexShrink: 0,
                      }}
                    >
                      <SparkleIcon />
                    </div>
                    <div>
                      <strong style={{ fontSize: '13px', color: 'var(--navy-900)', fontWeight: 700 }}>AI Research Response</strong>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                        {activeItem?.time || '10:42 AM'}
                      </span>
                    </div>
                  </div>

                  <h2
                    style={{
                      margin: '0 0 14px',
                      fontFamily: 'Georgia, serif',
                      fontSize: 'clamp(1.8rem, 2.5vw, 2.6rem)',
                      color: 'var(--navy-900)',
                      fontWeight: 700,
                      letterSpacing: '-0.03em',
                      lineHeight: 1.15,
                    }}
                  >
                    {activeItem?.responseTitle || activeItem?.title || 'Environmental Compliance Status in MCL'}
                  </h2>

                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '15px', lineHeight: 1.65, maxWidth: '640px' }}>
                    {activeItem?.summary ||
                      'Based on the available CMPDI and CIL documents, MCL has maintained a largely compliant environmental status, with most clearances up to date. However, a few observations have been noted regarding pending renewals for certain mining projects and compliance with recent MoEF&CC guidelines.'}
                  </p>
                </div>

                {/* Quote Callout Box */}
                <div style={{ borderLeft: '3px solid #d9531e', paddingLeft: '16px', marginTop: '46px' }}>
                  <p style={{ margin: 0, fontFamily: 'Georgia, serif', fontSize: '16px', fontStyle: 'normal', color: 'var(--navy-900)', lineHeight: 1.4, fontWeight: 600 }}>
                    {activeItem?.quote || '“Sustainable Mining for a Greener Tomorrow”'}
                  </p>
                </div>
              </div>

              {/* Suggestion Cards Row */}
              <div
                style={{
                  position: 'relative',
                  zIndex: 2,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '12px',
                  marginTop: 'auto',
                  paddingTop: '16px',
                }}
              >
                {suggestionQuestions.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => loadAnswerForQuestion(prompt)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 16px',
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--navy-900)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-card)',
                      transition: 'all 0.12s ease',
                    }}
                  >
                    <span>{prompt}</span>
                    <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>&rarr;</span>
                  </button>
                ))}
              </div>

              {/* Input Composer Box */}
              <form onSubmit={handleSubmit} style={{ position: 'relative', zIndex: 2 }}>
                <div
                  style={{
                    background: '#ffffff',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    boxShadow: 'var(--shadow-card)',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <input
                    type="text"
                    value={draftQuestion}
                    onChange={(e) => setDraftQuestion(e.target.value)}
                    placeholder={`Ask a follow-up question about ${activeItem?.title || 'MCL environmental compliance'} or related documents...`}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      fontSize: '14px',
                      color: 'var(--text-primary)',
                      width: '100%',
                      outline: 'none',
                    }}
                  />

                  {attachedFile && (
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: '#f6f4f0', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', color: '#123a3e', fontWeight: 600, width: 'fit-content' }}>
                      <span>📎 {attachedFile.name} ({(attachedFile.size / 1024).toFixed(1)} KB)</span>
                      <button type="button" onClick={() => setAttachedFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#888', fontWeight: 700 }}>×</button>
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px', borderTop: '1px solid #f0ede6' }}>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                      title="Attach file"
                    >
                      <PaperclipIcon />
                    </button>

                    <button
                      type="submit"
                      style={{
                        background: 'linear-gradient(180deg, #123a3e 0%, #0d2e31 100%)',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '9px 20px',
                        fontSize: '12px',
                        fontWeight: 700,
                        letterSpacing: '0.05em',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: '0 2px 6px rgba(18, 58, 62, 0.2)',
                      }}
                    >
                      <span>Send</span>
                      <span style={{ fontSize: '14px', lineHeight: 1 }}>&rarr;</span>
                    </button>
                  </div>
                </div>
              </form>

              <p style={{ position: 'relative', zIndex: 2, margin: 0, textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
                AI responses are based on official CIL and CMPDI documents. Please verify critical information.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
