import { useState } from 'react'
import Button from '../ui/Button'

export default function ExportButtons() {
  const [toast, setToast] = useState('')

  const showToast = (format) => {
    setToast(`${format} export queued for download.`)
    window.setTimeout(() => setToast(''), 1800)
  }

  return (
    <div className="report-export-wrapper">
      <div className="report-export-actions">
        <Button variant="secondary" onClick={() => showToast('PDF')}>Export PDF</Button>
        <Button variant="secondary" onClick={() => showToast('DOCX')}>Export DOCX</Button>
        <Button variant="secondary" onClick={() => showToast('XLSX')}>Export XLSX</Button>
      </div>
      {toast && <div className="report-toast">{toast}</div>}
    </div>
  )
}
