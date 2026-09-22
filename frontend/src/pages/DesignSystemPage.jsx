import { useState } from 'react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatCard from '../components/ui/StatCard'
import Badge from '../components/ui/Badge'
import DataTable from '../components/ui/DataTable'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import Tabs from '../components/ui/Tabs'
import Tag from '../components/ui/Tag'

const columns = [
  { key: 'mine', label: 'Mine' },
  { key: 'status', label: 'Status' },
  { key: 'owner', label: 'Owner' },
  { key: 'lastAudit', label: 'Last Audit' },
]

const rows = [
  { mine: 'Jorapokhar', status: 'Validated', owner: 'CMPDI', lastAudit: '12 Jul 2026' },
  { mine: 'Kusmunda', status: 'Warning', owner: 'CIL', lastAudit: '08 Jul 2026' },
  { mine: 'Basundhara', status: 'Conflict', owner: 'CMPDI', lastAudit: '04 Jul 2026' },
]

export default function DesignSystemPage() {
  const [selectedTab, setSelectedTab] = useState('Overview')
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="design-system-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Design System</p>
          <h1>Foundation Components</h1>
        </div>
      </div>

      <div className="design-grid">
        <Card className="design-section">
          <h2>Buttons</h2>
          <div className="button-row">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="success">Success</Button>
            <Button variant="danger">Danger</Button>
          </div>
          <div className="button-row">
            <Button disabled>Disabled</Button>
            <Button variant="secondary" disabled>
              Disabled Secondary
            </Button>
            <Button variant="danger" className="button--error">
              Error State
            </Button>
          </div>
        </Card>

        <Card className="design-section">
          <h2>Badges & Tags</h2>
          <div className="stack gap-sm">
            <div className="tag-row">
              <Badge tone="success">Validated</Badge>
              <Badge tone="warning">Warning</Badge>
              <Badge tone="danger">Conflict</Badge>
              <Badge tone="neutral">Pending</Badge>
            </div>
            <div className="tag-row">
              <Tag tone="purple">AI</Tag>
              <Tag tone="cyan">Visualization</Tag>
              <Tag tone="green">Trusted</Tag>
              <Tag tone="grey">Infrastructure</Tag>
            </div>
          </div>
        </Card>

        <Card className="design-section">
          <h2>Stat Cards</h2>
          <div className="stats-grid">
            <StatCard label="Validated Docs" value="4,860" change="+12.4%" tone="success" trend="up" />
            <StatCard label="Open Queries" value="248" change="-3.1%" tone="warning" trend="down" />
            <StatCard label="Critical Flags" value="18" change="+2" tone="danger" trend="up" />
            <StatCard label="AI Summaries" value="94.6%" change="+1.8%" tone="purple" trend="up" />
          </div>
        </Card>

        <Card className="design-section">
          <h2>Forms</h2>
          <div className="form-grid">
            <Input label="Document title" placeholder="Enter report name" />
            <Input label="Document ID" defaultValue="CMPDI-2041" error="Required format mismatch" />
            <Select
              label="Subsidiary"
              defaultValue="cmpdi"
              options={[
                { label: 'CMPDI', value: 'cmpdi' },
                { label: 'CIL', value: 'cil' },
                { label: 'ECL', value: 'ecl' },
              ]}
            />
            <Select
              label="Status"
              defaultValue="warning"
              error="Select a valid status"
              options={[
                { label: 'Warning', value: 'warning' },
                { label: 'Validated', value: 'validated' },
                { label: 'Conflict', value: 'conflict' },
              ]}
            />
          </div>
        </Card>

        <Card className="design-section">
          <h2>Tabs</h2>
          <Tabs tabs={['Overview', 'Validation', 'Actions', 'Audit']} value={selectedTab} onChange={setSelectedTab} />
          <p className="tab-copy">Current tab: {selectedTab}</p>
        </Card>

        <Card className="design-section">
          <h2>Modal</h2>
          <Button onClick={() => setIsOpen(true)}>Open modal</Button>
          <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Verification Summary">
            <p>Document set reviewed and tagged for risk exposure. No critical conflict is pending escalation.</p>
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setIsOpen(false)}>
                Close
              </Button>
              <Button onClick={() => setIsOpen(false)}>Confirm</Button>
            </div>
          </Modal>
        </Card>

        <Card className="design-section design-section--wide">
          <h2>Data Table</h2>
          <DataTable columns={columns} rows={rows} />
        </Card>
      </div>
    </div>
  )
}
