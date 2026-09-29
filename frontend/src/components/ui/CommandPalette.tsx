import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FileText, Bot, Map, BarChart3, ClipboardList, TrendingUp, FileBarChart, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { semanticSearch } from '../../api/analytics'

interface Command {
  id:    string
  label: string
  path:  string
  icon:  React.ReactNode
  group: string
  shortcut?: string
}

const COMMANDS: Command[] = [
  { id: 'dashboard',    label: 'Command Center',        path: '/dashboard',    icon: <BarChart3 size={14} />,    group: 'Navigation' },
  { id: 'copilot',      label: 'AI Copilot',            path: '/copilot',      icon: <Bot size={14} />,          group: 'Navigation' },
  { id: 'documents',    label: 'Document Intelligence', path: '/documents',    icon: <FileText size={14} />,     group: 'Navigation' },
  { id: 'analytics',   label: 'Analytics',             path: '/analytics',    icon: <BarChart3 size={14} />,    group: 'Navigation' },
  { id: 'map',          label: 'Mine Intelligence Map', path: '/map',          icon: <Map size={14} />,          group: 'Navigation' },
  { id: 'forecasting',  label: 'Forecasting Engine',    path: '/forecasting',  icon: <TrendingUp size={14} />,   group: 'Navigation' },
  { id: 'review',       label: 'Review Console',        path: '/review',       icon: <ClipboardList size={14} />, group: 'Navigation' },
  { id: 'reports',      label: 'Generate Report',       path: '/reports',      icon: <FileBarChart size={14} />, group: 'Navigation' },
  { id: 'upload',       label: 'Upload Documents',      path: '/documents?action=upload', icon: <FileText size={14} />, group: 'Actions' },
]

interface CommandPaletteProps {
  onClose: () => void
}

export function CommandPalette({ onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Array<{ label: string; path: string }>>([])
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    const timeout = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await semanticSearch(query, 5)
        setSearchResults(
          data.results.map((r) => ({
            label: `${r.document_filename || 'Document'} — ${r.text_excerpt.slice(0, 60)}…`,
            path:  `/documents/${r.document_id}`,
          }))
        )
      } catch {
        setSearchResults([])
      } finally {
        setLoading(false)
      }
    }, 400)

    return () => clearTimeout(timeout)
  }, [query])

  const filteredCommands = query
    ? COMMANDS.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : COMMANDS

  const handleSelect = (path: string) => {
    navigate(path)
    onClose()
  }

  return (
    <div className="command-backdrop" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: -8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: -8 }}
        transition={{ duration: 0.15 }}
        className="w-full max-w-xl bg-coal-900 border border-white/[0.1] rounded-sm shadow-coal overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
          <Search size={15} className="text-amber-500 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands, documents, entities..."
            className="flex-1 bg-transparent text-white text-sm placeholder-coal-400 outline-none font-mono"
          />
          {loading && <div className="w-4 h-4 rounded-full border-2 border-amber-500/30 border-t-amber-500 animate-spin" />}
          <button onClick={onClose} className="text-coal-400 hover:text-white transition-colors">
            <X size={14} />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {/* Commands */}
          {filteredCommands.length > 0 && (
            <div>
              <div className="px-4 py-1.5">
                <span className="section-label text-[10px]">Commands</span>
              </div>
              {filteredCommands.map((cmd) => (
                <button
                  key={cmd.id}
                  onClick={() => handleSelect(cmd.path)}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-coal-800 text-left transition-colors"
                >
                  <span className="text-amber-500">{cmd.icon}</span>
                  <span className="text-sm text-white">{cmd.label}</span>
                  <span className="ml-auto text-2xs text-coal-400 font-mono">{cmd.group}</span>
                </button>
              ))}
            </div>
          )}

          {/* Semantic search results */}
          {searchResults.length > 0 && (
            <div className="mt-2">
              <div className="px-4 py-1.5 border-t border-white/[0.04]">
                <span className="section-label text-[10px]">Intelligence Results</span>
              </div>
              {searchResults.map((r, i) => (
                <button
                  key={i}
                  onClick={() => handleSelect(r.path)}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-coal-800 text-left transition-colors"
                >
                  <span className="text-coal-400"><FileText size={12} /></span>
                  <span className="text-sm text-coal-100 truncate">{r.label}</span>
                </button>
              ))}
            </div>
          )}

          {query && !loading && filteredCommands.length === 0 && searchResults.length === 0 && (
            <div className="px-4 py-6 text-center text-coal-400 text-sm">
              No results for "{query}"
            </div>
          )}
        </div>

        <div className="border-t border-white/[0.06] px-4 py-2 flex items-center gap-4 text-2xs text-coal-400 font-mono">
          <span><kbd className="bg-coal-800 px-1 rounded">↑↓</kbd> navigate</span>
          <span><kbd className="bg-coal-800 px-1 rounded">Enter</kbd> select</span>
          <span><kbd className="bg-coal-800 px-1 rounded">Esc</kbd> close</span>
        </div>
      </motion.div>
    </div>
  )
}
