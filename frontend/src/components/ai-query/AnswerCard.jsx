import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import EvidenceExplorer from '../evidence/EvidenceExplorer'
import Badge from '../ui/Badge'

const toneMap = {
  green: 'success',
  yellow: 'warning',
  orange: 'warning',
  red: 'danger',
}

function FlagIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4.2 16V4.3c0-.5.4-.9.9-.9h7.4c.7 0 1.3.5 1.3 1.2v8.7c0 .4-.2.7-.6.9l-2.1 1.1a1.5 1.5 0 0 1-1.5 0L5 15.1a1 1 0 0 1-.8-.9Z" />
      <path d="M7.4 4.6v6.8" />
    </svg>
  )
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 3.2 16.5 15a1.2 1.2 0 0 1-1 1.8H4.5a1.2 1.2 0 0 1-1-1.8L10 3.2Z" />
      <path d="M10 7.5v4.1" />
      <path d="M10 14.2h.01" />
    </svg>
  )
}

export default function AnswerCard({ answer, selectedEvidence, onViewEvidence }) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('findings')

  if (!answer) {
    return null
  }

  const handleFlagForVerification = () => {
    navigate('/data-quality', {
      state: {
        flaggedItem: {
          id: `FLAG-AI-${Date.now()}`,
          title: `Flagged AI Query: ${answer.title}`,
          summary: answer.summary,
        },
      },
    })
  }

  return (
    <div className="ai-research-response">
      <div className="response-header">
        <div>
          <p className="eyebrow ai-research-response__eyebrow">AI Research Response</p>
          <h2>{answer.title}</h2>
        </div>
        <div className="response-header__meta">
          <Badge tone={answer.overallConfidence >= 85 ? 'success' : answer.overallConfidence >= 70 ? 'warning' : 'danger'}>
            {answer.overallConfidence}% Confidence
          </Badge>
          <Badge tone="neutral">Cross-Validated Proof</Badge>
          <button type="button" className="flag-button" onClick={handleFlagForVerification} title="Flag discrepancy for human verification">
            <FlagIcon />
            <span>Flag for Verification</span>
          </button>
        </div>
      </div>

      <div className="executive-findings">
        <h3>Executive Summary</h3>
        <p>{answer.summary}</p>
      </div>

      <hr className="response-divider" />

      <div className="response-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'findings'}
          className={`ui-tab ${activeTab === 'findings' ? 'ui-tab--active' : ''}`}
          onClick={() => setActiveTab('findings')}
        >
          Key Findings & Citations
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'data'}
          className={`ui-tab ${activeTab === 'data' ? 'ui-tab--active' : ''}`}
          onClick={() => setActiveTab('data')}
        >
          Supporting Analysis & Data
        </button>
      </div>

      {activeTab === 'findings' && (
        <div className="findings-pane">
          <div className="findings-pane__section">
            <h3>Key Audit Findings</h3>
            <ul className="ai-query-findings">
              {answer.findings.map((item) => (
                <li key={item.id} className="ai-query-finding">
                  <div className="ai-query-finding__header">
                    <div>
                      <strong>{item.label}</strong>
                      <span>{item.value}</span>
                    </div>
                    <div className="ai-query-finding__meta">
                      <Badge tone={toneMap[item.tone] || 'neutral'}>{item.tone}</Badge>
                      <button type="button" className="ui-button ui-button--ghost ui-button--sm" onClick={() => onViewEvidence(item.evidence)}>
                        View Source Evidence
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {answer.conflicts && answer.conflicts.length > 0 && (
            <div className="conflict-alert">
              <div className="conflict-alert__title">
                <WarningIcon />
                <span>Flagged Discrepancies Requiring Review</span>
              </div>
              <ul>
                {answer.conflicts.map((conflict, index) => (
                  <li key={`${conflict.title || 'conflict'}-${index}`}>
                    <strong>{conflict.title}:</strong> {conflict.detail}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selectedEvidence && (
            <div className="sources-evidence-section">
              <h3>Sources & Provenance Chain</h3>
              <EvidenceExplorer evidence={selectedEvidence} title={selectedEvidence.title} />
            </div>
          )}
        </div>
      )}

      {activeTab === 'data' && (
        <div className="data-pane">
          <div>
            <h3>Subsidiary Comparative Data</h3>
            <div className="ui-table-shell">
              <table className="ui-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>CCL (Mt)</th>
                    <th>WCL (Mt)</th>
                    <th>SECL (Mt)</th>
                  </tr>
                </thead>
                <tbody>
                  {answer.tableRows.map((row) => (
                    <tr key={row.year}>
                      <td><strong>{row.year}</strong></td>
                      <td>{row.ccl}</td>
                      <td>{row.wcl}</td>
                      <td>{row.secl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3>5-Year Comparative Visual Trend</h3>
            <div className="ai-query-chart-wrap">
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={answer.trendData}>
                  <defs>
                    <linearGradient id="cclFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor="var(--navy-900)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--navy-900)" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="wclFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor="var(--cyan-600)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="var(--cyan-600)" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="seclFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor="var(--green-600)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="var(--green-600)" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e1e4e8" />
                  <XAxis dataKey="year" stroke="#486581" />
                  <YAxis stroke="#486581" />
                  <Tooltip />
                  <Area type="monotone" dataKey="CCL" stroke="var(--navy-900)" fill="url(#cclFill)" strokeWidth={2.5} />
                  <Area type="monotone" dataKey="WCL" stroke="var(--cyan-600)" fill="url(#wclFill)" strokeWidth={2.5} />
                  <Area type="monotone" dataKey="SECL" stroke="var(--green-600)" fill="url(#seclFill)" strokeWidth={2.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
