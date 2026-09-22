export const evidenceMock = {
  productionProof: {
    title: 'Production Value Traceability',
    evidenceChain: [
      {
        id: 'insight',
        label: 'AI Insight',
        value: 'Production output is 26.4 Mt',
        confidence: 96,
        tone: 'green',
      },
      {
        id: 'calculation',
        label: 'Calculation',
        value: 'Sum of monthly production records across Q1-Q4',
        confidence: 94,
        tone: 'green',
      },
      {
        id: 'validated',
        label: 'Validated Values',
        value: 'Q1 6.1 Mt; Q2 6.5 Mt; Q3 6.9 Mt; Q4 6.9 Mt',
        confidence: 92,
        tone: 'green',
      },
      {
        id: 'source',
        label: 'Source Document',
        value: 'Annual Coal Production Report 2025-26',
        confidence: 97,
        tone: 'green',
      },
      {
        id: 'location',
        label: 'Page / Section / Table / Cell',
        value: 'Page 4, Executive Summary, Table A1, Cell B7',
        confidence: 98,
        tone: 'green',
      },
    ],
  },
  reserveProof: {
    title: 'Reserve Estimate Traceability',
    evidenceChain: [
      {
        id: 'insight',
        label: 'AI Insight',
        value: 'Net coal reserve estimated at 342.6 Mt',
        confidence: 91,
        tone: 'green',
      },
      {
        id: 'calculation',
        label: 'Calculation',
        value: 'Block-wise reserve estimate after geological deductions',
        confidence: 82,
        tone: 'yellow',
      },
      {
        id: 'validated',
        label: 'Validated Values',
        value: 'Block A 118.4 Mt; Block B 94.6 Mt; Block C 129.6 Mt',
        confidence: 86,
        tone: 'green',
      },
      {
        id: 'source',
        label: 'Source Document',
        value: 'Exploration Block Assessment',
        confidence: 95,
        tone: 'green',
      },
      {
        id: 'location',
        label: 'Page / Section / Table / Cell',
        value: 'Page 19, Reserves, Table R7, Cell E25',
        confidence: 97,
        tone: 'green',
      },
    ],
  },
  partialProof: {
    title: 'Inferred Value Traceability',
    evidenceChain: [
      {
        id: 'insight',
        label: 'AI Insight',
        value: 'Dispatch volume likely improved by 2.3%',
        confidence: 68,
        tone: 'orange',
      },
      {
        id: 'calculation',
        label: 'Calculation',
        value: 'Difference between planned and observed dispatch over 6 weeks',
        confidence: 66,
        tone: 'orange',
      },
      {
        id: 'validated',
        label: 'Validated Values',
        value: 'Observed dispatch 12.7 Mt against target 13.5 Mt',
        confidence: 71,
        tone: 'yellow',
      },
      {
        id: 'source',
        label: 'Source Document',
        value: 'Production Dispatch Ledger',
        confidence: 73,
        tone: 'yellow',
      },
      {
        id: 'location',
        label: 'Page / Section / Table / Cell',
        value: 'Page 6, Dispatch Summary, Table F1, Cell C18',
        confidence: 70,
        tone: 'yellow',
      },
    ],
  },
}

export default evidenceMock
