import { useMemo, useState } from 'react'
import Card from '../components/ui/Card'
import DraftResponseView from '../components/parliamentary/DraftResponseView'
import FinalResponseView from '../components/parliamentary/FinalResponseView'
import HumanReviewGate from '../components/parliamentary/HumanReviewGate'
import QuestionIntakeForm from '../components/parliamentary/QuestionIntakeForm'
import StepTracker from '../components/parliamentary/StepTracker'
import { parliamentaryQuestionsMock } from '../data/parliamentaryMock'

export default function ParliamentaryQueryPage({ hideHeader = false }) {
  const [selectedId, setSelectedId] = useState(parliamentaryQuestionsMock[0].id)
  const [questionText, setQuestionText] = useState(parliamentaryQuestionsMock[0].question)
  const [review, setReview] = useState({
    approved: parliamentaryQuestionsMock[0].review.approved,
    reviewer: parliamentaryQuestionsMock[0].review.reviewer || 'A. Singh',
    status: parliamentaryQuestionsMock[0].review.status,
    timestamp: parliamentaryQuestionsMock[0].review.timestamp,
  })

  const selectedQuestion = useMemo(
    () => parliamentaryQuestionsMock.find((item) => item.id === selectedId) || parliamentaryQuestionsMock[0],
    [selectedId],
  )

  const handleSelectQuestion = (id) => {
    const match = parliamentaryQuestionsMock.find((item) => item.id === id) || parliamentaryQuestionsMock[0]
    setSelectedId(match.id)
    setQuestionText(match.question)
    setReview({
      approved: match.review.approved,
      reviewer: match.review.reviewer || 'A. Singh',
      status: match.review.status,
      timestamp: match.review.timestamp,
    })
  }

  const handleGenerateDraft = () => {
    setReview({
      approved: false,
      reviewer: 'A. Singh',
      status: 'Awaiting human review',
      timestamp: null,
    })
  }

  const handleApprove = () => {
    setReview({
      approved: true,
      reviewer: 'A. Singh',
      status: 'Approved by human reviewer',
      timestamp: new Date().toISOString(),
    })
  }

  const handleRevisionRequest = () => {
    setReview({
      approved: false,
      reviewer: 'A. Singh',
      status: 'Revision requested',
      timestamp: new Date().toISOString(),
    })
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

      <div className="parliamentary-layout">
        <div className="parliamentary-column">
          <QuestionIntakeForm
            questions={parliamentaryQuestionsMock}
            selectedQuestionId={selectedId}
            questionText={questionText}
            onSelectQuestion={handleSelectQuestion}
            onQuestionChange={setQuestionText}
            onGenerateDraft={handleGenerateDraft}
          />

          <StepTracker steps={selectedQuestion.workflowSteps} />
        </div>

        <div className="parliamentary-column">
          <Card className="parliamentary-card">
            <div className="section-header">
              <div>
                <p className="eyebrow">Case briefing</p>
                <h2>{selectedQuestion.title}</h2>
              </div>
              <span className="ui-badge ui-badge--warning">{selectedQuestion.urgency}</span>
            </div>

            <div className="parliamentary-case-summary">
              <div>
                <span>Ministry</span>
                <strong>{selectedQuestion.ministry}</strong>
              </div>
              <div>
                <span>Question ID</span>
                <strong>{selectedQuestion.id.toUpperCase()}</strong>
              </div>
            </div>
          </Card>

          <HumanReviewGate review={review} onApprove={handleApprove} onRevisionRequest={handleRevisionRequest} />
        </div>
      </div>

      <div className="parliamentary-response-grid">
        {!review.approved ? (
          <DraftResponseView
            response={selectedQuestion.draftResponse}
            question={questionText}
            evidenceRefs={selectedQuestion.evidenceRefs}
          />
        ) : (
          <FinalResponseView
            response={selectedQuestion.finalResponse}
            question={questionText}
            evidenceRefs={selectedQuestion.evidenceRefs}
          />
        )}
      </div>
    </div>
  )
}
