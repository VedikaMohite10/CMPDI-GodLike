export function LoadingState({ title = 'Loading data', description = 'Fetching the latest operational records.' }) {
  return (
    <div className="state-panel state-panel--loading" aria-live="polite">
      <div className="state-panel__spinner" aria-hidden="true" />
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  )
}

export function EmptyState({ title = 'No records found', description = 'Adjust the filters or return later to check for new updates.' }) {
  return (
    <div className="state-panel state-panel--empty">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  )
}

export function ErrorState({ title = 'Unable to load data', description = 'The latest records could not be retrieved. Please retry or contact the operations desk.' }) {
  return (
    <div className="state-panel state-panel--error">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  )
}

export default {
  LoadingState,
  EmptyState,
  ErrorState,
}
