// Application configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const APP_CONFIG = {
  name: 'CMPDI GODLIKE',
  fullName: 'CMPDI AI Mining Intelligence Platform',
  version: '1.0.0',
  organization: 'Central Mine Planning & Design Institute Ltd.',
  ministry: 'Ministry of Coal, Government of India',
} as const

export const QUERY_KEYS = {
  dashboard:      ['dashboard'],
  documents:      ['documents'],
  document:       (id: string) => ['document', id],
  entities:       ['entities'],
  entity:         (id: string) => ['entity', id],
  facts:          ['facts'],
  conflicts:      ['conflicts'],
  conflict:       (id: string) => ['conflict', id],
  duplicates:     ['duplicates'],
  flags:          ['flags'],
  analytics:      ['analytics'],
  copilotHistory: ['copilot', 'history'],
  reports:        ['reports'],
  report:         (id: string) => ['report', id],
  forecasts:      ['forecasts'],
  mapLayers:      (layer: string) => ['map', layer],
  parliamentary:  ['parliamentary'],
  auditLog:       ['audit-log'],
  users:          ['users'],
  systemHealth:   ['system-health'],
  topics:         ['topics'],
  search:         (q: string) => ['search', q],
} as const

export const ROLES = {
  analyst:  'analyst',
  reviewer: 'reviewer',
  admin:    'admin',
} as const

export type Role = keyof typeof ROLES

export const ROUTE_PERMISSIONS: Record<string, Role[]> = {
  '/dashboard':           ['analyst', 'reviewer', 'admin'],
  '/copilot':             ['analyst', 'reviewer', 'admin'],
  '/documents':           ['analyst', 'reviewer', 'admin'],
  '/entities':            ['analyst', 'reviewer', 'admin'],
  '/facts':               ['analyst', 'reviewer', 'admin'],
  '/analytics':           ['analyst', 'reviewer', 'admin'],
  '/forecasting':         ['analyst', 'reviewer', 'admin'],
  '/map':                 ['analyst', 'reviewer', 'admin'],
  '/reports':             ['analyst', 'reviewer', 'admin'],
  '/conflicts':           ['analyst', 'reviewer', 'admin'],
  '/duplicates':          ['analyst', 'reviewer', 'admin'],
  '/review':              ['reviewer', 'admin'],
  '/parliamentary':       ['reviewer', 'admin'],
  '/audit':               ['reviewer', 'admin'],
  '/admin':               ['admin'],
  '/admin/users':         ['admin'],
  '/admin/system':        ['admin'],
  '/admin/benchmark':     ['admin'],
}

export const MAP_LAYERS = [
  'production',
  'dispatch',
  'resources',
  'reserves',
  'exploration',
  'report_volume',
  'data_quality',
  'conflict_density',
] as const

export const FORECAST_METRICS = [
  'coal_production',
  'coal_dispatch',
  'overburden_removal',
  'manpower',
] as const

export const PROCESSING_STATUSES = {
  pending:    { label: 'Pending',    color: 'text-coal-300' },
  processing: { label: 'Processing', color: 'text-amber-500' },
  done:       { label: 'Processed',  color: 'text-status-operational' },
  failed:     { label: 'Failed',     color: 'text-status-offline' },
} as const
