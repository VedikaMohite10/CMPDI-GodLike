export default function StepTracker({ steps }) {
  return (
    <div className="parliamentary-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Procedure</p>
          <h2>Workflow tracker</h2>
        </div>
      </div>

      <div className="parliamentary-stepper">
        {steps.map((step, index) => (
          <div
            key={step.id || `${step.label}-${index}`}
            className={`parliamentary-step parliamentary-step--${step.status}`}
          >
            <span className="parliamentary-step__index">{index + 1}</span>
            <div className="parliamentary-step__meta">
              <strong>{step.label}</strong>
              <small>
                {step.status === 'complete'
                  ? 'Completed'
                  : step.status === 'active'
                    ? 'In progress'
                    : 'Pending'}
              </small>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
