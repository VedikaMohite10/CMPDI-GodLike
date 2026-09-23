import { useState } from 'react'
import Card from '../ui/Card'
import { updateUser, deactivateUser } from '../../api/admin'
import { useAuth } from '../../context/AuthContext'

const ROLES = ['analyst', 'reviewer', 'admin']

export default function UserManagementTable({ users: initialUsers }) {
  const { token } = useAuth()
  const [users, setUsers] = useState(initialUsers)
  const [toast, setToast] = useState('')
  const [working, setWorking] = useState(null) // userId being modified

  const showToast = (msg) => { setToast(msg); window.setTimeout(() => setToast(''), 3000) }

  const handleRoleChange = async (userId, newRole) => {
    setWorking(userId)
    try {
      const updated = await updateUser(token, userId, { role: newRole })
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: updated.role } : u))
      showToast(`Role updated to ${newRole}`)
    } catch (err) {
      showToast(`Failed to update role: ${err?.detail ?? err?.message ?? 'Unknown error'}`)
    } finally {
      setWorking(null)
    }
  }

  const handleDeactivate = async (userId) => {
    if (!window.confirm('Deactivate this user? They will no longer be able to log in.')) return
    setWorking(userId)
    try {
      await deactivateUser(token, userId)
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, status: 'Inactive' } : u))
      showToast('User deactivated (audit record preserved)')
    } catch (err) {
      showToast(`Failed to deactivate: ${err?.detail ?? err?.message ?? 'Unknown error'}`)
    } finally {
      setWorking(null)
    }
  }

  return (
    <Card className="governance-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Access control</p>
          <h2>User management</h2>
        </div>
      </div>

      {toast && (
        <div className="report-toast report-toast--success" style={{ marginBottom: '12px' }}>
          {toast}
        </div>
      )}

      <div className="table-wrap">
        <table className="governance-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Team</th>
              <th>Status</th>
              <th>Last login</th>
              <th>Permissions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  <div className="user-cell">
                    <span className="user-avatar">{user.name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</span>
                    <div>
                      <strong>{user.name}</strong>
                      <small>{user.id}</small>
                    </div>
                  </div>
                </td>
                <td>
                  {/* Role select — admin-only action, backend enforces this too */}
                  <select
                    className="role-pill role-pill--admin"
                    value={user.role}
                    disabled={working === user.id}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: 700, fontSize: '12px' }}
                    aria-label={`Change role for ${user.name}`}
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td>{user.team}</td>
                <td>
                  <span className={`status-pill status-pill--${user.status.toLowerCase()}`}>{user.status}</span>
                </td>
                <td>{user.lastLogin}</td>
                <td>
                  <div className="permission-list">
                    {user.permissions.map((permission) => (
                      <span key={permission} className="permission-pill">
                        {permission}
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  {user.status === 'Active' && (
                    <button
                      type="button"
                      onClick={() => handleDeactivate(user.id)}
                      disabled={working === user.id}
                      style={{
                        fontSize: '11px', fontWeight: 700, padding: '4px 10px',
                        borderRadius: '4px', border: '1px solid #dc2626',
                        color: '#dc2626', background: 'transparent', cursor: 'pointer',
                        opacity: working === user.id ? 0.5 : 1,
                      }}
                    >
                      {working === user.id ? '…' : 'Deactivate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
