import { pipelineStages } from '../../data/dashboardMock'

export default function PipelineStrip() {
  return (
    <div className="pipeline-strip" aria-label="Intelligence pipeline flow">
      {pipelineStages.map((stage, index) => (
        <div key={stage} className="pipeline-stage">
          <div className="pipeline-stage__dot" aria-hidden="true" />
          <span>{stage}</span>
          {index < pipelineStages.length - 1 ? <div className="pipeline-stage__arrow" aria-hidden="true">→</div> : null}
        </div>
      ))}
    </div>
  )
}
