import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Plus, AlertCircle, CheckCircle, X, UserCheck } from 'lucide-react'
import { listUsers, createUser, updateUser, type UserOut } from '../../api/auth'
import { useAuthStore } from '../../stores/authStore'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'

export default function UsersPage() {
  const { token } = useAuthStore()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'analyst' as 'analyst' | 'reviewer' | 'admin' })
  const [createError, setCreateError] = useState('')

  const { data: users, isLoading, error, refetch } = useQuery({
    queryKey: QUERY_KEYS.users,
    queryFn: () => listUsers(token!),
    enabled: !!token,
  })

  const createMutation = useMutation({
    mutationFn: () => createUser(token!, newUser),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.users })
      setShowCreate(false)
      setNewUser({ username: '', password: '', role: 'analyst' })
      setCreateError('')
    },
    onError: (e: unknown) => {
      setCreateError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create user.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: { is_active?: boolean; role?: string } }) =>
      updateUser(token!, id, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEYS.users }),
  })

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">SYSTEM ADMINISTRATION</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Users size={16} className="text-amber-500" />
          User Management
          {users && <span className="text-coal-400 font-normal text-sm ml-1">({users.length})</span>}
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Create user button */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-coal-400">Manage platform users and their access roles.</div>
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-xs">
            <Plus size={13} /> Create User
          </button>
        </div>

        {/* Create user form */}
        {showCreate && (
          <IndustrialCard className="p-4">
            <div className="section-label mb-3">CREATE NEW USER</div>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="section-label block mb-1">Username</label>
                <input
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="industrial-input w-40 text-xs"
                  placeholder="username"
                />
              </div>
              <div>
                <label className="section-label block mb-1">Password</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="industrial-input w-40 text-xs"
                  placeholder="password"
                />
              </div>
              <div>
                <label className="section-label block mb-1">Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value as 'analyst' | 'reviewer' | 'admin' })}
                  className="industrial-input w-32 text-xs"
                >
                  <option value="analyst">Analyst</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!newUser.username || !newUser.password || createMutation.isPending}
                className="btn-primary text-xs"
              >
                <UserCheck size={12} />
                {createMutation.isPending ? 'Creating...' : 'Create User'}
              </button>
              <button onClick={() => setShowCreate(false)} className="text-coal-400 hover:text-white">
                <X size={14} />
              </button>
            </div>
            {createError && (
              <p className="mt-2 text-xs text-status-offline">{createError}</p>
            )}
          </IndustrialCard>
        )}

        {/* Users table */}
        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={5} /></div>
          ) : error ? (
            <EmptyState title="Unable to load users" message="Failed to retrieve user list." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !users?.length ? (
            <EmptyState title="No users" message="Create the first user above." icon={<Users size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user: UserOut) => (
                  <tr key={user.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-sm bg-coal-700 flex items-center justify-center shrink-0">
                          <span className="text-white text-[10px] font-bold">{user.username.slice(0, 2).toUpperCase()}</span>
                        </div>
                        <span className="text-white font-medium">{user.username}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`text-xs font-mono font-bold uppercase px-2 py-0.5 rounded-sm ${
                        user.role === 'admin' ? 'text-amber-500 bg-amber-500/10' :
                        user.role === 'reviewer' ? 'text-blue-400 bg-blue-400/10' :
                        'text-coal-300 bg-coal-800'
                      }`}>{user.role}</span>
                    </td>
                    <td>
                      <StatusBadge status={user.is_active ? 'operational' : 'offline'} />
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateMutation.mutate({ id: user.id, updates: { is_active: !user.is_active } })}
                          className="text-xs text-coal-400 hover:text-white transition-colors font-mono"
                        >
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>
      </div>
    </div>
  )
}
