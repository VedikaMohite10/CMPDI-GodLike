export const mockNotifications = [
  {
    id: 'notif-1',
    title: 'High-risk conflict assigned',
    detail: 'SECL Rajnagar production log discrepancy requires manual review.',
    timestamp: '12 mins ago',
    category: 'Verification',
    route: '/data-quality',
    unread: true,
  },
  {
    id: 'notif-2',
    title: 'Document processing complete',
    detail: '1,420 geological survey reports ingested and indexed for CCL.',
    timestamp: '25 mins ago',
    category: 'Ingestion',
    route: '/documents',
    unread: true,
  },
  {
    id: 'notif-3',
    title: 'Parliamentary response deadline',
    detail: 'Question No. 4120 on CSR compliance pending final sign-off.',
    timestamp: '1 hour ago',
    category: 'Parliamentary',
    route: '/reports/parliamentary',
    unread: true,
  },
  {
    id: 'notif-4',
    title: 'Executive report export ready',
    detail: 'August 2025-26 operational briefing package is available for download.',
    timestamp: '2 hours ago',
    category: 'Reports',
    route: '/reports',
    unread: false,
  },
  {
    id: 'notif-5',
    title: 'Data Trust Score verified',
    detail: 'System extraction accuracy confirmed at 96.4% across 8 CIL subsidiaries.',
    timestamp: '4 hours ago',
    category: 'Data Quality',
    route: '/data-quality/metrics',
    unread: false,
  },
]

export default mockNotifications
