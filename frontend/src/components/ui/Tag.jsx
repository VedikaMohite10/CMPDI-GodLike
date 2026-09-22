export default function Tag({ children, tone = 'neutral', className = '' }) {
  return <span className={`ui-tag ui-tag--${tone} ${className}`.trim()}>{children}</span>
}
