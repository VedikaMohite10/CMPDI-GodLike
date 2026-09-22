import Card from '../ui/Card'

export default function UserManagementTable({ users }) {
  return (
    <Card className="governance-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Access control</p>
          <h2>User management</h2>
        </div>
      </div>

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
                  <span className="role-pill role-pill--admin">{user.role}</span>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
