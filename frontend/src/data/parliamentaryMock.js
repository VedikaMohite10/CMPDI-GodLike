export const parliamentaryQuestionsMock = [
  {
    id: 'pq-001',
    title: 'Coal dispatch shortfall',
    ministry: 'Ministry of Coal',
    urgency: 'High',
    question:
      'What was the production and dispatch trend for CCL and MCL in Q3 FY2025, and what factors explain the shortfall against the target?',
    evidenceRefs: ['CCL-PRD-442', 'MCL-DL-118', 'Q3-Dispatch-Ledger', 'Coal-Quality-Audit-08'],
    workflowSteps: [
      { id: 'question-received', label: 'Question Received', status: 'complete' },
      { id: 'question-understanding', label: 'Question Understanding', status: 'complete' },
      { id: 'retrieval', label: 'Relevant Documents Retrieval', status: 'complete' },
      { id: 'extraction', label: 'Fact Extraction', status: 'complete' },
      { id: 'calculation', label: 'Data Calculation', status: 'complete' },
      { id: 'validation', label: 'Cross-Document Validation', status: 'complete' },
      { id: 'verification', label: 'Evidence Verification', status: 'complete' },
      { id: 'draft-response', label: 'Draft Response', status: 'active' },
      { id: 'human-review', label: 'Human Review', status: 'pending' },
      { id: 'final-response', label: 'Final Cited Response', status: 'pending' },
    ],
    draftResponse: {
      title: 'Draft response',
      summary:
        'CCL and MCL together produced 18.7 Mt in Q3 FY2025, below the 20.2 Mt target. The shortfall was driven primarily by logistics constraints, dispatch pacing, and a 3.1% reduction in usable high-ash coal at the pithead.',
      confidence: 91,
      facts: [
        { label: 'Q3 production', value: '18.7 Mt', detail: 'CCL 8.9 Mt + MCL 9.8 Mt' },
        { label: 'Target', value: '20.2 Mt', detail: 'Against plan' },
        { label: 'Dispatch variance', value: '-1.5 Mt', detail: 'Lower than dispatch schedule' },
        { label: 'Primary cause', value: 'Logistics & grade mix', detail: 'Rain-related congestion and lower feed quality' },
      ],
      evidence: {
        title: 'Coal dispatch evidence chain',
        evidenceChain: [
          { id: 'e-001', label: 'Production ledger', value: 'CCL: 8.9 Mt; MCL: 9.8 Mt', confidence: 96, tone: 'green' },
          { id: 'e-002', label: 'Dispatch schedule', value: 'Q3 dispatch actual: 17.2 Mt vs target 18.7 Mt', confidence: 92, tone: 'yellow' },
          { id: 'e-003', label: 'Logistics constraint memo', value: 'Rail capacity reduced by 12% during heavy rainfall window', confidence: 88, tone: 'orange' },
          { id: 'e-004', label: 'Quality assay', value: 'Average ash increased to 32.4%, reducing effective utilization', confidence: 90, tone: 'yellow' },
        ],
      },
    },
    finalResponse: {
      title: 'Final Cited Response',
      summary:
        'The combined Q3 FY2025 output of CCL and MCL was 18.7 Mt against a target of 20.2 Mt, reflecting a 7.4% shortfall caused by rail congestion, lower dispatch pacing, and a decline in usable coal quality. The shortfall was assessed and validated across production, dispatch, and assay records.',
      confidence: 96,
      facts: [
        { label: 'Production outcome', value: '18.7 Mt', detail: 'Validated across the production ledger and dispatch register' },
        { label: 'Gap to target', value: '1.5 Mt', detail: 'Equivalent to 7.4% under target' },
        { label: 'Operational reasons', value: 'Rail constraints', detail: 'Heavy rainfall reduced throughput and scheduling reliability' },
        { label: 'Quality impact', value: '32.4% ash', detail: 'Affecting effective usable coal available for dispatch' },
      ],
      evidence: {
        title: 'Final cited evidence chain',
        evidenceChain: [
          { id: 'f-001', label: 'Production ledger', value: 'CCL and MCL production confirmed at 18.7 Mt for Q3 FY2025', confidence: 98, tone: 'green' },
          { id: 'f-002', label: 'Dispatch control note', value: 'Dispatch aligned to rail capacity and slowed during rainfall shocks', confidence: 95, tone: 'green' },
          { id: 'f-003', label: 'Assay validation', value: 'Quality grade correction applied to production and dispatch estimates', confidence: 92, tone: 'yellow' },
          { id: 'f-004', label: 'Cross-check memo', value: 'Production, dispatch, and quality records reconcile within 1.2%', confidence: 97, tone: 'green' },
        ],
      },
    },
    review: {
      approved: false,
      reviewer: '',
      status: 'Awaiting human review',
      timestamp: null,
    },
  },
  {
    id: 'pq-002',
    title: 'CSR compliance reporting',
    ministry: 'Ministry of Coal / CSR Cell',
    urgency: 'Medium',
    question:
      'How much CSR funding was committed and spent by major subsidiaries in FY2024, and which districts benefited most from recommissioned rehabilitation projects?',
    evidenceRefs: ['CSR-ALLOC-221', 'CSR-BEN-117', 'REHAB-REPORT-9A', 'DISTRICT-OUTCOME-07'],
    workflowSteps: [
      { id: 'question-received', label: 'Question Received', status: 'complete' },
      { id: 'question-understanding', label: 'Question Understanding', status: 'complete' },
      { id: 'retrieval', label: 'Relevant Documents Retrieval', status: 'complete' },
      { id: 'extraction', label: 'Fact Extraction', status: 'complete' },
      { id: 'calculation', label: 'Data Calculation', status: 'complete' },
      { id: 'validation', label: 'Cross-Document Validation', status: 'complete' },
      { id: 'verification', label: 'Evidence Verification', status: 'complete' },
      { id: 'draft-response', label: 'Draft Response', status: 'active' },
      { id: 'human-review', label: 'Human Review', status: 'pending' },
      { id: 'final-response', label: 'Final Cited Response', status: 'pending' },
    ],
    draftResponse: {
      title: 'Draft response',
      summary:
        'The major coal subsidiaries committed ₹286.4 crore in FY2024, with ₹238.1 crore disbursed across 18 rehabilitation and district welfare initiatives. The largest share was directed to Angul, Korba, and Dhanbad district schemes.',
      confidence: 90,
      facts: [
        { label: 'Committed CSR', value: '₹286.4 crore', detail: 'Across listed subsidiaries' },
        { label: 'Spent', value: '₹238.1 crore', detail: '83.1% utilization' },
        { label: 'Top districts', value: 'Angul, Korba, Dhanbad', detail: 'Largest allocation clusters' },
        { label: 'Project type', value: 'Rehabilitation + water', detail: 'Community infrastructure and welfare' },
      ],
      evidence: {
        title: 'CSR evidence chain',
        evidenceChain: [
          { id: 'csr-001', label: 'CSR allocation register', value: '₹286.4 crore committed across subsidiaries', confidence: 94, tone: 'green' },
          { id: 'csr-002', label: 'Utilization report', value: '₹238.1 crore spent, leaving 17% unutilized', confidence: 91, tone: 'yellow' },
          { id: 'csr-003', label: 'District mapping', value: 'Angul and Korba accounted for 41% of total disbursement', confidence: 88, tone: 'orange' },
          { id: 'csr-004', label: 'Audit note', value: 'Rehabilitation projects documented in FY2024 program schedule', confidence: 93, tone: 'green' },
        ],
      },
    },
    finalResponse: {
      title: 'Final Cited Response',
      summary:
        'In FY2024, major coal subsidiaries committed ₹286.4 crore under CSR and records show ₹238.1 crore spent on rehabilitation and district-level welfare programs. The highest concentrations of activity were in Angul, Korba, and Dhanbad, where community infrastructure and livelihood restoration projects were prioritized.',
      confidence: 95,
      facts: [
        { label: 'CSR commitment', value: '₹286.4 crore', detail: 'Committed by major subsidiaries' },
        { label: 'Actual spend', value: '₹238.1 crore', detail: 'Disbursed in FY2024' },
        { label: 'District concentration', value: '41% in top 3 districts', detail: 'Angul, Korba, Dhanbad' },
        { label: 'Program focus', value: 'Rehabilitation & welfare', detail: 'Infrastructure, water, livelihoods' },
      ],
      evidence: {
        title: 'Final cited evidence chain',
        evidenceChain: [
          { id: 'fcsr-001', label: 'CSR ledger', value: 'Board-approved FY2024 commitment set at ₹286.4 crore', confidence: 97, tone: 'green' },
          { id: 'fcsr-002', label: 'Expenditure register', value: '₹238.1 crore released and utilized by year-end', confidence: 96, tone: 'green' },
          { id: 'fcsr-003', label: 'District outcomes note', value: 'Priority districts aligned with project site concentration', confidence: 93, tone: 'yellow' },
          { id: 'fcsr-004', label: 'Verification memo', value: 'Allocation and distribution records reconcile within 1.8%', confidence: 95, tone: 'green' },
        ],
      },
    },
    review: {
      approved: false,
      reviewer: '',
      status: 'Awaiting human review',
      timestamp: null,
    },
  },
  {
    id: 'pq-003',
    title: 'Coal quality compliance',
    ministry: 'Ministry of Coal / Quality Control',
    urgency: 'High',
    question:
      'What is the average GCV variance for coal supplied from major subsidiaries during the last two quarters, and what is the compliance position vis-à-vis the quality contract threshold?',
    evidenceRefs: ['GCV-Q2-901', 'GCV-Q3-902', 'QUALITY-CONTRACT-15', 'LOT-TRACE-88'],
    workflowSteps: [
      { id: 'question-received', label: 'Question Received', status: 'complete' },
      { id: 'question-understanding', label: 'Question Understanding', status: 'complete' },
      { id: 'retrieval', label: 'Relevant Documents Retrieval', status: 'complete' },
      { id: 'extraction', label: 'Fact Extraction', status: 'complete' },
      { id: 'calculation', label: 'Data Calculation', status: 'complete' },
      { id: 'validation', label: 'Cross-Document Validation', status: 'complete' },
      { id: 'verification', label: 'Evidence Verification', status: 'complete' },
      { id: 'draft-response', label: 'Draft Response', status: 'active' },
      { id: 'human-review', label: 'Human Review', status: 'pending' },
      { id: 'final-response', label: 'Final Cited Response', status: 'pending' },
    ],
    draftResponse: {
      title: 'Draft response',
      summary:
        'Average GCV variance remained within the acceptable range in Q2 and Q3, although one major supplier dipped below the contract threshold on a limited batch. The overall compliance position remains stable with corrective action already underway.',
      confidence: 89,
      facts: [
        { label: 'Average variance', value: '2.6% below target', detail: 'Across major suppliers' },
        { label: 'Q3 result', value: 'Within threshold', detail: 'With minor non-conformance in one lot' },
        { label: 'Risk area', value: 'Limited test batch', detail: 'One supplier underperformed on moisture correction' },
        { label: 'Compliance status', value: 'Mostly compliant', detail: 'Corrective action underway' },
      ],
      evidence: {
        title: 'Quality evidence chain',
        evidenceChain: [
          { id: 'gcv-001', label: 'Q2 assay report', value: 'Average GCV variation at 2.4% below contract target', confidence: 92, tone: 'green' },
          { id: 'gcv-002', label: 'Q3 assay report', value: 'Average GCV variation at 2.8% below target', confidence: 90, tone: 'yellow' },
          { id: 'gcv-003', label: 'Contract threshold note', value: 'Maximum allowed variance of 3.5% before corrective action', confidence: 96, tone: 'green' },
          { id: 'gcv-004', label: 'Quality review memo', value: 'One batch flagged for moisture-driven variance and corrective treatment', confidence: 87, tone: 'orange' },
        ],
      },
    },
    finalResponse: {
      title: 'Final Cited Response',
      summary:
        'Across Q2 and Q3, average GCV variance for the major suppliers remained within the allowable contract band, with the overall compliance position stable. A single isolated lot exceeded the preferred quality band due to moisture-related variance, and the supplier has been placed under corrective action while the remainder of supply remains compliant.',
      confidence: 94,
      facts: [
        { label: 'Average variance', value: '2.6% below target', detail: 'Measured across two quarters' },
        { label: 'Contract compliance', value: 'Within allowable threshold', detail: 'Average remains under 3.5%' },
        { label: 'Deviation observed', value: 'Single lot anomaly', detail: 'Moisture-related quality variance' },
        { label: 'Corrective action', value: 'Initiated', detail: 'Supplier treatment and process checks' },
      ],
      evidence: {
        title: 'Final cited evidence chain',
        evidenceChain: [
          { id: 'fgcv-001', label: 'Q2 and Q3 assay summary', value: 'Average GCV variance remained within the contract allowance for all major suppliers', confidence: 96, tone: 'green' },
          { id: 'fgcv-002', label: 'Contract threshold benchmark', value: 'Threshold set at 3.5% variance before corrective steps trigger', confidence: 98, tone: 'green' },
          { id: 'fgcv-003', label: 'Lot trace report', value: 'One supplier lot recorded moisture-related variance below quality acceptance', confidence: 91, tone: 'yellow' },
          { id: 'fgcv-004', label: 'Quality closure memo', value: 'Corrective action implemented and compliance monitoring extended', confidence: 94, tone: 'green' },
        ],
      },
    },
    review: {
      approved: false,
      reviewer: '',
      status: 'Awaiting human review',
      timestamp: null,
    },
  },
]

export default parliamentaryQuestionsMock
