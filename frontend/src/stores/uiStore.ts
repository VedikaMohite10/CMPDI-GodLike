import { create } from 'zustand'

interface UIState {
  sidebarCollapsed:   boolean
  commandPaletteOpen: boolean
  activePanel:        string | null

  toggleSidebar:        () => void
  setSidebarCollapsed:  (v: boolean) => void
  openCommandPalette:   () => void
  closeCommandPalette:  () => void
  setActivePanel:       (panel: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed:   false,
  commandPaletteOpen: false,
  activePanel:        null,

  toggleSidebar:       () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
  openCommandPalette:  () => set({ commandPaletteOpen: true }),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  setActivePanel:      (panel) => set({ activePanel: panel }),
}))
