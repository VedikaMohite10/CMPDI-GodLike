export const reportsMock = {
  '2025-26': {
    CCL: {
      executiveSummary:
        'CCL continued to lead CMPDI production performance in FY 2025-26, increasing output to 26.4 Mt while sustaining a strong dispatch profile and quality controls across major operational blocks.',
      productionOverview: {
        total: '26.4 Mt',
        yoy: '+8.4%',
        dispatch: '18.9 Mt',
        quality: '5023 kcal/kg',
      },
      historicalTrends: [
        { label: '2021-22', value: 22.1 },
        { label: '2022-23', value: 23.8 },
        { label: '2023-24', value: 24.9 },
        { label: '2024-25', value: 25.6 },
        { label: '2025-26', value: 26.4 },
      ],
      comparativeAnalysis: [
        {
          title: 'CCL vs WCL vs SECL',
          detail: 'CCL remains 18% above WCL and 26% above SECL in annual production volume, while maintaining a more stable output profile year-over-year.',
          tone: 'green',
          evidence: {
            title: 'CCL comparative evidence',
            evidenceChain: [
              { id: 'cmp-a', label: 'AI Insight', value: 'CCL leads the portfolio by a clear margin in annual production.', confidence: 92, tone: 'green' },
              { id: 'cmp-b', label: 'Source Document', value: 'Annual Coal Production Report 2025-26', confidence: 95, tone: 'green' },
              { id: 'cmp-c', label: 'Page / Section / Table / Cell', value: 'Page 4, Executive Summary, Table A1, Cell B7', confidence: 96, tone: 'green' },
            ],
          },
        },
      ],
      keyFindings: [
        'Output grew from 24.9 Mt to 26.4 Mt in one year with stable operational discipline.',
        'Dispatch-to-power sector volume remained healthy, supporting thermal demand commitments.',
        'Average GCV remained in a strong range, supporting grade-target adherence.',
      ],
      dataQualityWarnings: [
        'Annual reporting aligns with dispatch data within a narrow variance band.',
        'No critical OCR ambiguity identified in the current review set.',
      ],
      sources: [
        'Annual Coal Production Report 2025-26',
        'Coal Quality Assay Register',
        'Production Dispatch Ledger',
      ],
      recommendations: [
        'Extend current production plan into the next quarter with incremental optimization at active benches.',
        'Maintain quality controls to support continued power-sector supply efficiency.',
      ],
      heatmap: [
        { label: 'Production', value: 92 },
        { label: 'Dispatch', value: 88 },
        { label: 'Quality', value: 90 },
        { label: 'Safety', value: 81 },
      ],
      metrics: {
        mines: 6,
        pca: '81%',
        safety: '0.7 LTIFR',
      },
    },
    WCL: {
      executiveSummary:
        'WCL maintained a steady rise in output and reserve conversion throughout FY 2025-26, supported by geological confidence and improved extraction efficiency.',
      productionOverview: {
        total: '21.1 Mt',
        yoy: '+6.3%',
        dispatch: '15.6 Mt',
        quality: '4740 kcal/kg',
      },
      historicalTrends: [
        { label: '2021-22', value: 17.4 },
        { label: '2022-23', value: 18.7 },
        { label: '2023-24', value: 19.6 },
        { label: '2024-25', value: 20.4 },
        { label: '2025-26', value: 21.1 },
      ],
      comparativeAnalysis: [
        {
          title: 'WCL growth trend',
          detail: 'WCL improved output by 21% over the last five years, sampling a reliable uplift in extraction throughput without a proportionate quality drift.',
          tone: 'green',
          evidence: {
            title: 'WCL trend evidence',
            evidenceChain: [
              { id: 'wcl-a', label: 'AI Insight', value: 'WCL output continues to rise with steady operational momentum.', confidence: 88, tone: 'green' },
              { id: 'wcl-b', label: 'Source Document', value: 'Geological Exploration Summary', confidence: 87, tone: 'green' },
              { id: 'wcl-c', label: 'Page / Section / Table / Cell', value: 'Page 9, Mine Performance, Table M2, Cell D12', confidence: 86, tone: 'yellow' },
            ],
          },
        },
      ],
      keyFindings: [
        'Production climbed steadily across the five-year period.',
        'Reserve conversion outlook remains favourable for continued expansion.',
        'Quality profile remains stable but could be improved through blending optimization.',
      ],
      dataQualityWarnings: [
        'One geological summary uses a missing unit in the OCR layer and requires manual review.',
      ],
      sources: [
        'Geological Exploration Summary',
        'Mine Planning Sheet',
      ],
      recommendations: [
        'Reconcile unit metadata in technical summaries before formal publication.',
        'Maintain current extraction pacing while monitoring seam variability.',
      ],
      heatmap: [
        { label: 'Production', value: 84 },
        { label: 'Geology', value: 86 },
        { label: 'Quality', value: 79 },
        { label: 'Efficiency', value: 82 },
      ],
      metrics: {
        mines: 5,
        pca: '76%',
        safety: '0.9 LTIFR',
      },
    },
    SECL: {
      executiveSummary:
        'SECL delivered a strong quality-led output profile and narrowed the gap against higher-volume operators while improving assay consistency across active blocks.',
      productionOverview: {
        total: '18.9 Mt',
        yoy: '+7.1%',
        dispatch: '16.3 Mt',
        quality: '5120 kcal/kg',
      },
      historicalTrends: [
        { label: '2021-22', value: 15.3 },
        { label: '2022-23', value: 16.1 },
        { label: '2023-24', value: 17.4 },
        { label: '2024-25', value: 18.2 },
        { label: '2025-26', value: 18.9 },
      ],
      comparativeAnalysis: [
        {
          title: 'SECL quality-led scaling',
          detail: 'SECL has the strongest coal-quality profile among the three operating subsidiaries while still achieving material annual growth.',
          tone: 'green',
          evidence: {
            title: 'SECL quality evidence',
            evidenceChain: [
              { id: 'secl-a', label: 'AI Insight', value: 'SECL quality remains the strongest in the current benchmark set.', confidence: 90, tone: 'green' },
              { id: 'secl-b', label: 'Source Document', value: 'Coal Quality Assay Register', confidence: 91, tone: 'green' },
              { id: 'secl-c', label: 'Page / Section / Table / Cell', value: 'Page 11, Assay Results, Table Q2, Cell H4', confidence: 93, tone: 'green' },
            ],
          },
        },
      ],
      keyFindings: [
        'SECL maintained the best ash profile in the portfolio.',
        'The output trend is consistent and materially improved over five years.',
        'The quality profile supports power-sector dispatch with reduced beneficiation load.',
      ],
      dataQualityWarnings: [
        'Entity naming appears under two variants in field extraction and should be normalized in the master registry.',
      ],
      sources: [
        'Coal Quality Assay Register',
        'Operational Mine Ledger',
      ],
      recommendations: [
        'Normalize naming conventions across field descriptions to reduce duplicate entity tracking.',
        'Prioritize quality-led dispatch planning to preserve the value premium.',
      ],
      heatmap: [
        { label: 'Production', value: 80 },
        { label: 'Quality', value: 92 },
        { label: 'Dispatch', value: 84 },
        { label: 'Blend', value: 88 },
      ],
      metrics: {
        mines: 7,
        pca: '79%',
        safety: '0.8 LTIFR',
      },
    },
  },
}

