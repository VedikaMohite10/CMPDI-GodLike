export default function Input({ label, error, className = '', ...props }) {
  return (
    <label className={`ui-field ${className}`.trim()}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <input className={error ? 'ui-input ui-input--error' : 'ui-input'} {...props} />
      {error ? <span className="ui-field__error">{error}</span> : null}
    </label>
  )
}
