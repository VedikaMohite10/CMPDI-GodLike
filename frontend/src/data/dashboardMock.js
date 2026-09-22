export const dashboardSummary = {
  documentsProcessed: 148640,
  automationRate: 78.4,
  conflictsDetected: 86,
  pendingVerifications: 214,
  avgProcessingTimeHours: 6.4,
  trend: [
    { month: 'Jan', value: 10200 },
    { month: 'Feb', value: 10840 },
    { month: 'Mar', value: 11930 },
    { month: 'Apr', value: 12080 },
    { month: 'May', value: 13460 },
    { month: 'Jun', value: 14680 },
    { month: 'Jul', value: 15120 },
    { month: 'Aug', value: 16240 },
  ],
  subsidiaries: [
    {
      name: 'CCL',
      documents: 36420,
      automation: 81,
      conflicts: 18,
      verification: 42,
      status: 'Stable',
    },
    {
      name: 'WCL',
      documents: 31840,
      automation: 76,
      conflicts: 21,
      verification: 56,
      status: 'Monitoring',
    },
    {
      name: 'SECL',
      documents: 28950,
      automation: 79,
      conflicts: 16,
      verification: 48,
      status: 'Stable',
    },
    {
      name: 'MCL',
      documents: 26610,
      automation: 73,
      conflicts: 19,
      verification: 39,
      status: 'Review',
    },
    {
      name: 'NCL',
      documents: 25820,
      automation: 75,
      conflicts: 12,
      verification: 29,
      status: 'Stable',
    },
  ],
}

export const pipelineStages = [
  'Fragmented Documents',
  'Ingestion',
  'OCR / Extraction',
  'Validation',
  'Evidence Mapping',
  'Mining Intelligence',
  'AI Query / Reports',
  'Human Verification',
  'Decision Support',
]

export const activityFeed = [
  {
    id: 1,
    type: 'ingestion',
    title: 'New document batch ingested',
    detail: 'CCL: 1,420 reports indexed from mine safety logs',
    timestamp: '8 mins ago',
  },
  {
    id: 2,
    type: 'validation',
    title: 'OCR validation complete',
    detail: 'WCL tender packets matched 96.8% across 12 files',
    timestamp: '19 mins ago',
  },
  {
    id: 3,
    type: 'ai',
    title: 'AI query resolved',
    detail: 'Parliamentary response generated for rehabilitation and CSR compliance',
    timestamp: '42 mins ago',
  },
  {
    id: 4,
    type: 'verification',
    title: 'Human verification pending',
    detail: '3 high-risk conflict flags require manual sign-off',
    timestamp: '1 hour ago',
  },
  {
    id: 5,
    type: 'report',
    title: 'Executive summary published',
    detail: 'August production intelligence package distributed to SECL leadership',
    timestamp: '2 hours ago',
  },
]

export default dashboardSummary
