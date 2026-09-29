import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Search, Bell, ChevronRight, Zap, Activity } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useUIStore } from '../../stores/uiStore'
import { getSystemHealth } from '../../api/review'

const BREADCRUMB_MAP: Record<string, string> = {
  '/dashboard':   'Command Center',
  '/copilot':     'AI Copilot',
  '/search':      'Global Search',
  '/documents':   'Document Intelligence',
  '/entities':    'Entities',
  '/facts':       'Extracted Facts',
  '/topics':      'Topics',
  '/analytics':   'Analytics',
  '/forecasting': 'Forecasting Engine',
  '/map':         'Mine Intelligence Map',
  '/conflicts':   'Conflict Detection',
  '/duplicates':  'Duplicate Detection',
  '/review':      'Review Console',
  '/parliamentary':'Parliamentary Copilot',
  '/audit':       'Audit Log',
  '/reports':     'Report Generation',
  '/admin/users': 'User Management',
  '/admin/system':'System Health',
  '/admin/benchmark': 'Benchmark',
}

interface HeaderProps {
  onSearchClick?: () => void
}

export function Header({ onSearchClick }: HeaderProps) {
  const { user } = useAuthStore()
  const { openCommandPalette } = useUIStore()
  const location = useLocation()
  const [systemStatus, setSystemStatus] = useState<'operational' | 'degraded' | 'offline'>('operational')

  const breadcrumb = BREADCRUMB_MAP[location.pathname] || 'CMPDI GODLIKE'

  // Poll health
  useEffect(() => {
    getSystemHealth()
      .then(() => setSystemStatus('operational'))
      .catch(() => setSystemStatus('offline'))

    const interval = setInterval(() => {
      getSystemHealth()
        .then(() => setSystemStatus('operational'))
        .catch(() => setSystemStatus('offline'))
    }, 60_000)
    return () => clearInterval(interval)
  }, [])

  const statusColors = {
    operational: 'text-status-operational',
    degraded:    'text-status-degraded',
    offline:     'text-status-offline',
  }

  return (
    <header className="h-11 bg-coal-950 border-b border-white/[0.06] flex items-center px-4 gap-4 shrink-0">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-coal-300 font-mono">
        <span className="text-amber-500 font-semibold">CMPDI GODLIKE</span>
        <ChevronRight size={11} className="text-coal-600" />
        <span className="text-white font-medium">{breadcrumb}</span>
      </div>

      <div className="flex-1" />

      {/* Global Search */}
      <button
        onClick={onSearchClick || openCommandPalette}
        className="flex items-center gap-2 bg-coal-850 hover:bg-coal-800 border border-white/[0.06] rounded-sm px-3 py-1.5 text-coal-300 hover:text-white transition-all text-xs font-mono"
      >
        <Search size={12} />
        <span className="hidden sm:block">Search intelligence...</span>
        <kbd className="hidden sm:block text-[10px] bg-coal-700 px-1.5 py-0.5 rounded text-coal-400">⌘K</kbd>
      </button>

      {/* AI Copilot shortcut */}
      <button
        onClick={() => {}}
        className="flex items-center gap-1.5 text-amber-500 hover:text-amber-400 text-xs font-medium transition-colors"
        title="AI Copilot"
      >
        <Zap size={13} />
        <span className="hidden sm:block">Copilot</span>
      </button>

      {/* System status */}
      <div className={`flex items-center gap-1.5 text-xs font-mono ${statusColors[systemStatus]}`}>
        <div className={`w-1.5 h-1.5 rounded-full ${
          systemStatus === 'operational' ? 'bg-status-operational animate-pulse-slow' :
          systemStatus === 'degraded' ? 'bg-status-degraded' : 'bg-status-offline animate-pulse'
        }`} />
        <span className="hidden sm:block uppercase text-[10px] tracking-wider font-semibold">
          {systemStatus === 'operational' ? 'Operational' :
           systemStatus === 'degraded' ? 'Degraded' : 'Offline'}
        </span>
      </div>

      {/* Notifications */}
      <button className="relative p-1 text-coal-300 hover:text-white transition-colors">
        <Bell size={14} />
      </button>

      {/* User badge */}
      <div className="flex items-center gap-2 text-xs">
        <div className="w-6 h-6 rounded-sm bg-coal-700 flex items-center justify-center">
          <span className="text-white font-bold text-[10px]">{user?.username?.slice(0,2).toUpperCase()}</span>
        </div>
        <div className="hidden sm:block">
          <div className="text-white text-xs leading-none">{user?.username}</div>
          <div className="text-amber-500 text-[10px] uppercase tracking-wider leading-none mt-0.5">{user?.role}</div>
        </div>
      </div>
    </header>
  )
}
