import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser, Role } from '../types'

interface AuthState {
  token:   string | null
  user:    AuthUser | null
  isAuth:  boolean

  // Actions
  setAuth:  (token: string, user: AuthUser) => void
  logout:   () => void
  hasRole:  (minRole: Role) => boolean
  canAccess:(path: string) => boolean
}

const ROLE_LEVEL: Record<Role, number> = {
  analyst:  1,
  reviewer: 2,
  admin:    3,
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token:   null,
      user:    null,
      isAuth:  false,

      setAuth: (token, user) => set({ token, user, isAuth: true }),

      logout: () => {
        set({ token: null, user: null, isAuth: false })
        // Remove from localStorage on logout
        localStorage.removeItem('cmpdi_token')
      },

      hasRole: (minRole: Role) => {
        const user = get().user
        if (!user) return false
        return ROLE_LEVEL[user.role] >= ROLE_LEVEL[minRole]
      },

      canAccess: (path: string) => {
        const user = get().user
        if (!user) return false

        // Import route permissions inline to avoid circular deps
        const ROUTE_PERMISSIONS: Record<string, Role[]> = {
          '/review':         ['reviewer', 'admin'],
          '/parliamentary':  ['reviewer', 'admin'],
          '/audit':          ['reviewer', 'admin'],
          '/admin':          ['admin'],
          '/admin/users':    ['admin'],
          '/admin/system':   ['admin'],
          '/admin/benchmark':['admin'],
        }

        const requiredRoles = ROUTE_PERMISSIONS[path]
        if (!requiredRoles) return true // open to all authenticated users
        return requiredRoles.includes(user.role)
      },
    }),
    {
      name:    'cmpdi-auth',
      version: 1,
    }
  )
)
