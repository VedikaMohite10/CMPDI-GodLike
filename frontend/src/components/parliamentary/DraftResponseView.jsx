import EvidenceExplorer from '../evidence/EvidenceExplorer'
import ExplainableAIPanel from '../ai-query/ExplainableAIPanel'

/**
 * DraftResponseView — shows the AI-generated draft answer for a parliamentary query.
 *
 * Props:
 *   response     {object}   — full backend query/parliamentary record
 *   question     {string}   — the submitted question text
 *   evidenceRefs {string[]} — legacy evidence reference IDs (shown as links)
 *
 * Renders the ExplainableAIPanel when the response contains reasoning_type or evidence
 * from the backend, satisfying the project rule: "nothing should present an LLM-inference
 * answer as fact without showing its Reasoning Type and Confidence."
 */
export default function DraftResponseView({ response, question, evidenceRefs = [] }) {
  const evidence = response?.evidence || { evidenceChain: [] }

  // Build the answer object for ExplainableAIPanel from the parliamentary record
  // Backend returns: draft_answer, reasoning_type, confidence, evidence[], calculation,
  //                  conflicts_surfaced[], model_used_intent, model_used_synthesis
  const explainablePayload = response ? {
    answer:                response.draft_answer ?? response.summary ?? response.draftResponse ?? null,
    reasoning_type:        response.reasoning_type ?? null,
    confidence:            response.confidence ?? null,
    evidence:              Array.isArray(response.evidence)
                             ? response.evidence
                             : Array.isArray(response.evidenceRefs) ? [] : [],
    conflicts_surfaced:    response.conflicts_surfaced ?? [],
    calculation:           response.calculation ?? null,
    model_used_intent:     response.model_used_intent ?? null,
    model_used_synthesis:  response.model_used_synthesis ?? null,
  } : null

  return (
    <div className="parliamentary-card">
      <div className="parliamentary-response__header">
        <div>
          <p className="eyebrow">Draft output</p>
          <h2>{response?.title || 'Draft response'}</h2>
        </div>
        <span className="parliamentary-status parliamentary-status--draft">Draft</span>
      </div>

      <div className="parliamentary-response__meta">
        <span>Question</span>
        <p>{question}</p>
      </div>

      <div className="parliamentary-response__summary">
        <strong>Response</strong>
        <p>{response?.summary ?? response?.draftResponse ?? response?.draft_answer ?? response?.answer ?? 'Awaiting AI generation…'}</p>
      </div>

      <div className="parliamentary-response__confidence">
        <span>Confidence</span>
        <strong>{response?.confidence || 0}%</strong>
      </div>

      <div className="parliamentary-facts">
        {(response?.facts || []).map((fact) => (
          <div key={fact.label} className="parliamentary-fact">
            <span>{fact.label}</span>
            <strong>{fact.value}</strong>
            <small>{fact.detail}</small>
          </div>
        ))}
      </div>

      {/* Explainable AI Panel — mandatory: show reasoning_type + confidence + evidence */}
      <ExplainableAIPanel answer={explainablePayload} compact />

      <div className="parliamentary-evidence-links">
        {evidenceRefs.map((ref) => (
          <a key={ref} href={`#${ref}`}>
            {ref}
          </a>
        ))}
      </div>

      <div className="parliamentary-divider" />
      <EvidenceExplorer evidence={evidence} title={evidence.title || 'Evidence chain'} />
    </div>
  )
}