export const reportsWorkspaceMock = {
  summary: [
    { label: 'Total Reports', value: '124', detail: 'Across all categories', tone: 'neutral' },
    { label: 'Generated This Month', value: '32', detail: '18% from last month', tone: 'positive' },
    { label: 'Pending Reports', value: '08', detail: 'Scheduled / processing', tone: 'caution' },
    { label: 'Completed', value: '116', detail: '94% success rate', tone: 'positive' },
  ],
  categories: [
    { label: 'All Reports', count: 124 },
    { label: 'Production Reports', count: 28 },
    { label: 'Safety & Compliance', count: 18 },
    { label: 'Environmental Reports', count: 16 },
    { label: 'Financial & Operational', count: 12 },
    { label: 'Land & Acquisition', count: 14 },
    { label: 'Infrastructure & Projects', count: 10 },
    { label: 'Subsidiary-wise Reports', count: 20 },
    { label: 'Custom Reports', count: 6 },
  ],
  reports: [
    {
      id: 'q2-production-2025',
      name: 'Q2 2025 Production Report',
      description: 'Quarterly production output across active coalfields.',
      category: 'Production Reports',
      subsidiary: 'MCL',
      date: '12 Sept 2026',
      isoDate: '2026-09-12',
      status: 'Completed',
      type: 'PDF',
    },
    {
      id: 'safety-audit-summary',
      name: 'Safety Audit Summary',
      description: 'Validated safety findings and review status.',
      category: 'Safety & Compliance',
      subsidiary: 'SECL',
      date: '10 Sept 2026',
      isoDate: '2026-09-10',
      status: 'Completed',
      type: 'DOCX',
    },
    {
      id: 'environmental-impact-assessment',
      name: 'Environmental Impact Assessment',
      description: 'Environmental compliance and operational impact review.',
      category: 'Environmental Reports',
      subsidiary: 'CCL',
      date: '08 Sept 2026',
      isoDate: '2026-09-08',
      status: 'Completed',
      type: 'PDF',
    },
    {
      id: 'land-acquisition-status',
      name: 'Land Acquisition Status',
      description: 'Current acquisition progress across project areas.',
      category: 'Land & Acquisition',
      subsidiary: 'WCL',
      date: '05 Sept 2026',
      isoDate: '2026-09-05',
      status: 'Pending',
      type: 'XLSX',
    },
    {
      id: 'financial-performance-report',
      name: 'Financial Performance Report',
      description: 'Operational cost and financial performance overview.',
      category: 'Financial & Operational',
      subsidiary: 'NCL',
      date: '03 Sept 2026',
      isoDate: '2026-09-03',
      status: 'Completed',
      type: 'PDF',
    },
  ],
  recentlyGenerated: [
    { name: 'Subsidiary Performance', date: '12 Sept 2026', status: 'Completed' },
    { name: 'Monthly Production Data', date: '10 Sept 2026', status: 'Completed' },
    { name: 'Compliance Status Report', date: '08 Sept 2026', status: 'Completed' },
  ],
}

export default reportsMock
