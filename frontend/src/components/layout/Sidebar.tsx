import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Bot, FileText, Database, BarChart3,
  Map, TrendingUp, ClipboardList, FileBarChart, Shield,
  Users, Activity, ChevronLeft, ChevronRight, Search,
  AlertTriangle, Copy, MessageSquare, BookOpen, Tag,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useUIStore } from '../../stores/uiStore'
import { clsx } from 'clsx'

interface NavSection {
  label: string
  items: NavItem[]
}

interface NavItem {
  label:    string
  path:     string
  icon:     React.ReactNode
  roles?:   string[]
  badge?:   string | number
}

const NAV_SECTIONS: NavSection[] = [
  {
    label: 'COMMAND CENTER',
    items: [
      { label: 'Overview',      path: '/dashboard',     icon: <LayoutDashboard size={15} /> },
      { label: 'AI Copilot',    path: '/copilot',        icon: <Bot size={15} /> },
      { label: 'Search',        path: '/search',         icon: <Search size={15} /> },
    ],
  },
  {
    label: 'KNOWLEDGE',
    items: [
      { label: 'Documents',     path: '/documents',      icon: <FileText size={15} /> },
      { label: 'Entities',      path: '/entities',       icon: <BookOpen size={15} /> },
      { label: 'Facts',         path: '/facts',          icon: <Database size={15} /> },
      { label: 'Topics',        path: '/topics',         icon: <Tag size={15} /> },
    ],
  },
  {
    label: 'INTELLIGENCE',
    items: [
      { label: 'Analytics',     path: '/analytics',      icon: <BarChart3 size={15} /> },
      { label: 'Forecasting',   path: '/forecasting',    icon: <TrendingUp size={15} /> },
      { label: 'Mine Map',      path: '/map',            icon: <Map size={15} /> },
    ],
  },
  {
    label: 'DATA TRUST',
    items: [
      { label: 'Conflicts',     path: '/conflicts',      icon: <AlertTriangle size={15} /> },
      { label: 'Duplicates',    path: '/duplicates',     icon: <Copy size={15} /> },
    ],
  },
  {
    label: 'REVIEW',
    items: [
      { label: 'Review Queue',  path: '/review',         icon: <ClipboardList size={15} />, roles: ['reviewer','admin'] },
      { label: 'Parliamentary', path: '/parliamentary',  icon: <MessageSquare size={15} />, roles: ['reviewer','admin'] },
      { label: 'Audit Log',     path: '/audit',          icon: <Shield size={15} />,        roles: ['reviewer','admin'] },
    ],
  },
  {
    label: 'REPORTING',
    items: [
      { label: 'Reports',       path: '/reports',        icon: <FileBarChart size={15} /> },
    ],
  },
  {
    label: 'SYSTEM',
    items: [
      { label: 'Users',         path: '/admin/users',    icon: <Users size={15} />,    roles: ['admin'] },
      { label: 'System Health', path: '/admin/system',   icon: <Activity size={15} />, roles: ['admin'] },
    ],
  },
]

export function Sidebar() {
  const { user, hasRole, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const location = useLocation()

  const roleLevel: Record<string, number> = { analyst: 1, reviewer: 2, admin: 3 }
  const userLevel = user ? (roleLevel[user.role] ?? 0) : 0

  const canSeeItem = (item: NavItem) => {
    if (!item.roles) return true
    return item.roles.some((r) => roleLevel[r] <= userLevel)
  }

  return (
    <aside
      className={clsx(
        'relative flex flex-col h-screen bg-coal-950 border-r border-white/[0.06] transition-all duration-300 shrink-0',
        sidebarCollapsed ? 'w-14' : 'w-56'
      )}
    >
      {/* Logo */}
      <div className={clsx('flex items-center border-b border-white/[0.06] shrink-0',
        sidebarCollapsed ? 'p-3 justify-center' : 'px-4 py-4 gap-3'
      )}>
        {/* CMPDI emblem placeholder */}
        <div className="w-7 h-7 rounded-sm bg-amber-500 flex items-center justify-center shrink-0">
          <span className="text-coal-950 font-black text-[10px] leading-none">CG</span>
        </div>
        {!sidebarCollapsed && (
          <div>
            <div className="text-white font-bold text-sm leading-tight tracking-wide">CMPDI</div>
            <div className="text-amber-500 font-black text-xs leading-tight tracking-widest">GODLIKE</div>
          </div>
        )}
      </div>

      {/* Toggle */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-16 w-6 h-6 rounded-full bg-coal-800 border border-white/[0.1] flex items-center justify-center text-coal-300 hover:text-amber-500 z-10 transition-colors"
      >
        {sidebarCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 space-y-4">
        {NAV_SECTIONS.map((section) => {
          const visibleItems = section.items.filter(canSeeItem)
          if (!visibleItems.length) return null

          return (
            <div key={section.label}>
              {!sidebarCollapsed && (
                <div className="px-4 mb-1">
                  <span className="section-label text-[10px]">{section.label}</span>
                </div>
              )}
              {sidebarCollapsed && <div className="h-px bg-white/[0.04] mx-2 mb-2" />}

              <div className="space-y-0.5 px-2">
                {visibleItems.map((item) => {
                  const isActive = location.pathname === item.path ||
                    (item.path !== '/dashboard' && location.pathname.startsWith(item.path))
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      title={sidebarCollapsed ? item.label : undefined}
                      className={clsx(
                        'flex items-center rounded-sm text-sm font-medium transition-all duration-150 relative group',
                        sidebarCollapsed ? 'justify-center p-2.5' : 'gap-2.5 px-3 py-1.5',
                        isActive
                          ? 'text-amber-500 bg-amber-500/10'
                          : 'text-coal-300 hover:text-white hover:bg-coal-800'
                      )}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-amber-500 rounded-r" />
                      )}
                      <span className={isActive ? 'text-amber-500' : ''}>{item.icon}</span>
                      {!sidebarCollapsed && <span>{item.label}</span>}
                      {/* Tooltip for collapsed */}
                      {sidebarCollapsed && (
                        <div className="absolute left-14 bg-coal-800 border border-white/[0.1] text-white text-xs rounded-sm px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                          {item.label}
                        </div>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      {/* User footer */}
      <div className={clsx(
        'border-t border-white/[0.06] p-3 shrink-0',
        sidebarCollapsed ? 'flex justify-center' : ''
      )}>
        {!sidebarCollapsed ? (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-sm bg-coal-700 flex items-center justify-center shrink-0">
              <span className="text-white font-bold text-xs">{user?.username?.slice(0,2).toUpperCase() || 'U'}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-xs font-medium truncate">{user?.username}</div>
              <div className="text-amber-500 text-[10px] uppercase tracking-wider font-semibold">{user?.role}</div>
            </div>
            <button
              onClick={logout}
              className="text-coal-400 hover:text-white transition-colors text-[10px] uppercase tracking-wider"
              title="Logout"
            >
              ⏻
            </button>
          </div>
        ) : (
          <div
            title={user?.username}
            className="w-7 h-7 rounded-sm bg-coal-700 flex items-center justify-center cursor-pointer"
          >
            <span className="text-white font-bold text-xs">{user?.username?.slice(0,2).toUpperCase() || 'U'}</span>
          </div>
        )}
      </div>
    </aside>
  )
}
