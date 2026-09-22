import Button from '../ui/Button'
import Card from '../ui/Card'
import { ArrowIcon } from '../LandingNavigation'

const subsidiaries = ['CCL', 'WCL', 'SECL', 'MCL', 'NCL']
const metrics = ['Production', 'Dispatch', 'Quality', 'Reserve', 'Safety', 'Cost']
const analyticalRequirements = ['Trend analysis', 'Comparative analysis', 'Risk review', 'Model/AI Insights']

export default function ReportScopeForm({ form, setForm, onGenerate, loading }) {
  const toggleArrayValue = (field, value) => {
    setForm((current) => {
      const selected = current[field] || []
      return {
        ...current,
        [field]: selected.includes(value)
          ? selected.filter((item) => item !== value)
          : [...selected, value],
      }
    })
  }

  return (
    <Card className="report-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Report configuration</p>
          <h2>Scope selection</h2>
        </div>
      </div>

      <div className="report-form-grid">
        <div className="ui-field">
          <label className="ui-field__label">Reporting period</label>
          <select
            className="ui-select"
            value={form.timePeriod}
            onChange={(event) => setForm((current) => ({ ...current, timePeriod: event.target.value }))}
          >
            <option value="2025-26">FY 2025-26</option>
            <option value="2024-25">FY 2024-25</option>
            <option value="2023-24">FY 2023-24</option>
          </select>
        </div>

        <div className="ui-field ui-field--full">
          <span className="ui-field__label">Entities / subsidiaries</span>
          <div className="report-chip-group">
            {subsidiaries.map((subsidiary) => (
              <button
                key={subsidiary}
                type="button"
                className={`report-chip ${form.subsidiaries.includes(subsidiary) ? 'is-selected' : ''}`}
                onClick={() => toggleArrayValue('subsidiaries', subsidiary)}
              >
                {subsidiary}
              </button>
            ))}
          </div>
        </div>

        <div className="ui-field ui-field--full">
          <span className="ui-field__label">Metrics</span>
          <div className="report-chip-group">
            {metrics.map((metric) => (
              <button
                key={metric}
                type="button"
                className={`report-chip ${form.metrics.includes(metric) ? 'is-selected' : ''}`}
                onClick={() => toggleArrayValue('metrics', metric)}
              >
                {metric}
              </button>
            ))}
          </div>
        </div>

        <div className="ui-field ui-field--full">
          <span className="ui-field__label">Analysis requirements</span>
          <div className="report-toggle-list">
            {analyticalRequirements.map((item) => (
              <label key={item} className="report-toggle">
                <input
                  type="checkbox"
                  checked={form.requirements.includes(item)}
                  onChange={() => toggleArrayValue('requirements', item)}
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="report-actions">
        <Button onClick={onGenerate} disabled={loading}>
          <span>{loading ? 'Generating preview...' : 'Generate report'}</span>
          {!loading && <ArrowIcon />}
        </Button>
      </div>
    </Card>
  )
}
