export const aiQueryExamples = [
  {
    id: 'production-comparison',
    question: 'Compare production of CCL, WCL and SECL over the last five years',
    answer: {
      title: 'Production performance across the last five years',
      summary:
        'CCL remains the top-producing subsidiary with a sustained growth trend, while WCL and SECL are both improving but remain below CCL. The relative spread is stable, suggesting consistent operating planning rather than abrupt volatility.',
      overallConfidence: 91,
      tableRows: [
        { year: '2021-22', ccl: '22.1 Mt', wcl: '17.4 Mt', secl: '15.3 Mt' },
        { year: '2022-23', ccl: '23.8 Mt', wcl: '18.7 Mt', secl: '16.1 Mt' },
        { year: '2023-24', ccl: '24.9 Mt', wcl: '19.6 Mt', secl: '17.4 Mt' },
        { year: '2024-25', ccl: '25.6 Mt', wcl: '20.4 Mt', secl: '18.2 Mt' },
        { year: '2025-26', ccl: '26.4 Mt', wcl: '21.1 Mt', secl: '18.9 Mt' },
      ],
      trendData: [
        { year: '2021-22', CCL: 22.1, WCL: 17.4, SECL: 15.3 },
        { year: '2022-23', CCL: 23.8, WCL: 18.7, SECL: 16.1 },
        { year: '2023-24', CCL: 24.9, WCL: 19.6, SECL: 17.4 },
        { year: '2024-25', CCL: 25.6, WCL: 20.4, SECL: 18.2 },
        { year: '2025-26', CCL: 26.4, WCL: 21.1, SECL: 18.9 },
      ],
      findings: [
        {
          id: 'ccl-lead',
          label: 'CCL remains the production leader',
          value: 'CCL delivered 26.4 Mt in FY 2025-26, 18% above WCL and 26% above SECL.',
          tone: 'green',
          confidence: 94,
          evidence: {
            title: 'CCL production traceability',
            evidenceChain: [
              { id: 'ccl-insight', label: 'AI Insight', value: 'CCL output in FY 2025-26 is 26.4 Mt.', confidence: 94, tone: 'green' },
              { id: 'ccl-source', label: 'Source Document', value: 'Annual Coal Production Report 2025-26', confidence: 96, tone: 'green' },
              { id: 'ccl-location', label: 'Page / Section / Table / Cell', value: 'Page 4, Executive Summary, Table A1, Cell B7', confidence: 97, tone: 'green' },
            ],
          },
        },
        {
          id: 'wcl-growth',
          label: 'WCL shows steady year-on-year growth',
          value: 'WCL improved from 17.4 Mt in FY 2021-22 to 21.1 Mt in FY 2025-26, a 21% increase.',
          tone: 'green',
          confidence: 88,
          evidence: {
            title: 'WCL production traceability',
            evidenceChain: [
              { id: 'wcl-insight', label: 'AI Insight', value: 'WCL production rose from 17.4 Mt to 21.1 Mt over five years.', confidence: 88, tone: 'green' },
              { id: 'wcl-source', label: 'Source Document', value: 'North-west Production Summary', confidence: 85, tone: 'yellow' },
              { id: 'wcl-location', label: 'Page / Section / Table / Cell', value: 'Page 9, Mine Performance, Table M2, Cell D12', confidence: 86, tone: 'yellow' },
            ],
          },
        },
        {
          id: 'secl-pace',
          label: 'SECL is narrowing the gap',
          value: 'SECL climbed from 15.3 Mt to 18.9 Mt, reducing the difference to CCL from 6.8 Mt to 7.5 Mt in relative terms.',
          tone: 'yellow',
          confidence: 78,
          evidence: {
            title: 'SECL trajectory traceability',
            evidenceChain: [
              { id: 'secl-insight', label: 'AI Insight', value: 'SECL output improved by 24% over the period.', confidence: 79, tone: 'yellow' },
              { id: 'secl-source', label: 'Source Document', value: 'SECL Production Ledger', confidence: 81, tone: 'yellow' },
              { id: 'secl-location', label: 'Page / Section / Table / Cell', value: 'Page 12, Output Summary, Table Q8, Cell C5', confidence: 80, tone: 'yellow' },
            ],
          },
        },
      ],
      conflicts: [
        {
          title: 'Operational variance',
          detail: 'Although the annual production trend is positive, the dispatch record for MCL still under-performs the target, suggesting a moderate gap between supply planning and dispatch execution.',
          tone: 'orange',
        },
      ],
    },
  },
  {
    id: 'quality-review',
    question: 'Which subsidiary has the lowest ash content and what does that mean operationally?',
    answer: {
      title: 'Quality comparison and operational implication',
      summary:
        'SECL has the lowest ash content in the current evaluation set, which supports a stronger quality mix for power-sector dispatch. WCL is comparatively higher and may require more washing or blending to maintain coal-quality targets.',
      overallConfidence: 87,
      tableRows: [
        { year: 'Current assay', ccl: '31.2%', wcl: '34.6%', secl: '25.6%' },
        { year: 'Moisture', ccl: '8.7%', wcl: '9.4%', secl: '8.1%' },
        { year: 'GCV', ccl: '4,860 kcal/kg', wcl: '4,420 kcal/kg', secl: '5,120 kcal/kg' },
      ],
      trendData: [
        { year: 'CCL', CCL: 31.2, WCL: 34.6, SECL: 25.6 },
        { year: 'WCL', CCL: 31.9, WCL: 35.1, SECL: 26.4 },
        { year: 'SECL', CCL: 30.8, WCL: 33.9, SECL: 25.6 },
      ],
      findings: [
        {
          id: 'quality-lead',
          label: 'SECL has the lowest ash content',
          value: 'SECL assay records show 25.6% ash content versus 31.2% for CCL and 34.6% for WCL.',
          tone: 'green',
          confidence: 92,
          evidence: {
            title: 'Quality assurance traceability',
            evidenceChain: [
              { id: 'ash-insight', label: 'AI Insight', value: 'SECL displays the strongest quality profile in the current review.', confidence: 92, tone: 'green' },
              { id: 'ash-source', label: 'Source Document', value: 'Coal Quality Assay Register', confidence: 91, tone: 'green' },
              { id: 'ash-location', label: 'Page / Section / Table / Cell', value: 'Page 11, Assay Results, Table Q2, Cell H4', confidence: 93, tone: 'green' },
            ],
          },
        },
        {
          id: 'power-use',
          label: 'Quality mix supports power-sector dispatch',
          value: 'Lower ash content correlates with higher dispatch suitability and lower beneficiation cost per tonne.',
          tone: 'yellow',
          confidence: 82,
          evidence: {
            title: 'Dispatch suitability traceability',
            evidenceChain: [
              { id: 'dispatch-insight', label: 'AI Insight', value: 'Lower ash improves fuel suitability for thermal plants.', confidence: 82, tone: 'yellow' },
              { id: 'dispatch-source', label: 'Source Document', value: 'Dispatch to Power Sector Ledger', confidence: 80, tone: 'yellow' },
              { id: 'dispatch-location', label: 'Page / Section / Table / Cell', value: 'Page 14, Operations Review, Table D2, Cell E12', confidence: 81, tone: 'yellow' },
            ],
          },
        },
      ],
      conflicts: [
        {
          title: 'Quality signal vs production scale',
          detail: 'SECL is higher in quality but still trails CCL in volumetric output. This indicates a trade-off between grade quality and absolute production volume.',
          tone: 'yellow',
        },
      ],
    },
  },
  {
    id: 'reserve-prioritization',
    question: 'Which block should be prioritized for future mine expansion based on reserve and strip ratio?',
    answer: {
      title: 'Reserve prioritization recommendation',
      summary:
        'NCL has the largest net reserve base and a favourable strip ratio, making it the strongest candidate for expansion. CCL is productive but faces more intensive stripping, reducing immediate economic flexibility.',
      overallConfidence: 89,
      tableRows: [
        { year: 'Subsidiary', ccl: 'CCL', wcl: 'WCL', secl: 'SECL', ncl: 'NCL' },
        { year: 'Net reserve', ccl: '214.8 Mt', wcl: '188.2 Mt', secl: '201.4 Mt', ncl: '342.6 Mt' },
        { year: 'Strip ratio', ccl: '2.3:1', wcl: '2.1:1', secl: '1.9:1', ncl: '1.8:1' },
      ],
      trendData: [
        { year: 'Reserve', CCL: 214.8, WCL: 188.2, SECL: 201.4, NCL: 342.6 },
        { year: 'Strip ratio', CCL: 2.3, WCL: 2.1, SECL: 1.9, NCL: 1.8 },
      ],
      findings: [
        {
          id: 'ncl-priority',
          label: 'NCL is the best candidate for expansion',
          value: 'NCL holds 342.6 Mt of net reserve with a 1.8:1 strip ratio, which is superior to CCL and WCL on both reserve scale and stripping efficiency.',
          tone: 'green',
          confidence: 93,
          evidence: {
            title: 'Expansion priority traceability',
            evidenceChain: [
              { id: 'exp-insight', label: 'AI Insight', value: 'NCL offers the strongest expansion opportunity in the current portfolio.', confidence: 93, tone: 'green' },
              { id: 'exp-source', label: 'Source Document', value: 'Exploration Block Assessment', confidence: 95, tone: 'green' },
              { id: 'exp-location', label: 'Page / Section / Table / Cell', value: 'Page 19, Reserves, Table R7, Cell E25', confidence: 96, tone: 'green' },
            ],
          },
        },
        {
          id: 'strip-constraint',
          label: 'CCL remains output-heavy but costlier to expand',
          value: 'CCL’s higher strip ratio reduces short-term expansion flexibility despite strong output performance.',
          tone: 'yellow',
          confidence: 80,
          evidence: {
            title: 'Mining continuity traceability',
            evidenceChain: [
              { id: 'cost-insight', label: 'AI Insight', value: 'Higher stripping intensity increases expansion overhead for CCL.', confidence: 80, tone: 'yellow' },
              { id: 'cost-source', label: 'Source Document', value: 'Mine Planning and Cost Review', confidence: 78, tone: 'yellow' },
              { id: 'cost-location', label: 'Page / Section / Table / Cell', value: 'Page 21, Mine Planning, Table S2, Cell D9', confidence: 79, tone: 'yellow' },
            ],
          },
        },
      ],
      conflicts: [
        {
          title: 'Demand timing conflict',
          detail: 'NCL expansion looks attractive on reserve density, but the current demand profile remains anchored on CCL output, which may delay capital prioritization.',
          tone: 'orange',
        },
      ],
    },
  },
  {
    id: 'dispatch-risk',
    question: 'Is MCL dispatch below target because of operational disruption or reporting variance?',
    answer: {
      title: 'MCL dispatch variance and likely explanatory path',
      summary:
        'The current evidence points to a partial operational shortfall rather than a pure reporting issue. The performance gap is real, but the variance is not extreme enough to suggest complete data-quality failure.',
      overallConfidence: 74,
      tableRows: [
        { year: 'Target', ccl: '13.5 Mt', wcl: '11.8 Mt', secl: '10.7 Mt', mcl: '13.5 Mt' },
        { year: 'Observed', ccl: '12.7 Mt', wcl: '11.2 Mt', secl: '10.4 Mt', mcl: '12.7 Mt' },
        { year: 'Variance', ccl: '-6.0%', wcl: '-5.1%', secl: '-2.8%', mcl: '-5.9%' },
      ],
      trendData: [
        { year: 'Target', CCL: 13.5, WCL: 11.8, SECL: 10.7, MCL: 13.5 },
        { year: 'Observed', CCL: 12.7, WCL: 11.2, SECL: 10.4, MCL: 12.7 },
      ],
      findings: [
        {
          id: 'dispatch-gap',
          label: 'Dispatch remains below planned target',
          value: 'MCL achieved 12.7 Mt against a 13.5 Mt target, a 5.9% shortfall in the current period.',
          tone: 'orange',
          confidence: 76,
          evidence: {
            title: 'Dispatch variance traceability',
            evidenceChain: [
              { id: 'variance-insight', label: 'AI Insight', value: 'Observed dispatch is below target by 5.9%.', confidence: 76, tone: 'orange' },
              { id: 'variance-source', label: 'Source Document', value: 'Production Dispatch Ledger', confidence: 73, tone: 'yellow' },
              { id: 'variance-location', label: 'Page / Section / Table / Cell', value: 'Page 6, Dispatch Summary, Table F1, Cell C18', confidence: 70, tone: 'yellow' },
            ],
          },
        },
        {
          id: 'not-reporting-only',
          label: 'The pattern looks operational, not purely reporting-based',
          value: 'Dispatch variance is consistent with a real throughput gap rather than a single isolated clerical mismatch.',
          tone: 'yellow',
          confidence: 71,
          evidence: {
            title: 'Operational explanation traceability',
            evidenceChain: [
              { id: 'op-insight', label: 'AI Insight', value: 'Variance is persistent and consistent with equipment or planning constraint.', confidence: 71, tone: 'yellow' },
              { id: 'op-source', label: 'Source Document', value: 'Maintenance and production log', confidence: 68, tone: 'orange' },
              { id: 'op-location', label: 'Page / Section / Table / Cell', value: 'Page 8, Performance Review, Table P3, Cell J9', confidence: 69, tone: 'orange' },
            ],
          },
        },
      ],
      conflicts: [
        {
          title: 'Conflicting signals',
          detail: 'The operational evidence is directionally clear, but the target shortfall is small enough that reporting or timing artifacts cannot be excluded without a deeper review.',
          tone: 'red',
        },
      ],
    },
  },
]

export default aiQueryExamples
