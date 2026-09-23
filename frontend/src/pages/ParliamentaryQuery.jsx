import { useCallback, useEffect, useMemo, useState } from 'react'
import Card from '../components/ui/Card'
import DraftResponseView from '../components/parliamentary/DraftResponseView'
import FinalResponseView from '../components/parliamentary/FinalResponseView'
import HumanReviewGate from '../components/parliamentary/HumanReviewGate'
import QuestionIntakeForm from '../components/parliamentary/QuestionIntakeForm'
import StepTracker from '../components/parliamentary/StepTracker'
import { parliamentaryQuestionsMock } from '../data/parliamentaryMock'
import { useAuth } from '../context/AuthContext'
import {
  listParliamentaryQueries,
  getParliamentaryQuery,
  submitParliamentaryQuery,
  approveParliamentaryQuery,
  rejectParliamentaryQuery,
} from '../api/intelligence'

/** Map a backend parliamentary record to the shape the existing child components expect */
function normaliseQuery(q) {
  return {
    id:        q.id,
    question:  q.question,
    title:     q.title ?? q.question?.slice(0, 60) ?? 'Parliamentary Query',
    ministry:  q.ministry ?? 'Ministry of Coal',
    urgency:   q.urgency ?? 'Medium',
    status:    q.status,
    draftResponse:  q.draft_answer ?? q.answer ?? null,
    finalResponse:  q.final_answer ?? null,
    evidenceRefs:   q.evidence ?? [],
    workflowSteps:  q.workflow_steps ?? [],
    review: {
      approved:  q.status === 'approved',
      reviewer:  q.approved_by ?? null,
      status:    q.status === 'approved' ? 'Approved by human reviewer'
               : q.status === 'rejected' ? 'Revision requested'
               : q.status === 'pending_review' ? 'Awaiting human review'
               : 'Draft in progress',
      timestamp: q.approved_at ?? q.updated_at ?? null,
    },
  }
}

export default function ParliamentaryQueryPage({ hideHeader = false }) {
  const { token, user } = useAuth()

  const [queries, setQueries]         = useState([])
  const [selectedId, setSelectedId]   = useState(null)
  const [questionText, setQuestionText] = useState('')
  const [loading, setLoading]         = useState(true)
  const [submitting, setSubmitting]   = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast]             = useState('')

  const showToast = (msg) => { setToast(msg); window.setTimeout(() => setToast(''), 3000) }

  // Load list from backend, fallback to mock on error
  const loadQueries = useCallback(async () => {
    if (!token) return
    try {
      const result = await listParliamentaryQueries(token, { pageSize: 50 })
      const normalised = (result.items ?? []).map(normaliseQuery)
      if (normalised.length > 0) {
        setQueries(normalised)
        if (!selectedId) {
          setSelectedId(normalised[0].id)
          setQuestionText(normalised[0].question)
        }
        return
      }
    } catch { /* fallthrough to mock */ }
    // Fallback to mock data
    const mock = parliamentaryQuestionsMock.map(normaliseQuery)
    setQueries(mock)
    setSelectedId(mock[0]?.id ?? null)
    setQuestionText(mock[0]?.question ?? '')
  }, [token, selectedId])

  useEffect(() => {
    setLoading(true)
    loadQueries().finally(() => setLoading(false))
  }, [loadQueries])

  const selectedQuery = useMemo(
    () => queries.find((q) => q.id === selectedId) ?? queries[0] ?? null,
    [queries, selectedId],
  )

  const handleSelectQuestion = (id) => {
    const match = queries.find((q) => q.id === id)
    if (match) {
      setSelectedId(match.id)
      setQuestionText(match.question)
    }
  }

  const handleGenerateDraft = async () => {
    if (!questionText.trim()) return
    setSubmitting(true)
    try {
      const result = await submitParliamentaryQuery(token, questionText.trim())
      showToast('Draft submitted — awaiting review')
      // Add new query to the list and select it
      const normalised = normaliseQuery(result)
      setQueries((prev) => [normalised, ...prev])
      setSelectedId(normalised.id)
    } catch (err) {
      showToast(`Submission failed: ${err.message ?? 'Unknown error'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleApprove = async () => {
    if (!selectedQuery) return
    setActionLoading(true)
    try {
      const result = await approveParliamentaryQuery(token, selectedQuery.id, '')
      const normalised = normaliseQuery(result)
      setQueries((prev) => prev.map((q) => q.id === normalised.id ? normalised : q))
      showToast('Query approved — final answer is now visible')
    } catch (err) {
      showToast(`Approval failed: ${err.message ?? 'Unknown error'}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRevisionRequest = async () => {
    if (!selectedQuery) return
    const note = window.prompt('Reason for revision (optional):') ?? ''
    setActionLoading(true)
    try {
      const result = await rejectParliamentaryQuery(token, selectedQuery.id, note)
      const normalised = normaliseQuery(result)
      setQueries((prev) => prev.map((q) => q.id === normalised.id ? normalised : q))
      showToast('Revision requested')
    } catch (err) {
      showToast(`Action failed: ${err.message ?? 'Unknown error'}`)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="parliamentary-page">
        <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px' }}>
          Loading parliamentary queries…
        </div>
      </div>
    )
  }

  return (
    <div className="parliamentary-page">
      {!hideHeader && (
        <div className="page-header">
          <div>
            <p className="eyebrow">Parliamentary Query</p>
            <h1>Parliamentary response workflow</h1>
          </div>
        </div>
      )}

      {toast && (
        <div className="report-toast report-toast--success">
          <span>{toast}</span>
        </div>
      )}

      <div className="parliamentary-layout">
        <div className="parliamentary-column">
          <QuestionIntakeForm
            questions={queries}
            selectedQuestionId={selectedId}
            questionText={questionText}
            onSelectQuestion={handleSelectQuestion}
            onQuestionChange={setQuestionText}
            onGenerateDraft={handleGenerateDraft}
            isSubmitting={submitting}
          />

          {selectedQuery && <StepTracker steps={selectedQuery.workflowSteps} />}
        </div>

        <div className="parliamentary-column">
          {selectedQuery && (
            <Card className="parliamentary-card">
              <div className="section-header">
                <div>
                  <p className="eyebrow">Case briefing</p>
                  <h2>{selectedQuery.title}</h2>
                </div>
                <span className="ui-badge ui-badge--warning">{selectedQuery.urgency}</span>
              </div>

              <div className="parliamentary-case-summary">
                <div>
                  <span>Ministry</span>
                  <strong>{selectedQuery.ministry}</strong>
                </div>
                <div>
                  <span>Question ID</span>
                  <strong>{String(selectedQuery.id).toUpperCase()}</strong>
                </div>
              </div>
            </Card>
          )}

          {selectedQuery && (
            <HumanReviewGate
              review={selectedQuery.review}
              onApprove={handleApprove}
              onRevisionRequest={handleRevisionRequest}
              disabled={actionLoading}
            />
          )}
        </div>
      </div>

      {selectedQuery && (
        <div className="parliamentary-response-grid">
          {!selectedQuery.review.approved ? (
            <DraftResponseView
              response={selectedQuery.draftResponse}
              question={questionText}
              evidenceRefs={selectedQuery.evidenceRefs}
            />
          ) : (
            <FinalResponseView
              response={selectedQuery.finalResponse}
              question={questionText}
              evidenceRefs={selectedQuery.evidenceRefs}
            />
          )}
        </div>
      )}
    </div>
  )
}

