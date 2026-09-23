import { useState } from 'react'
import Button from '../ui/Button'

/**
 * ExportButtons — wired to exportReport() API.
 * Props:
 *   reportId  {string|null}  — the backend report ID to export
 *   token     {string}       — JWT access token
 */
export default function ExportButtons({ reportId, token }) {
  const [toast, setToast] = useState('')
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format) => {
    if (!reportId || !token) {
      setToast(`${format} export queued — no report ID available yet`)
      window.setTimeout(() => setToast(''), 2500)
      return
    }

    setExporting(true)
    setToast(`Preparing ${format} download…`)
    try {
      // Import lazily to avoid circular dependency issues
      const { exportReport } = await import('../../api/reports')
      const blobUrl = await exportReport(token, reportId, format.toLowerCase())
      const a = Object.assign(document.createElement('a'), {
        href: blobUrl,
        download: `report-${reportId.slice(0, 8)}.${format.toLowerCase()}`,
      })
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(blobUrl)
      setToast(`${format} downloaded successfully`)
    } catch (err) {
      // Backend may not implement all export formats yet — show clear error
      setToast(`${format} export failed: ${err?.detail ?? err?.message ?? 'Check backend logs'}`)
    } finally {
      setExporting(false)
      window.setTimeout(() => setToast(''), 3000)
    }
  }

  return (
    <div className="report-export-wrapper">
      <div className="report-export-actions">
        <Button variant="secondary" onClick={() => handleExport('PDF')} disabled={exporting}>Export PDF</Button>
        <Button variant="secondary" onClick={() => handleExport('DOCX')} disabled={exporting}>Export DOCX</Button>
        <Button variant="secondary" onClick={() => handleExport('XLSX')} disabled={exporting}>Export XLSX</Button>
      </div>
      {toast && <div className="report-toast">{toast}</div>}
    </div>
  )
}
