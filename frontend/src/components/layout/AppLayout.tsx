import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { CommandPalette } from '../ui/CommandPalette'
import { useUIStore } from '../../stores/uiStore'

export function AppLayout() {
  const { commandPaletteOpen, closeCommandPalette, openCommandPalette } = useUIStore()

  // Global Ctrl+K shortcut
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        openCommandPalette()
      }
      if (e.key === 'Escape') closeCommandPalette()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [openCommandPalette, closeCommandPalette])

  return (
    <div className="flex h-screen overflow-hidden bg-coal-950">
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      {commandPaletteOpen && (
        <CommandPalette onClose={closeCommandPalette} />
      )}
    </div>
  )
}
