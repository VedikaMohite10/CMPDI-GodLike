import DataTable from '../ui/DataTable'
import Badge from '../ui/Badge'

const columns = [
  { key: 'itemType', label: 'Item Type' },
  { key: 'source', label: 'Source' },
  { key: 'flagType', label: 'Flag Type' },
  { key: 'flagReason', label: 'Flag Reason' },
  { key: 'confidence', label: 'Confidence' },
  { key: 'status', label: 'Status' },
  { key: 'action', label: 'Action' },
]

export default function VerificationQueueTable({ items, onSelect, selectedId }) {
  const rows = items.map((item) => ({
    ...item,
    confidence: `${item.confidence}%`,
    flagType: <span className="verification-pill verification-pill--flag">{item.flagType}</span>,
    status: <Badge tone={item.status === 'Rejected' ? 'danger' : item.status === 'Accepted' ? 'success' : item.status === 'Resolved' ? 'success' : item.status === 'Corrected' ? 'warning' : 'neutral'}>{item.status}</Badge>,
    action: (
      <button type="button" className="verification-open" onClick={() => onSelect(item.id)}>
        {selectedId === item.id ? 'Open' : 'Open'}
      </button>
    ),
  }))

  return <DataTable columns={columns} rows={rows} />
}
