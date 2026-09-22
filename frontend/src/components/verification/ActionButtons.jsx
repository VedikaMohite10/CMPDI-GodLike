import Button from '../ui/Button'

export default function ActionButtons({ onAction }) {
  return (
    <div className="verification-actions">
      <Button variant="success" onClick={() => onAction('Accept')}>Accept</Button>
      <Button variant="secondary" onClick={() => onAction('Correct')}>Correct</Button>
      <Button variant="danger" onClick={() => onAction('Reject')}>Reject</Button>
      <Button variant="primary" onClick={() => onAction('Resolve Conflict')}>Resolve Conflict</Button>
    </div>
  )
}
