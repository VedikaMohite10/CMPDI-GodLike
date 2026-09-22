import React, { createContext, useContext, useState } from 'react'
import { mockUsers } from '../data/mockUsers'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // Default to Analyst user (Rahul Sharma) for seamless direct access
  const [user, setUser] = useState(mockUsers[0])

  const login = (email, password) => {
    const foundUser = mockUsers.find(
      (u) => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password,
    )

    if (foundUser) {
      setUser(foundUser)
      return { success: true, user: foundUser }
    }

    return { success: false, error: 'Invalid email or password. Please use a mock account.' }
  }

  const loginAsRole = (roleName) => {
    const foundUser = mockUsers.find((u) => u.role === roleName)
    if (foundUser) {
      setUser(foundUser)
      return { success: true, user: foundUser }
    }
    return { success: false, error: `No mock user found for role ${roleName}` }
  }

  const logout = () => {
    // Reset to default mock user
    setUser(mockUsers[0])
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || 'Analyst',
        isAuthenticated: true,
        login,
        loginAsRole,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    return {
      user: mockUsers[0],
      role: 'Analyst',
      isAuthenticated: true,
      login: () => ({ success: true }),
      loginAsRole: () => ({ success: true }),
      logout: () => {},
    }
  }
  return context
}
