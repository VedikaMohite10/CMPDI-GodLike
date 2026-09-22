export default function QuestionIntakeForm({
  questions,
  selectedQuestionId,
  questionText,
  onSelectQuestion,
  onQuestionChange,
  onGenerateDraft,
}) {
  return (
    <div className="parliamentary-card parliamentary-card--form">
      <div className="section-header">
        <div>
          <p className="eyebrow">Question intake</p>
          <h2>Parliamentary query</h2>
        </div>
      </div>

      <div className="parliamentary-form">
        <label className="parliamentary-field">
          <span>Scripted question</span>
          <select
            className="parliamentary-select"
            value={selectedQuestionId}
            onChange={(event) => onSelectQuestion(event.target.value)}
          >
            {questions.map((question) => (
              <option key={question.id} value={question.id}>
                {question.title}
              </option>
            ))}
          </select>
        </label>

        <label className="parliamentary-field">
          <span>Question wording</span>
          <textarea
            className="parliamentary-textarea"
            value={questionText}
            onChange={(event) => onQuestionChange(event.target.value)}
            rows={5}
          />
        </label>

        <div className="parliamentary-form__row">
          <label className="parliamentary-field">
            <span>Ministry</span>
            <input className="parliamentary-input" value="Ministry of Coal" readOnly />
          </label>

          <label className="parliamentary-field">
            <span>Urgency</span>
            <input className="parliamentary-input" value="High priority" readOnly />
          </label>
        </div>

        <button type="button" className="ui-button ui-button--primary ui-button--md" onClick={onGenerateDraft}>
          Generate draft response
        </button>
      </div>
    </div>
  )
}
